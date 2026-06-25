"""定时任务 Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ScheduleBase(BaseModel):
    """定时任务基类。"""

    plan_id: int = Field(..., ge=1, description="关联测试计划 ID")
    cron_expression: str = Field(..., min_length=1, max_length=100, description="5 段 cron 表达式")
    timezone: str = Field(default="UTC", max_length=50, description="IANA 时区，如 Asia/Shanghai")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cron_expression 不能为空")
        # 简单 5 段校验（具体合法性由 scheduler 服务校验）
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("cron 表达式必须为 5 段（分 时 日 月 周）")
        return v


class ScheduleCreate(ScheduleBase):
    """创建定时任务请求。"""


class ScheduleUpdate(BaseModel):
    """更新定时任务请求。"""

    cron_expression: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)
    enabled: bool | None = None


class ScheduleOut(ScheduleBase):
    """定时任务输出。"""

    id: int
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_by: int | None = None
    created_at: datetime | None = None
