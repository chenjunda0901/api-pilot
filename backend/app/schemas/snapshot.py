"""快照 / Diff Pydantic 模型。"""

from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ApiSnapshotOut(BaseModel):
    """接口快照输出。"""

    id: int
    api_id: int
    change_type: str = Field(..., description="枚举: create / update / delete")
    change_summary: str = ""
    changed_by: Optional[int] = None
    created_at: Optional[datetime] = None


class ApiSnapshotDetail(ApiSnapshotOut):
    """接口快照详情（含快照数据）。"""

    snapshot_data: dict = Field(default_factory=dict)


class ApiSnapshotDiffResponse(BaseModel):
    """接口快照 diff 响应。"""

    api_id: int
    from_snapshot_id: int
    to_snapshot_id: int
    ops: list[dict[str, Any]] = Field(default_factory=list, description="DiffOp 列表")
    summary: str = ""
    breaking: bool = False


class ApiRestoreRequest(BaseModel):
    """从快照恢复接口请求。"""

    snapshot_id: int = Field(..., ge=1, description="要恢复到的快照 ID")
