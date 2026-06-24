from pydantic import BaseModel, Field, validator
import re


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)
    nickname: str = Field(default="", max_length=100)
    email: str = Field(default="", max_length=255)

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @validator('email')
    def validate_email(cls, v):
        if not v:
            return v
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式不正确')
        return v

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: str
    email: str
    role: str


class ProfileUpdate(BaseModel):
    nickname: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=100)

    @validator('email')
    def validate_email(cls, v: str) -> str:
        if v and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('邮箱格式不正确')
        return v


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=6, max_length=200)


class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)

class ResetPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    reset_code: str = Field(..., min_length=16, max_length=16)
    new_password: str = Field(..., min_length=6, max_length=200)

class AdminResetPasswordRequest(BaseModel):
    """管理员重置用户密码"""
    admin_password: str = Field(..., min_length=1, max_length=200, description="当前登录管理员自己的密码")
    target_user_id: int = Field(..., description="目标用户 ID")
    new_password: str = Field(..., min_length=6, max_length=200, description="为用户设置的新密码")
