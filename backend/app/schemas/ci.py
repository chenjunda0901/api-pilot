"""CI 集成 Pydantic 模型。"""

from typing import Any
from pydantic import BaseModel, Field


class CiTriggerRequest(BaseModel):
    """CI 触发测试计划请求。"""

    plan_id: int = Field(..., ge=1, description="测试计划 ID")
    ref: str | None = Field(default=None, description="代码 ref（分支/tag/sha）")
    idempotency_key: str = Field(..., min_length=1, max_length=200, description="幂等性键（24h 内不重复执行）")


class CiTriggerResponse(BaseModel):
    """CI 触发响应。"""

    run_id: int = Field(..., description="测试运行 ID")
    plan_id: int
    status_url: str = Field(..., description="查询执行状态的 URL")
    cached: bool = Field(default=False, description="是否命中幂等缓存")


class CiWebhookEvent(BaseModel):
    """通用 Webhook 事件（GitHub/GitLab/Jenkins 适配）。"""

    source: str = Field(..., description="事件源: github / gitlab / jenkins / custom")
    event: str = Field(..., description="事件名：push / pull_request / build ...")
    ref: str | None = None
    commit_sha: str | None = None
    plan_id: int | None = Field(default=None, description="可选：直接指定要执行的计划")
    payload: dict[str, Any] = Field(default_factory=dict, description="原始 payload")


class CiRunStatus(BaseModel):
    """CI 执行状态查询响应。"""

    run_id: int
    plan_id: int
    status: str = Field(..., description="状态: pending / running / passed / failed / cancelled")
    total: int = 0
    passed: int = 0
    failed: int = 0
    duration_ms: float = 0.0
    started_at: str | None = None
    finished_at: str | None = None


class CiConfigUpdate(BaseModel):
    """CI 配置更新请求。"""

    regenerate_token: bool = Field(default=False, description="是否重新生成 CI Token")
    plan_ids: list[int] | None = Field(default=None, description="关联的测试计划 ID 列表")


class CiConfigResponse(BaseModel):
    """CI 配置响应。"""

    ci_token: str = Field(..., description="CI Token（脱敏显示）")
    ci_token_set: bool = Field(default=False, description="CI Token 是否已设置")
    webhook_url_template: str = Field(..., description="Webhook URL 模板")
    plan_ids: list[int] = Field(default_factory=list, description="关联的测试计划 ID 列表")
