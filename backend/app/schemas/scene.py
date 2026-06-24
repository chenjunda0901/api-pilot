from typing import Optional, Literal
from pydantic import BaseModel, Field

from app.schemas.step import StepCreate
from app.schemas.edge import EdgeCreate

OnFailure = Literal["stop", "continue"]
OnError = Literal["stop", "continue"]


class SceneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    category_id: Optional[int] = None
    env_id: Optional[int] = None
    loop_count: int = Field(default=1, ge=1)
    thread_count: int = Field(default=1, ge=1, le=20)
    delay: int = Field(default=0)
    on_failure: OnFailure = Field(default="stop")
    on_error: OnError = Field(default="stop")
    save_detail: str = Field(default="all")
    retry_count: int = Field(default=0)
    global_cookie: int = Field(default=0)
    save_cookie_to_global: int = Field(default=0)
    var_persist_target: Optional[str] = Field(default="environment")
    steps: list[StepCreate] = []
    edges: list[EdgeCreate] = []


class SceneUpdate(BaseModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="")
    category_id: Optional[int] = None
    env_id: Optional[int] = None
    loop_count: int = Field(default=1, ge=1)
    thread_count: int = Field(default=1, ge=1, le=20)
    delay: int = Field(default=0)
    on_failure: OnFailure = Field(default="stop")
    on_error: OnError = Field(default="stop")
    save_detail: str = Field(default="all")
    retry_count: int = Field(default=0)
    global_cookie: int = Field(default=0)
    save_cookie_to_global: int = Field(default=0)
    var_persist_target: Optional[str] = Field(default="environment")
    steps: list[StepCreate] = []
    edges: list[EdgeCreate] = []


class BatchCopyStepsRequest(BaseModel):
    steps: list[dict] = Field(..., description="要复制的步骤列表")


class BatchStepIdsRequest(BaseModel):
    """批量步骤操作请求基类"""
    step_ids: list[int] = Field(..., description="步骤ID列表", min_length=1)


class BatchToggleStepsRequest(BaseModel):
    """批量启用/禁用步骤请求"""
    step_ids: list[int] = Field(..., description="步骤ID列表", min_length=1)
    enabled: bool = Field(True, description="是否启用")
