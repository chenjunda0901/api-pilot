from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import raise_biz, ErrorCodes
from app.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user, bearer_scheme, revoke_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, ProfileUpdate, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest, AdminResetPasswordRequest
from app.services.auth_service import AuthService, reset_login_attempts
from app.utils.password import hash_password, validate_password_strength, verify_password
from app.utils.response import success

# cookie secure 标志：仅生产环境启用（本地 HTTP 环境下 secure=True 会导致浏览器拒绝 cookie）
COOKIE_SECURE = settings.is_production

REFRESH_TOKEN_COOKIE_NAME = 'api_pilot_refresh_token'
REFRESH_TOKEN_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_CODE_TTL_MINUTES = 10
RESET_CODE_MAX_ATTEMPTS = 5
RESET_CODE_BYTES = 8


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

@router.post("/register", summary="用户注册", description="创建新用户账号，支持注册后自动登录")
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        async with db.begin():
            service = AuthService(db)

            # 邮箱唯一性检查：防止重复注册
            if req.email:
                email_check = await db.execute(select(User).where(User.email == req.email))
                if email_check.scalar_one_or_none():
                    raise_biz(ErrorCodes.AUTH_EMAIL_EXISTS, "邮箱已被注册")

            user = await service.register(req)
            # 注册成功后自动登录：生成 access_token + refresh_token
            from app.middleware.auth import create_access_token, create_refresh_token
            from app.models.refresh_token import RefreshToken as RTModel
            access_token = create_access_token(user.id)
            refresh_token = create_refresh_token(user.id)
            # 保存 refresh token 到 sessions 表
            rt = RTModel(user_id=user.id, token=refresh_token, expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), is_revoked=False)
            db.add(rt)
            # 为新用户创建独立的演示项目副本
            from app.models.project import Project
            from app.models.project_member import ProjectMember
            from app.utils.seed_core import copy_project_to_user
            tpl_result = await db.execute(select(Project).where(Project.global_demo == 1).limit(1))
            template = tpl_result.scalar_one_or_none()
            if template:
                await copy_project_to_user(db, template.id, user.id, nickname=user.nickname or user.username)
            else:
                # 无演示模板时，创建一个空白默认项目，确保用户始终有可用项目
                default_project = Project(
                    name=f"{user.nickname or user.username} 的项目",
                    description="默认项目",
                    created_by=user.id,
                    global_demo=0,
                    is_public=False,
                )
                db.add(default_project)
                await db.flush()
                db.add(ProjectMember(project_id=default_project.id, user_id=user.id, role="owner"))

            # 将 refresh_token 设置为 httpOnly cookie（防 XSS 盗取）
            refresh_token_str = refresh_token
            reg_cookies = None
            if refresh_token_str:
                reg_cookies = [dict(
                    key=REFRESH_TOKEN_COOKIE_NAME,
                    value=refresh_token_str,
                    max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
                    httponly=True,
                    secure=COOKIE_SECURE,
                    samesite="lax",
                    path="/",
                )]

            return success({
                "access_token": access_token,
                "user": {"id": user.id, "username": user.username, "nickname": user.nickname, "email": user.email, "role": user.role, "created_at": str(user.created_at)}
            }, cookies=reg_cookies)
    except IntegrityError as e:
        # 捕获数据库唯一约束冲突（username 或 email 重复）
        await db.rollback()
        error_msg = str(e.orig)
        if "username" in error_msg.lower():
            raise_biz(ErrorCodes.AUTH_USERNAME_EXISTS, "用户名已被注册")
        elif "email" in error_msg.lower():
            raise_biz(ErrorCodes.AUTH_EMAIL_EXISTS, "邮箱已被注册")
        else:
            raise_biz(ErrorCodes.AUTH_USERNAME_EXISTS, "注册信息冲突，请检查后重试")


@router.post("/login", summary="用户登录", description="用户名密码登录，返回 JWT Token")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    
    # 获取客户端信息
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    async with db.begin():
        result = await service.login(req, ip_address=ip_address, user_agent=user_agent)

    # 将 refresh_token 设置为 httpOnly cookie（防 XSS 盗取）
    refresh_token = result.get("refresh_token")
    cookies = None
    if refresh_token:
        cookies = [dict(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=refresh_token,
            max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
            httponly=True,
            secure=COOKIE_SECURE,  # 生产 HTTPS 启用，本地 HTTP 关闭
            samesite="lax",        # 防止 CSRF
            path="/",
        )]
        # refresh_token 已通过 httpOnly cookie 传输，JSON body 中不再包含
        result.pop("refresh_token", None)
    return success(result, cookies=cookies)

@router.post("/refresh", summary="刷新 Token", description="使用 Refresh Token 获取新的 Access Token。支持 Authorization Bearer 头、JSON body 或 Cookie 中的 refresh_token")
@limiter.limit(settings.RATE_LIMIT_REFRESH)
async def refresh(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: AsyncSession = Depends(get_db)):
    # 优先使用 Authorization Bearer，回退到 JSON body，最后回退到 Cookie
    token_str = None
    if credentials and credentials.credentials:
        token_str = credentials.credentials
    if not token_str:
        try:
            body = await request.json()
            token_str = body.get("refresh_token")
        except Exception:
            pass
    if not token_str:
        token_str = request.cookies.get("api_pilot_refresh_token")
    if not token_str:
        raise_biz(ErrorCodes.AUTH_TOKEN_EXPIRED, "缺少 refresh token")
    service = AuthService(db)
    async with db.begin():
        result = await service.refresh(token_str)
    # 旋转后的 refresh_token 也通过 httpOnly cookie 更新
    new_refresh_token = result.get("refresh_token")
    cookies = None
    if new_refresh_token:
        cookies = [dict(
            key=REFRESH_TOKEN_COOKIE_NAME,
            value=new_refresh_token,
            max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
            httponly=True,
            secure=COOKIE_SECURE,  # 生产 HTTPS 启用，本地 HTTP 关闭
            samesite="lax",
            path="/",
        )]
        # refresh_token 已通过 httpOnly cookie 传输，JSON body 中不再包含
        result.pop("refresh_token", None)
    return success(result, cookies=cookies)


@router.post("/logout", summary="退出登录", description="清除当前登录状态并吊销 Access Token")
@limiter.limit("10/minute")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    async with db.begin():
        await service.logout(current_user)
        await revoke_token(db, credentials.credentials)
    return success(message="退出登录成功", delete_cookies=[REFRESH_TOKEN_COOKIE_NAME])

@router.get("/me", summary="获取当前用户信息", description="返回当前登录用户的个人信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return success({"id": current_user.id, "username": current_user.username,
                   "nickname": current_user.nickname, "email": current_user.email,
                   "role": current_user.role, "created_at": str(current_user.created_at)})


@router.put("/me", summary="更新个人信息", description="修改当前用户的昵称等基本信息")
@limiter.limit("10/minute")
async def update_me(request: Request, req: ProfileUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    async with db.begin():
        user = await service.update_profile(current_user, req.nickname, req.email)
    return success({"id": user.id, "username": user.username,
                   "nickname": user.nickname, "email": user.email,
                   "role": user.role, "created_at": str(user.created_at)})


@router.put("/password", summary="修改密码", description="验证旧密码后更新为新密码")
@limiter.limit("3/minute")
async def change_password(req: PasswordChange, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    async with db.begin():
        await service.change_password(current_user, req.old_password, req.new_password)
    return success(message="密码修改成功")

@router.post("/forgot-password", summary="忘记密码", description="请求密码重置码（内部工具直接展示，无需邮件）")
@limiter.limit("3/minute")
async def forgot_password(req: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.get_user_by_username(req.username)
    
    # 统一返回消息，防止用户信息泄露
    unified_message = "如果账号存在，重置码已生成"
    
    if not user:
        # 账号不存在时，延迟一小段时间再返回，防止时序攻击
        import asyncio
        await asyncio.sleep(0.5)
        # 返回与成功时一致的 JSON 结构，防止用户名枚举
        return success({
            "reset_code": "0" * (RESET_CODE_BYTES * 2),
            "expires_in": RESET_CODE_TTL_MINUTES * 60,
            "message": unified_message,
        })

    async with db.begin():
        await db.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.purpose == "password_reset",
            )
        )

        code = secrets.token_hex(RESET_CODE_BYTES)
        db.add(RefreshToken(
            user_id=user.id,
            token=f"password-reset:{user.id}:{datetime.now(timezone.utc).timestamp()}",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES),
            is_revoked=False,
            purpose="password_reset",
            reset_code_hash=hash_password(code),
            reset_attempts=0,
        ))

    # 任何环境都不返回完整的明文重置码，仅返回前4位用于人工核对
    masked_code = code[:4] + "*" * (len(code) - 4)
    return success({
        "reset_code": masked_code,
        "expires_in": RESET_CODE_TTL_MINUTES * 60,
        "message": "重置码已生成，10分钟内有效"
    })


@router.post("/reset-password", summary="重置密码", description="使用重置码设置新密码")
@limiter.limit("3/minute")
async def reset_password(req: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.get_user_by_username(req.username)
    if not user:
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "重置码无效或已过期")

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.purpose == "password_reset",
            ~RefreshToken.is_revoked,
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "重置码无效或已过期")
    if datetime.now(timezone.utc) > _to_utc(stored.expires_at):
        await db.delete(stored)
        await db.flush()
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "重置码已过期，请重新申请")

    # 原子递增尝试次数（防 TOCTOU 竞争条件）
    import sqlalchemy as sa
    update_result = await db.execute(
        sa.update(RefreshToken)
        .where(RefreshToken.id == stored.id)
        .where(RefreshToken.reset_attempts < RESET_CODE_MAX_ATTEMPTS)
        .where(~RefreshToken.is_revoked)
        .values(reset_attempts=RefreshToken.reset_attempts + 1)
    )
    if update_result.rowcount == 0:
        # 尝试次数已达上限（另一请求已递增到阈值）
        # 删除该重置码，避免后续测试
        await db.execute(sa.delete(RefreshToken).where(RefreshToken.id == stored.id))
        await db.flush()
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "重置码尝试次数过多，请重新申请")
    await db.flush()
    # 重新读取以获取最新 reset_attempts
    await db.refresh(stored)

    if not verify_password(req.reset_code, stored.reset_code_hash):
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "重置码错误")
    if not validate_password_strength(req.new_password):
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "密码至少 8 位，必须包含大写字母、小写字母和数字")

    # 防回滚：不允许设置与当前密码相同的新密码
    if verify_password(req.new_password, user.password_hash):
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "新密码不能与当前密码相同")

    user.password_hash = hash_password(req.new_password)
    await db.delete(stored)
    await service.logout(user)
    # 密码重置后清除登录锁定计数器，避免用户重置密码后仍被锁定
    reset_login_attempts(req.username)
    await db.flush()
    return success(message="密码重置成功，请重新登录")


@router.post("/admin/reset-password", summary="管理员重置密码", description="管理员验证自身密码后，强制重置指定用户的密码（仅 admin 角色可调用）")
@limiter.limit("3/minute")
async def admin_reset_password(
    req: AdminResetPasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员强制重置指定用户的密码。"""
    # 仅 admin 系统角色可调用
    if current_user.role != "admin":
        raise_biz(ErrorCodes.AUTH_FORBIDDEN, "仅管理员可执行此操作")

    # 禁止管理员重置自己的密码
    if req.target_user_id == current_user.id:
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "不能重置自己的密码")

    # 验证管理员自身密码
    if not verify_password(req.admin_password, current_user.password_hash):
        raise_biz(ErrorCodes.AUTH_INVALID_CREDENTIALS, "管理员密码错误")

    # 查询目标用户
    target_user = await db.get(User, req.target_user_id)
    if not target_user:
        raise_biz(ErrorCodes.USER_NOT_FOUND, "目标用户不存在")

    # 验证新密码强度
    if not validate_password_strength(req.new_password):
        raise_biz(ErrorCodes.AUTH_WEAK_PASSWORD, "密码至少 8 位，必须包含大写字母、小写字母和数字")

    # 更新密码
    async with db.begin():
        target_user.password_hash = hash_password(req.new_password)

    return success(message=f"用户 {target_user.username} 的密码已重置")
