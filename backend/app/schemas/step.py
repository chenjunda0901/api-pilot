from pydantic import BaseModel, Field


class StepCreate(BaseModel):
    node_id: str = Field(default="")
    node_type: str = Field(default="request")
    label: str = Field(default="")
    position_x: float = Field(default=0)
    position_y: float = Field(default=0)
    api_id: int | None = None
    test_case_id: int | None = None
    sort_order: int = Field(default=0)
    enabled: bool = Field(default=True)
    timeout: int = Field(default=30000)
    retry_count: int = Field(default=0)
    request_body: str | None = None
    headers: str | None = None
    query_params: str | None = None
    assertions: str | None = None
    extract_vars: str | None = None
    condition_expression: str | None = None
    loop_count: int | None = None
    loop_variable: str | None = None
    wait_duration: int | None = None
    wait_mode: str | None = None
    wait_min: int | None = None
    wait_max: int | None = None
    parallel_group: int = Field(
        default=0, description="并行组ID：相同组号的步骤并发执行，0=顺序执行"
    )


class StepUpdate(BaseModel):
    node_id: str = Field(default="")
    node_type: str = Field(default="request")
    label: str = Field(default="")
    position_x: float = Field(default=0)
    position_y: float = Field(default=0)
    api_id: int | None = None
    test_case_id: int | None = None
    sort_order: int = Field(default=0)
    enabled: bool = Field(default=True)
    timeout: int = Field(default=30000)
    retry_count: int = Field(default=0)
    request_body: str | None = None
    headers: str | None = None
    query_params: str | None = None
    assertions: str | None = None
    extract_vars: str | None = None
    condition_expression: str | None = None
    loop_count: int | None = None
    loop_variable: str | None = None
    wait_duration: int | None = None
    wait_mode: str | None = None
    wait_min: int | None = None
    wait_max: int | None = None
