"""全局异常框架 —— BizError + ErrorCodes + raise_biz + HTTP 状态码自动映射。

阶段 4 增强：
  - BizError 携带 ``suggestion``（用户友好的解决建议）字段
  - 通过 ``app.core.errors`` 4 位数字业务码体系统一错误码
  - 保留旧 ``ErrorCodes.AUTH_xxx`` / ``API_xxx`` 等字符串常量做向下兼容
  - 新增 ``RequestTimeoutError`` / ``IdempotencyConflictError`` 等阶段 4 异常
"""

from __future__ import annotations

from typing import Any

from app.core import errors as _errors

__all__ = [
    "BizError",
    "ErrorCodes",
    "raise_biz",
    "ERROR_MESSAGES",
    "_resolve_http_status",
    "RequestTimeoutError",
    "IdempotencyConflictError",
    "TransactionError",
    "SoftDeleteError",
]


class ErrorCodes:
    """旧字符串错误码（向下兼容）。

    新代码请直接使用 ``app.core.errors`` 中的 4 位数字码；
    本类仅保留旧值并通过 ``raise_biz`` 自动翻译为新码。
    """

    # Auth
    AUTH_TOKEN_MISSING = "AUTH_001"
    AUTH_INVALID_TOKEN = "AUTH_002"
    AUTH_INVALID_CREDENTIALS = "AUTH_003"
    AUTH_USERNAME_EXISTS = "AUTH_004"
    AUTH_TOKEN_EXPIRED = "AUTH_005"
    AUTH_TOKEN_REVOKED = "AUTH_006"
    AUTH_USER_NOT_FOUND = "AUTH_007"
    AUTH_FORBIDDEN = "AUTH_008"
    AUTH_WEAK_PASSWORD = "AUTH_009"
    AUTH_EMAIL_EXISTS = "AUTH_010"
    AUTH_ACCOUNT_LOCKED = "AUTH_011"

    # API
    API_NOT_FOUND = "API_001"
    API_NAME_DUPLICATE = "API_002"
    API_PATH_DUPLICATE = "API_003"
    CONFLICT = "CONFLICT_001"

    # Import
    IMPORT_INVALID_FORMAT = "IMPORT_001"
    IMPORT_FILE_TOO_LARGE = "IMPORT_002"
    IMPORT_PARSE_ERROR = "IMPORT_003"
    IMPORT_EMPTY_CONTENT = "IMPORT_004"
    IMPORT_EXECUTE_ERROR = "IMPORT_005"

    # Scene
    SCENE_NOT_FOUND = "SCENE_001"
    SCENE_STEP_FAILED = "SCENE_002"
    SCENE_STEP_NOT_FOUND = "SCENE_003"
    SCENE_VARIABLE_DUPLICATE = "SCENE_004"
    SCENE_NAME_DUPLICATE = "SCENE_005"

    # Project
    PROJECT_NOT_FOUND = "PROJECT_001"
    PROJECT_FORBIDDEN = "PROJECT_002"
    PROJECT_NAME_EXISTS = "PROJECT_003"

    # Environment
    ENV_NOT_FOUND = "ENV_001"
    ENV_REQUIRED = "ENV_002"
    ENV_IN_USE = "ENV_003"
    ENV_FORBIDDEN = "ENV_004"

    # Case
    CASE_NOT_FOUND = "CASE_001"

    # Report
    REPORT_NOT_FOUND = "REPORT_001"
    REPORT_LINK_INVALID = "REPORT_002"
    REPORT_NO_SCENE = "REPORT_003"
    REPORT_LINK_EXPIRED = "REPORT_004"

    # Mock
    MOCK_NOT_FOUND = "MOCK_001"

    # Category
    CATEGORY_NOT_FOUND = "CAT_001"
    SCENE_CATEGORY_NOT_FOUND = "CAT_002"

    # Members
    PROJECT_MEMBER_NOT_FOUND = "MEMBER_001"
    PROJECT_MEMBER_EXISTS = "MEMBER_002"
    USER_NOT_FOUND = "MEMBER_003"
    PARAM_ERROR = "PARAM_001"

    # Docs
    DOC_NOT_FOUND = "DOC_001"
    DOC_EXPIRED = "DOC_002"
    DOC_PASSWORD_WRONG = "DOC_003"

    # Internal
    INTERNAL_ERROR = "INTERNAL_000"
    # Dataset
    DATASET_NOT_FOUND = "DATASET_001"


ERROR_MESSAGES: dict[str, str] = {
    ErrorCodes.AUTH_TOKEN_MISSING: "登录后即可执行此操作",
    ErrorCodes.AUTH_INVALID_TOKEN: "登录信息无效，请重新登录",
    ErrorCodes.AUTH_INVALID_CREDENTIALS: "用户名或密码不正确",
    ErrorCodes.AUTH_USERNAME_EXISTS: "用户名已被占用",
    ErrorCodes.AUTH_TOKEN_EXPIRED: "登录已过期，请重新登录",
    ErrorCodes.AUTH_TOKEN_REVOKED: "登录信息已失效，请重新登录",
    ErrorCodes.AUTH_USER_NOT_FOUND: "账号不存在或已被删除",
    ErrorCodes.AUTH_FORBIDDEN: "需要管理员权限才能执行此操作",
    ErrorCodes.AUTH_WEAK_PASSWORD: "密码强度不足，须至少 6 位",
    ErrorCodes.AUTH_EMAIL_EXISTS: "邮箱已被注册",
    ErrorCodes.AUTH_ACCOUNT_LOCKED: "账号已被锁定，请稍后重试",
    ErrorCodes.API_NOT_FOUND: "接口不存在或已被删除",
    ErrorCodes.API_NAME_DUPLICATE: "同接口目录下已有同名接口",
    ErrorCodes.API_PATH_DUPLICATE: "同接口目录下相同路径和方法的接口已存在",
    ErrorCodes.CONFLICT: "数据已被其他人修改，请刷新后重试",
    ErrorCodes.IMPORT_INVALID_FORMAT: "无法识别该文件，请上传 Apifox 导出的 JSON 文件",
    ErrorCodes.IMPORT_FILE_TOO_LARGE: "文件过大（超过 10MB），请拆分后重新上传",
    ErrorCodes.IMPORT_PARSE_ERROR: "文件解析失败，请检查文件是否损坏",
    ErrorCodes.IMPORT_EMPTY_CONTENT: "文件内容不能为空",
    ErrorCodes.IMPORT_EXECUTE_ERROR: "导入执行失败，请检查文件内容后重试",
    ErrorCodes.SCENE_NOT_FOUND: "测试场景不存在或已被删除",
    ErrorCodes.SCENE_STEP_FAILED: "场景执行中断，某步骤未通过",
    ErrorCodes.SCENE_STEP_NOT_FOUND: "场景步骤不存在",
    ErrorCodes.SCENE_VARIABLE_DUPLICATE: "变量名冲突",
    ErrorCodes.SCENE_NAME_DUPLICATE: "场景名称已存在",
    ErrorCodes.PROJECT_NOT_FOUND: "项目不存在或已被删除",
    ErrorCodes.PROJECT_FORBIDDEN: "无权访问该项目",
    ErrorCodes.PROJECT_NAME_EXISTS: "同名项目已存在",
    ErrorCodes.ENV_NOT_FOUND: "环境不存在或已被删除",
    ErrorCodes.ENV_REQUIRED: "请先选择执行环境",
    ErrorCodes.ENV_IN_USE: "该环境正在被使用",
    ErrorCodes.ENV_FORBIDDEN: "环境不属于该项目",
    ErrorCodes.CASE_NOT_FOUND: "测试用例不存在或已被删除",
    ErrorCodes.REPORT_NOT_FOUND: "测试报告不存在或已被删除",
    ErrorCodes.REPORT_LINK_INVALID: "分享链接无效或已过期",
    ErrorCodes.REPORT_NO_SCENE: "该报告无关联场景",
    ErrorCodes.REPORT_LINK_EXPIRED: "分享链接已过期",
    ErrorCodes.MOCK_NOT_FOUND: "Mock 规则不存在或已被删除",
    ErrorCodes.CATEGORY_NOT_FOUND: "接口目录不存在或已被删除",
    ErrorCodes.SCENE_CATEGORY_NOT_FOUND: "场景目录不存在或已被删除",
    ErrorCodes.PROJECT_MEMBER_NOT_FOUND: "项目成员不存在",
    ErrorCodes.PROJECT_MEMBER_EXISTS: "该用户已是项目成员",
    ErrorCodes.USER_NOT_FOUND: "用户不存在",
    ErrorCodes.PARAM_ERROR: "参数错误，请检查输入",
    ErrorCodes.DOC_NOT_FOUND: "文档不存在或已失效",
    ErrorCodes.DOC_EXPIRED: "文档已过期",
    ErrorCodes.DOC_PASSWORD_WRONG: "密码错误",
    ErrorCodes.INTERNAL_ERROR: "服务器出了点问题，请稍后重试",
    ErrorCodes.DATASET_NOT_FOUND: "数据集不存在或已被删除",
}


# --- HTTP 状态码自动映射（兼容旧字符串码）---
# 旧码 → 状态码
_CODE_STATUS_MAP = {
    ErrorCodes.AUTH_FORBIDDEN: 403,
    ErrorCodes.PROJECT_FORBIDDEN: 403,
    ErrorCodes.PROJECT_NAME_EXISTS: 409,
    ErrorCodes.CONFLICT: 409,
    ErrorCodes.API_NAME_DUPLICATE: 409,
    ErrorCodes.API_PATH_DUPLICATE: 409,
    ErrorCodes.SCENE_NAME_DUPLICATE: 409,
    ErrorCodes.AUTH_TOKEN_MISSING: 401,
    ErrorCodes.AUTH_INVALID_TOKEN: 401,
    ErrorCodes.AUTH_INVALID_CREDENTIALS: 401,
    ErrorCodes.AUTH_TOKEN_EXPIRED: 401,
    ErrorCodes.AUTH_TOKEN_REVOKED: 401,
    ErrorCodes.AUTH_USER_NOT_FOUND: 401,
    ErrorCodes.REPORT_LINK_EXPIRED: 410,
}

_PREFIX_STATUS_MAP = [
    ("NOT_FOUND", 404),
    ("_FORBIDDEN", 403),
]


def _resolve_http_status(code: str) -> int:
    """根据业务错误码推导最匹配的 HTTP 状态码。

    兼容两类：
      - 4 位数字新码：直接读 errors.ErrorDefinition.http_status
      - 旧字符串码：精确 → 前缀 → 400 兜底
    """
    if code.isdigit() and len(code) == 4:
        return _errors.resolve(code).http_status
    if code in _CODE_STATUS_MAP:
        return _CODE_STATUS_MAP[code]
    for prefix, status in _PREFIX_STATUS_MAP:
        if prefix in code:
            return status
    return 400


def _normalize_code(code: str) -> str:
    """把旧字符串码翻译为新 4 位数字码。"""
    return _errors.compat_translate(code)


class BizError(Exception):
    """业务异常——带错误码、用户友好的消息与建议。

    新增 ``suggestion`` 字段（用户友好的解决建议），
    取自 ``app.core.errors.ErrorDefinition.suggestion``。

    设计：``code`` 字段保留开发者传入的原始字面值（向后兼容旧字符串
    错误码），同时缓存 ``normalized_code``（4 位数字码）供 HTTP 响应
    层使用。开发者写 ``raise_biz(ErrorCodes.AUTH_003)`` 与
    ``raise_biz("1003")`` 都会得到一致的对外响应。
    """

    def __init__(
        self,
        code: str,
        message: str = "",
        detail: str = "",
        suggestion: str = "",
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.normalized_code = _normalize_code(code)
        definition = _errors.resolve(self.normalized_code)
        self.message = message or ERROR_MESSAGES.get(code) or definition.message
        self.suggestion = suggestion or definition.suggestion
        self.detail = detail
        self.details = details or {}
        self.category = definition.category.value
        self.http_status = _resolve_http_status(self.normalized_code)

    def to_payload(self) -> dict[str, Any]:
        """序列化为统一错误响应体（对外使用标准化 4 位数字码）。"""
        payload: dict[str, Any] = {
            "code": self.normalized_code,
            "message": self.message,
            "suggestion": self.suggestion,
            "category": self.category,
        }
        if self.detail:
            payload["detail"] = self.detail
        if self.details:
            payload["details"] = self.details
        return payload

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" + (f" ({self.detail})" if self.detail else "")


def raise_biz(code: str, detail: str = "", **kwargs: Any) -> None:
    """抛出业务异常——BizError.__init__ 自动查找友好消息并推导 HTTP 状态码。"""
    raise BizError(code=code, detail=detail, **kwargs)


# ── 阶段 4 新增异常 ──────────────────────────────────────────────────────


class RequestTimeoutError(BizError):
    """请求整体超时（中间件 504）。"""

    def __init__(self, detail: str = "", timeout_seconds: float | None = None) -> None:
        details: dict[str, Any] = {}
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(code="3013", detail=detail or "请求处理超时", details=details)


class IdempotencyConflictError(BizError):
    """同一 Idempotency-Key 关联到了不同的请求体。"""

    def __init__(self, detail: str = "") -> None:
        super().__init__(code="2004", detail=detail or "Idempotency-Key 已被其他请求使用")


class TransactionError(BizError):
    """事务回滚异常。"""

    def __init__(self, detail: str = "") -> None:
        super().__init__(code="5002", detail=detail or "数据库事务回滚")


class SoftDeleteError(BizError):
    """软删除一致性错误。"""

    def __init__(self, detail: str = "") -> None:
        super().__init__(code="2001", detail=detail or "资源已删除或软删除状态异常")
