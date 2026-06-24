"""统一业务错误码体系（阶段 4：错误处理 + 可观测性）。

码段划分（4 位数字）：
  - 1xxx  认证与权限
  - 2xxx  资源（Not Found / Conflict / 重复）
  - 3xxx  业务校验（断言 / 调度 / Mock / 执行）
  - 4xxx  导入导出与互操作
  - 5xxx  内部错误

字段规范：
  - code:        4 位数字字符串，作为业务唯一标识
  - message:     用户友好消息
  - suggestion:  给前端展示的可执行建议
  - http_status: 默认 HTTP 状态码
  - category:    业务分类，与码段对应
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """业务错误分类。"""

    AUTH = "auth"            # 1xxx
    RESOURCE = "resource"    # 2xxx
    BUSINESS = "business"    # 3xxx
    INTEROP = "interop"      # 4xxx
    INTERNAL = "internal"    # 5xxx


@dataclass(frozen=True)
class ErrorDefinition:
    """业务错误的元数据。"""

    code: str
    message: str
    suggestion: str
    http_status: int
    category: ErrorCategory


# ── 1xxx  认证与权限 ─────────────────────────────────────────────────────

_AUTHS: list[ErrorDefinition] = [
    ErrorDefinition("1001", "认证失败，请重新登录", "请重新登录后重试", 401, ErrorCategory.AUTH),
    ErrorDefinition("1002", "登录信息无效", "请重新登录", 401, ErrorCategory.AUTH),
    ErrorDefinition("1003", "用户名或密码不正确", "请检查输入或重置密码", 401, ErrorCategory.AUTH),
    ErrorDefinition("1004", "用户名已被占用", "请更换用户名", 409, ErrorCategory.AUTH),
    ErrorDefinition("1005", "登录已过期", "请重新登录", 401, ErrorCategory.AUTH),
    ErrorDefinition("1006", "登录信息已失效", "请重新登录", 401, ErrorCategory.AUTH),
    ErrorDefinition("1007", "账号不存在或已被删除", "请确认账号或联系管理员", 401, ErrorCategory.AUTH),
    ErrorDefinition("1008", "无权限执行此操作", "请联系管理员申请权限", 403, ErrorCategory.AUTH),
    ErrorDefinition("1009", "密码强度不足", "请使用至少 6 位的密码", 400, ErrorCategory.AUTH),
    ErrorDefinition("1010", "邮箱已被注册", "请使用其他邮箱或找回账号", 409, ErrorCategory.AUTH),
    ErrorDefinition("1011", "账号已被锁定", "请稍后重试或联系管理员解锁", 423, ErrorCategory.AUTH),
    ErrorDefinition("1012", "禁止访问该项目", "请申请项目权限", 403, ErrorCategory.AUTH),
    ErrorDefinition("1013", "请求签名无效", "请检查 API 签名是否正确", 401, ErrorCategory.AUTH),
]

# ── 2xxx  资源 ───────────────────────────────────────────────────────────

_RESOURCES: list[ErrorDefinition] = [
    ErrorDefinition("2001", "资源不存在或已被删除", "请刷新页面或确认资源 ID", 404, ErrorCategory.RESOURCE),
    ErrorDefinition("2002", "资源名称冲突", "请使用其他名称", 409, ErrorCategory.RESOURCE),
    ErrorDefinition("2003", "资源路径冲突", "请修改接口路径或方法", 409, ErrorCategory.RESOURCE),
    ErrorDefinition("2004", "数据冲突", "请刷新后重试", 409, ErrorCategory.RESOURCE),
    ErrorDefinition("2005", "环境正在被使用", "请先解除引用再删除", 409, ErrorCategory.RESOURCE),
    ErrorDefinition("2006", "资源已被引用", "请先解除引用再删除", 409, ErrorCategory.RESOURCE),
    ErrorDefinition("2007", "报告链接已过期", "请联系分享者重新生成", 410, ErrorCategory.RESOURCE),
    ErrorDefinition("2008", "成员已是项目成员", "请勿重复添加", 409, ErrorCategory.RESOURCE),
    ErrorDefinition("2009", "成员不存在", "请刷新成员列表后重试", 404, ErrorCategory.RESOURCE),
]

# ── 3xxx  业务校验 ──────────────────────────────────────────────────────

_BUSINESS: list[ErrorDefinition] = [
    ErrorDefinition("3001", "断言失败", "请检查响应数据是否符合预期", 422, ErrorCategory.BUSINESS),
    ErrorDefinition("3002", "场景执行失败", "请检查失败步骤的响应", 422, ErrorCategory.BUSINESS),
    ErrorDefinition("3003", "场景步骤不存在", "请刷新场景后重试", 404, ErrorCategory.BUSINESS),
    ErrorDefinition("3004", "场景变量名冲突", "请修改变量名", 409, ErrorCategory.BUSINESS),
    ErrorDefinition("3005", "Mock 规则不存在", "请刷新 Mock 列表后重试", 404, ErrorCategory.BUSINESS),
    ErrorDefinition("3006", "执行环境未选择", "请先选择执行环境", 400, ErrorCategory.BUSINESS),
    ErrorDefinition("3007", "测试计划不存在", "请刷新计划列表", 404, ErrorCategory.BUSINESS),
    ErrorDefinition("3008", "调度任务已存在", "请勿重复创建", 409, ErrorCategory.BUSINESS),
    ErrorDefinition("3009", "调度任务不存在", "请刷新任务列表", 404, ErrorCategory.BUSINESS),
    ErrorDefinition("3010", "调度任务已在运行", "请等待完成后重试", 409, ErrorCategory.BUSINESS),
    ErrorDefinition("3011", "参数错误", "请检查输入参数", 400, ErrorCategory.BUSINESS),
    ErrorDefinition("3012", "权限不足", "请检查角色权限配置", 403, ErrorCategory.BUSINESS),
    ErrorDefinition("3013", "请求超时", "请稍后重试或增加超时阈值", 504, ErrorCategory.BUSINESS),
]

# ── 4xxx  导入导出与互操作 ──────────────────────────────────────────────

_INTEROP: list[ErrorDefinition] = [
    ErrorDefinition("4001", "导入失败", "请检查文件格式后重试", 400, ErrorCategory.INTEROP),
    ErrorDefinition("4002", "文件过大", "请拆分文件（限 10MB）", 413, ErrorCategory.INTEROP),
    ErrorDefinition("4003", "文件解析失败", "请检查文件是否损坏", 400, ErrorCategory.INTEROP),
    ErrorDefinition("4004", "文件内容为空", "请上传有效文件", 400, ErrorCategory.INTEROP),
    ErrorDefinition("4005", "不支持的文件格式", "请使用 Apifox / OpenAPI / Postman 等支持格式", 400, ErrorCategory.INTEROP),
    ErrorDefinition("4006", "导出失败", "请检查项目数据完整性", 500, ErrorCategory.INTEROP),
    ErrorDefinition("4007", "WebHook 投递失败", "请检查 WebHook 配置", 502, ErrorCategory.INTEROP),
    ErrorDefinition("4008", "外部 API 调用失败", "请检查网络和目标服务", 502, ErrorCategory.INTEROP),
]

# ── 5xxx  内部错误 ──────────────────────────────────────────────────────

_INTERNAL: list[ErrorDefinition] = [
    ErrorDefinition("5001", "服务器内部错误", "请稍后重试", 500, ErrorCategory.INTERNAL),
    ErrorDefinition("5002", "数据库错误", "请稍后重试", 500, ErrorCategory.INTERNAL),
    ErrorDefinition("5003", "缓存错误", "请稍后重试", 500, ErrorCategory.INTERNAL),
    ErrorDefinition("5004", "配置错误", "请联系管理员", 500, ErrorCategory.INTERNAL),
    ErrorDefinition("5005", "服务不可用", "请稍后重试", 503, ErrorCategory.INTERNAL),
    ErrorDefinition("5006", "上游依赖不可用", "请稍后重试", 502, ErrorCategory.INTERNAL),
]


# ── 注册表 ──────────────────────────────────────────────────────────────

_REGISTRY: dict[str, ErrorDefinition] = {}
for _bucket in (_AUTHS, _RESOURCES, _BUSINESS, _INTEROP, _INTERNAL):
    for _e in _bucket:
        _REGISTRY[_e.code] = _e


# ── 公开 API ────────────────────────────────────────────────────────────


def resolve(code: str) -> ErrorDefinition:
    """根据 code 查找错误定义；未找到时返回通用 5001。

    >>> resolve("1001").message
    '认证失败，请重新登录'
    """
    return _REGISTRY.get(code) or _REGISTRY["5001"]


def all_codes() -> list[str]:
    """返回所有已注册的错误码（用于自检/测试）。"""
    return list(_REGISTRY.keys())


def make_error_payload(
    code: str,
    *,
    message: str | None = None,
    suggestion: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造统一错误响应体。"""
    definition = resolve(code)
    payload: dict[str, Any] = {
        "code": definition.code,
        "message": message or definition.message,
        "suggestion": suggestion or definition.suggestion,
        "category": definition.category.value,
    }
    if details:
        payload["details"] = details
    return payload


# 向后兼容：原 ErrorCodes 字符串常量映射
COMPAT_MAP: dict[str, str] = {
    # AUTH
    "AUTH_001": "1001",
    "AUTH_002": "1002",
    "AUTH_003": "1003",
    "AUTH_004": "1004",
    "AUTH_005": "1005",
    "AUTH_006": "1006",
    "AUTH_007": "1007",
    "AUTH_008": "1008",
    "AUTH_009": "1009",
    "AUTH_010": "1010",
    "AUTH_011": "1011",
    # API
    "API_001": "2001",
    "API_002": "2002",
    "API_003": "2003",
    "CONFLICT_001": "2004",
    # IMPORT
    "IMPORT_001": "4005",
    "IMPORT_002": "4002",
    "IMPORT_003": "4003",
    "IMPORT_004": "4004",
    "IMPORT_005": "4001",
    # SCENE
    "SCENE_001": "2001",
    "SCENE_002": "3002",
    "SCENE_003": "3003",
    "SCENE_004": "3004",
    # PROJECT
    "PROJECT_001": "2001",
    "PROJECT_002": "1012",
    "PROJECT_003": "2002",
    # ENV
    "ENV_001": "2001",
    "ENV_002": "3006",
    "ENV_003": "2005",
    # CASE
    "CASE_001": "2001",
    # REPORT
    "REPORT_001": "2001",
    "REPORT_002": "2007",
    "REPORT_003": "3007",
    "REPORT_004": "2007",
    # MOCK
    "MOCK_001": "3005",
    # CATEGORY
    "CAT_001": "2001",
    "CAT_002": "2001",
    # MEMBERS
    "MEMBER_001": "2009",
    "MEMBER_002": "2008",
    "MEMBER_003": "2009",
    "PARAM_001": "3011",
    # DOCS
    "DOC_001": "2001",
    "DOC_002": "2007",
    "DOC_003": "1002",
    # INTERNAL
    "INTERNAL_000": "5001",
}


def compat_translate(code: str) -> str:
    """把旧 AUTH_xxx / API_xxx 等业务码翻译为新 4 位数字码。"""
    if code in _REGISTRY:
        return code
    return COMPAT_MAP.get(code, "5001")
