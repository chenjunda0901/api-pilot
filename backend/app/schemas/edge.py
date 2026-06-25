from pydantic import BaseModel, Field


class EdgeCreate(BaseModel):
    edge_id: str = Field(default="")
    source_node_id: str = Field(default="")
    target_node_id: str = Field(default="")
    source_handle: str | None = None
    label: str = Field(default="")
