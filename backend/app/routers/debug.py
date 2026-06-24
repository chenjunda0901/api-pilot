"""调试工具路由 — 用于 E2E 测试验证请求发送。

仅开发环境可用，生产环境不加载。
"""

from fastapi import APIRouter, HTTPException, Request
from app.utils.response import success
from app.config import settings

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.api_route("/echo", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    summary="Echo 端点", description="原样返回请求信息，用于测试执行引擎的请求发送是否正确")
async def echo(request: Request):
    """Return request details for testing purposes."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not Found")
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8") if body_bytes else ""

    form_data = {}
    try:
        form = await request.form()
        form_data = {k: str(v) for k, v in form.items()}
    except (ValueError, UnicodeDecodeError):
        pass

    files_info = {}
    try:
        form = await request.form()
        for k, v in form.items():
            import typing
            if isinstance(v, typing.IO) or hasattr(v, "read"):
                content = v.file.read() if hasattr(v, "file") else v.read()
                files_info[k] = {
                    "filename": getattr(v, "filename", None) or getattr(v, "name", None),
                    "size": len(content),
                    "content_type": getattr(v, "content_type", None),
                }
    except (ValueError, UnicodeDecodeError, AttributeError):
        pass

    return success({
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "body": body_text,
        "form": form_data,
        "files": files_info,
    })
