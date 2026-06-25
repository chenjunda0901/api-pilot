"""测试计划 / 测试计划步骤 Pydantic 模型。"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TestPlanStepBase(BaseModel):
    """测试计划步骤基类。"""

    step_type: str = Field(default="case", description="步骤类型: case / scene")
    step_id: int = Field(..., ge=1, description="用例或场景 ID")
    order_index: int = Field(default=0, ge=0, description="执行顺序")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("step_type")
    @classmethod
    def validate_step_type(cls, v: str) -> str:
        if v not in ("case", "scene"):
            raise ValueError("step_type 必须是 case 或 scene")
        return v


class TestPlanStepCreate(TestPlanStepBase):
    """创建测试计划步骤。"""


class TestPlanStepUpdate(BaseModel):
    """更新测试计划步骤。"""

    step_type: str | None = None
    step_id: int | None = Field(default=None, ge=1)
    order_index: int | None = Field(default=None, ge=0)
    enabled: bool | None = None


class TestPlanStepOut(TestPlanStepBase):
    """测试计划步骤输出。"""

    id: int
    plan_id: int
    created_at: datetime | None = None


class TestPlanBase(BaseModel):
    """测试计划基类。"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    concurrency: int = Field(default=1, ge=1, le=50, description="并发数")
    timeout_seconds: int = Field(default=30, ge=1, le=3600, description="单步超时（秒）")
    failure_strategy: str = Field(default="continue", description="失败策略: stop_all / continue")
    status: str = Field(default="active", description="状态: active / paused")

    @field_validator("failure_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in ("stop_all", "continue"):
            raise ValueError("failure_strategy 必须是 stop_all 或 continue")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("active", "paused"):
            raise ValueError("status 必须是 active 或 paused")
        return v


class TestPlanCreate(TestPlanBase):
    """创建测试计划请求。"""

    steps: list[TestPlanStepCreate] = Field(default_factory=list, description="计划步骤")


class TestPlanUpdate(BaseModel):
    """更新测试计划请求。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    concurrency: int | None = Field(default=None, ge=1, le=50)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    failure_strategy: str | None = None
    status: str | None = None


class TestPlanOut(TestPlanBase):
    """测试计划输出。"""

    id: int
    project_id: int
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    steps: list[TestPlanStepOut] = Field(default_factory=list)


class TestPlanCloneRequest(BaseModel):
    """测试计划克隆请求。"""

    new_name: str | None = Field(default=None, max_length=200, description="新计划名；为空则自动加 (副本)")


class TestPlanRunRequest(BaseModel):
    """立即执行测试计划请求。"""

    env_id: int | None = Field(default=None, description="环境 ID；为空则使用默认环境")
