from typing import Literal

from pydantic import BaseModel, Field


class MemberAddRequest(BaseModel):
    """邀请/添加项目成员"""
    user_id: int = Field(..., description="用户 ID")
    role: Literal["viewer", "member", "editor", "owner"] = Field(default="member", description="角色: viewer/member/editor/owner")


class MemberUpdateRoleRequest(BaseModel):
    """修改成员角色"""
    role: Literal["viewer", "member", "editor", "owner"] = Field(..., description="新角色: viewer/member/editor/owner")


class MemberResponse(BaseModel):
    """成员信息响应"""
    id: int
    user_id: int
    username: str
    nickname: str
    email: str
    role: str
    created_at: str
