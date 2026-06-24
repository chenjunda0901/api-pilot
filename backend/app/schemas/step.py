from typing import Optional
from pydantic import BaseModel, Field


class StepCreate(BaseModel):
    node_id: str = Field(default="")
    node_type: str = Field(default="request")
    label: str = Field(default="")
    position_x: float = Field(default=0)
    position_y: float = Field(default=0)
    api_id: Optional[int] = None
    test_case_id: Optional[int] = None
    sort_order: int = Field(default=0)
    enabled: bool = Field(default=True)
    timeout: int = Field(default=30000)
    retry_count: int = Field(default=0)
    request_body: Optional[str] = None
    headers: Optional[str] = None
    query_params: Optional[str] = None
    assertions: Optional[str] = None
    extract_vars: Optional[str] = None
    condition_expression: Optional[str] = None
    loop_count: Optional[int] = None
    loop_variable: Optional[str] = None
    wait_duration: Optional[int] = None
    wait_mode: Optional[str] = None
    wait_min: Optional[int] = None
    wait_max: Optional[int] = None
    parallel_group: int = Field(
        default=0, description="并行组ID：相同组号的步骤并发执行，0=顺序执行"
    )


class StepUpdate(BaseModel):
    node_id: str = Field(default="")
    node_type: str = Field(default="request")
    label: str = Field(default="")
    position_x: float = Field(default=0)
    position_y: float = Field(default=0)
    api_id: Optional[int] = None
    test_case_id: Optional[int] = None
    sort_order: int = Field(default=0)
    enabled: bool = Field(default=True)
    timeout: int = Field(default=30000)
    retry_count: int = Field(default=0)
    request_body: Optional[str] = None
    headers: Optional[str] = None
    query_params: Optional[str] = None
    assertions: Optional[str] = None
    extract_vars: Optional[str] = None
    condition_expression: Optional[str] = None
    loop_count: Optional[int] = None
    loop_variable: Optional[str] = None
    wait_duration: Optional[int] = None
    wait_mode: Optional[str] = None
    wait_min: Optional[int] = None
    wait_max: Optional[int] = None
