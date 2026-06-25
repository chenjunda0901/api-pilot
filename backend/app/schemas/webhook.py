"""出站 Webhook Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class WebhookBase(BaseModel):
    """Webhook 基类。"""

    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=500)
    secret: str | None = Field(default=None, max_length=255, description="HMAC 签名密钥")
    channel: str = Field(default="custom", description="渠道: feishu / dingtalk / wechat / slack / email / custom")
    events: list[str] = Field(default_factory=list, description="订阅事件列表，如 test_plan.failed")
    template: str = Field(default="", description="Jinja2 模板（可选）")
    enabled: bool = Field(default=True)

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        allowed = {"feishu", "dingtalk", "wechat", "slack", "email", "custom"}
        if v not in allowed:
            raise ValueError(f"channel 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class WebhookCreate(WebhookBase):
    """创建 Webhook 请求。"""


class WebhookUpdate(BaseModel):
    """更新 Webhook 请求。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    secret: str | None = Field(default=None, max_length=255)
    channel: str | None = None
    events: list[str] | None = None
    template: str | None = None
    enabled: bool | None = None


class WebhookOut(WebhookBase):
    """Webhook 输出（secret 默认脱敏）。"""

    id: int
    project_id: int
    secret_masked: str | None = Field(default=None, description="脱敏后的 secret")
    created_by: int | None = None
    created_at: datetime | None = None


class WebhookTestRequest(BaseModel):
    """测试 Webhook 发送请求。"""

    event: str = Field(default="webhook.test", description="模拟事件名")
    payload: dict = Field(default_factory=dict, description="模拟事件负载")


class WebhookDeliveryOut(BaseModel):
    """Webhook 投递历史输出。"""

    id: int
    webhook_id: int
    channel: str
    event: str
    status: str
    retry_count: int
    sent_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime | None = None
