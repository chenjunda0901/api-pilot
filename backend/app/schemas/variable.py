"""5 层作用域变量 Pydantic 模型。"""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


def _mask_secret(value: str) -> str:
    """对 secret 类型做脱敏：保留前 2 + 后 2 字符。"""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


class VariableBase(BaseModel):
    """变量基类。"""

    scope: str = Field(..., description="作用域: global / project / env / case")
    name: str = Field(..., min_length=1, max_length=200)
    value: str = Field(default="")
    is_secret: bool = Field(default=False, description="是否加密存储")
    description: str = Field(default="")

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        allowed = {"global", "project", "env", "case"}
        if v not in allowed:
            raise ValueError(f"scope 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class VariableCreate(VariableBase):
    """创建变量请求。"""

    scope_id: Optional[int] = Field(default=None, ge=1, description="对应 project/case 的 id；global/env 可为 null")


class VariableUpdate(BaseModel):
    """更新变量请求。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    value: Optional[str] = None
    is_secret: Optional[bool] = None
    description: Optional[str] = None


class VariableOut(VariableBase):
    """变量输出（secret 类型仅显示掩码）。"""

    id: int
    scope_id: Optional[int] = None
    value: str = Field(default="", description="secret 类型只显示掩码")
    is_secret: bool = False
    created_at: Optional[str] = None

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> "VariableOut":
        """重写：secret 类型在序列化时把 value 转掩码。"""
        if hasattr(obj, "is_secret") and getattr(obj, "is_secret", 0):
            raw_value = getattr(obj, "value", "") or ""
            obj = type("_AnonVar", (), {
                "id": getattr(obj, "id"),
                "scope": getattr(obj, "scope"),
                "scope_id": getattr(obj, "scope_id"),
                "name": getattr(obj, "name"),
                "value": _mask_secret(raw_value),
                "is_secret": True,
                "description": getattr(obj, "description", ""),
                "created_at": getattr(obj, "created_at", None),
            })
        return super().model_validate(obj, **kwargs)


class VariableResolveRequest(BaseModel):
    """变量解析请求。"""

    name: str = Field(..., min_length=1, max_length=200, description="要解析的变量名")
    scope_stack: list[dict[str, Any]] = Field(
        default_factory=list,
        description="作用域栈，按优先级排列。例: [{scope:'global',payload:{}},{scope:'project',payload:{}}]",
    )


class VariableResolveResponse(BaseModel):
    """变量解析响应。"""

    name: str
    value: Any = None
    found: bool
    masked: bool = Field(default=False, description="是否因 secret 而脱敏")


class ImportVariableItem(BaseModel):
    """导入变量中的单条记录。"""

    scope: str = Field(..., description="作用域: global / project / env / case")
    scope_id: Optional[int] = Field(default=None, ge=1, description="作用域 ID")
    name: str = Field(..., min_length=1, max_length=200, description="变量名")
    value: str = Field(default="", description="变量值")
    is_secret: bool = Field(default=False, description="是否加密存储")
    description: str = Field(default="", description="变量描述")

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        allowed = {"global", "project", "env", "case"}
        if v not in allowed:
            raise ValueError(f"scope 必须是 {', '.join(sorted(allowed))} 之一")
        return v


class ImportVariablesRequest(BaseModel):
    """导入变量请求。"""

    items: list[ImportVariableItem] = Field(..., min_length=1, description="变量列表")
