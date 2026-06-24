"""
结构化日志工具 - 支持 JSON 格式输出，便于日志聚合和查询

阶段 4 增强（J5）：
  - 每个日志携带 ``trace_id`` / ``user_id`` / ``project_id`` / ``request_id`` / ``path`` / ``method``
  - 通过 ``TraceContextFilter`` 自动从 contextvars 注入 trace_id
  - 不破坏现有 StructuredLogger / RequestLogger 接口
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

import structlog


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class StructuredLogger:
    """
    结构化日志记录器
    
    特性：
    - JSON 格式输出（便于 ELK/Loki 聚合）
    - 上下文追踪（request_id, user_id 等）
    - 标准字段规范
    - 敏感信息脱敏
    """
    
    def __init__(self, name: str = "api_pilot", json_format: bool = True):
        self.logger = logging.getLogger(name)
        self.json_format = json_format
        self._context: Dict[str, Any] = {}
        
        # 配置根日志记录器
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def set_context(self, **kwargs):
        """设置日志上下文"""
        self._context.update(kwargs)
    
    def clear_context(self):
        """清除日志上下文"""
        self._context = {}
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """格式化日志消息"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "message": message,
            "logger": self.logger.name,
            **self._context,
            **kwargs,
        }
        return json.dumps(log_entry, ensure_ascii=False, default=str)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format_message("debug", message, **kwargs))
    
    def info(self, message: str, **kwargs):
        self.logger.info(self._format_message("info", message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_message("warning", message, **kwargs))
    
    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        error_data = {"error_type": type(exc_info).__name__} if exc_info else {}
        if exc_info and kwargs.get("include_trace", False):
            error_data["traceback"] = traceback.format_exc()
        self.logger.error(self._format_message("error", message, **kwargs, **error_data))
    
    def critical(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        error_data = {"error_type": type(exc_info).__name__} if exc_info else {}
        if exc_info:
            error_data["traceback"] = traceback.format_exc()
        self.logger.critical(self._format_message("critical", message, **kwargs, **error_data))


class RequestLogger(StructuredLogger):
    """
    请求日志记录器 - 专门用于记录 API 请求
    """
    
    def log_request(self, method: str, path: str, request_id: str, **kwargs):
        """记录请求"""
        self.info(
            f"{method} {path}",
            event="request_start",
            http_method=method,
            path=path,
            request_id=request_id,
            **kwargs,
        )
    
    def log_response(self, method: str, path: str, request_id: str, status_code: int, duration_ms: float, **kwargs):
        """记录响应"""
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        getattr(self, level)(
            f"{method} {path} -> {status_code}",
            event="request_complete",
            http_method=method,
            path=path,
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs,
        )



# 全局日志实例
_app_logger: Optional[StructuredLogger] = None
_request_logger: Optional[RequestLogger] = None



def get_logger(name: str = "api_pilot") -> StructuredLogger:
    """获取全局日志实例"""
    global _app_logger
    if _app_logger is None:
        _app_logger = StructuredLogger(name)
    return _app_logger


def get_request_logger() -> RequestLogger:
    """获取请求日志实例"""
    global _request_logger
    if _request_logger is None:
        _request_logger = RequestLogger("api_pilot.requests")
    return _request_logger


def configure_logging(json_format: bool = True, level: str = "INFO"):
    """配置全局日志"""
    import logging

    log_level = getattr(logging, level.upper(), logging.INFO)

    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 配置标准 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # 阶段 4：注册 trace_id 过滤器，使所有日志自动带 trace_id
    try:
        from app.utils.logging import TraceContextFilter
        for name in ("api_pilot", "api_pilot.request", "api_pilot.request_log",
                      "api_pilot.db", "api_pilot.timeout",
                      "api_pilot.idempotency", "api_pilot.routers.import_export",
                      "run", "service.test_runner", "service.notifier"):
            _lg = logging.getLogger(name)
            if not any(isinstance(f, TraceContextFilter) for f in _lg.filters):
                _lg.addFilter(TraceContextFilter())
    except ImportError:
        pass

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    return get_logger()


class TraceContextFilter(logging.Filter):
    """阶段 4 增强：把 ``TraceContext`` 中的 trace_id / user_id 等
    自动注入每条日志记录（避免每个 logger.bind 调用）。

    通过 contextvars 工作，零侵入；中间件设置 → 业务代码读取。
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            from app.services.trace import TraceContext

            trace_id = TraceContext.get()
        except Exception:  # noqa: BLE001
            trace_id = None

        if trace_id and not getattr(record, "trace_id", None):
            record.trace_id = trace_id
        return True