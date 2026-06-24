"""运行指标聚合 Pydantic 模型。"""

from pydantic import BaseModel


class ApiPercentileOut(BaseModel):
    """接口百分位响应。"""

    api_id: int
    days: int
    count: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


class BaselineAlertOut(BaseModel):
    """基线告警响应。"""

    api_id: int
    threshold_ms: float
    current_p95_ms: float
    triggered: bool
    message: str = ""


class SlowRequestOut(BaseModel):
    """慢请求条目输出。"""

    scope: str
    scope_id: int
    duration_ms: float
    recorded_at: str


class DashboardOut(BaseModel):
    """项目仪表盘聚合响应。"""

    project_id: int
    days: int
    total_requests: int
    error_count: int
    error_rate: float
    avg_p95_ms: float
    slow_count: int
    plan_runs: int
