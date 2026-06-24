"""
HTTP 客户端工具 - 带重试、熔断、超时控制
用于 API 执行器中的外部 HTTP 请求
"""

import asyncio
import ipaddress
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse

import threading
import httpx

from app.config import settings

logger = logging.getLogger("api_pilot.http")

# 默认超时配置
DEFAULT_TIMEOUT = 30.0       # 默认超时 30 秒
CONNECT_TIMEOUT = 10.0        # 连接超时 10 秒
READ_TIMEOUT = 60.0          # 读取超时 60 秒



def validate_request_url(url: str) -> str:
    """SSRF 防护：检查 URL 的 hostname 是否在白名单 ALLOWED_API_HOSTS 中。

    Args:
        url: 待校验的完整 URL

    Returns:
        校验通过的原始 URL

    Raises:
        ValueError: URL 无效或 hostname 不在白名单中
    """

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的 URL Scheme: {parsed.scheme}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("无效 URL：无法解析 hostname")

    allowed_raw = settings.ALLOWED_API_HOSTS
    allowed_items = [h.strip() for h in allowed_raw.split(",") if h.strip()]

    # 先尝试精确匹配 + 通配符后缀匹配
    for item in allowed_items:
        if item == hostname:
            return url
        # 通配符域名匹配：*.example.com 匹配 sub.example.com
        if item.startswith("*.") and hostname.endswith(item[1:]):
            return url

    # 尝试 IP / CIDR 匹配
    try:
        addr = ipaddress.ip_address(hostname)
        for item in allowed_items:
            try:
                network = ipaddress.ip_network(item, strict=False)
                if addr in network:
                    return url
            except ValueError:
                continue
    except ValueError:
        pass

    raise ValueError(
        f"SSRF 防护：目标主机 '{hostname}' 不在 ALLOWED_API_HOSTS 白名单中。"
        f" 允许的值: {allowed_raw}"
    )




class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"         # 正常状态，请求通过
    OPEN = "open"            # 熔断状态，请求被拒绝
    HALF_OPEN = "half_open"  # 半开状态，尝试放行部分请求


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5       # 失败次数阈值
    recovery_timeout: int = 60       # 恢复超时（秒）
    half_open_max_calls: int = 3     # 半开状态允许的请求数


@dataclass
class CircuitBreaker:
    """熔断器实现"""
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    
    def record_success(self):
        """记录成功"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            # HALF_OPEN 下任意一次成功即表明下游已恢复，立即关闭熔断器
            self.state = CircuitState.CLOSED
            logger.info("熔断器恢复：请求恢复正常")
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"熔断器开启：连续 {self.failure_count} 次失败")
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # 检查是否超过恢复超时
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = self.config.half_open_max_calls
                    logger.info("熔断器进入半开状态：尝试放行请求")
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls > 0:
                self.half_open_calls -= 1
                return True
            return False
        
        return False


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3              # 最大重试次数
    base_delay: float = 0.5            # 基础延迟（秒）
    max_delay: float = 10.0            # 最大延迟（秒）
    exponential_base: float = 2.0      # 指数退避基数
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避 + 抖动）"""
        import random
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        # 添加 20% 随机抖动，避免惊群效应
        jitter = delay * 0.2 * (random.random() - 0.5)
        return delay + jitter


class HTTPClient:
    """
    带重试和熔断的 HTTP 客户端
    
    特性：
    - 自动重试（指数退避 + 抖动）
    - 熔断器保护
    - 超时控制
    - 连接池复用
    """
    
    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        
        # 创建共享的 httpx 客户端
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT,
                read=READ_TIMEOUT,
                write=10.0,
                pool=5.0,
            ),
            limits=limits,
            follow_redirects=True,
            max_redirects=5,
        )
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        content: Optional[bytes] = None,
        timeout: Optional[float] = None,
        skip_retry: bool = False,
    ) -> httpx.Response:
        """
        发送 HTTP 请求，自动重试和熔断保护
        """
        # 检查熔断器
        if not self.circuit_breaker.can_execute():
            raise HTTPClientError(
                "Circuit breaker is open",
                status_code=503,
                retry_after=self.circuit_breaker.config.recovery_timeout,
            )
        
        # SSRF 防护：验证目标 URL 是否在白名单中
        try:
            validate_request_url(url)
        except ValueError as e:
            raise HTTPClientError(
                str(e),
                status_code=403,
            )
        
        async def _do_request():
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                    content=content,
                    timeout=timeout or self.timeout,
                )
                
                # 根据状态码判断是否需要重试
                if response.status_code >= 500:
                    raise RetryableError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )
                
                self.circuit_breaker.record_success()
                return response
                
            except (httpx.TimeoutException, httpx.ConnectError, RetryableError) as e:
                self.circuit_breaker.record_failure()
                raise
        
        # 执行请求（带重试）
        last_error = None
        for attempt in range(self.retry_config.max_attempts if not skip_retry else 1):
            try:
                return await _do_request()
            except RetryableError as e:
                last_error = e
                if attempt < self.retry_config.max_attempts - 1:
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(f"请求失败，{delay:.2f}秒后重试 ({attempt + 1}/{self.retry_config.max_attempts}): {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"请求重试失败，已达到最大次数: {e}")
        
        raise last_error or HTTPClientError("Request failed")
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)
    
    async def close(self):
        """关闭客户端，释放连接"""
        await self._client.aclose()
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None,
        }


class RetryableError(Exception):
    """可重试的错误"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class HTTPClientError(Exception):
    """HTTP 客户端错误"""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


# 全局 HTTP 客户端实例（单例）
_client_lock = threading.Lock()
_global_client: Optional[HTTPClient] = None


def get_http_client() -> HTTPClient:
    """获取全局 HTTP 客户端实例（线程安全）"""
    global _global_client
    if _global_client is None:
        with _client_lock:
            if _global_client is None:
                _global_client = HTTPClient(
                    retry_config=RetryConfig(
                        max_attempts=3,
                        base_delay=0.5,
                        max_delay=5.0,
                    ),
                    circuit_breaker=CircuitBreaker(
                        config=CircuitBreakerConfig(
                            failure_threshold=5,
                            recovery_timeout=60,
                        )
                    ),
                )
    return _global_client


async def close_http_client():
    """关闭全局 HTTP 客户端"""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None