from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.project import Project
from app.models.test_report import TestReport
from app.services.report_service import ReportService
from app.services.permission_service import check_read_access, check_write_access
from app.utils.response import success
from app.utils.export import export_report_excel, export_report_pdf
from app.core.exceptions import ErrorCodes
from app.core.exceptions import raise_biz

router = APIRouter(prefix="/projects/{project_id}/reports", tags=["Test Reports"])
logger = logging.getLogger("api_pilot.routers.reports")


@router.get("", summary="报告列表", description="获取项目的测试报告列表，支持分页筛选")
async def list_reports(
    project_id: int,
    scene_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ReportService(db)
    items, total = await s.list(
        project_id, scene_id, status, start_date, end_date, keyword, page, page_size
    )
    return success(
        {"items": items, "total": total, "page": page, "page_size": page_size}
    )


@router.get("/trend", summary="Report trend data")
async def get_report_trend(
    project_id: int,
    days: int = 30,
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.models.test_report import TestReport
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict

    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(TestReport)
        .where(TestReport.project_id == project_id, TestReport.created_at >= since)
        .order_by(TestReport.created_at.asc())
    )
    reports = result.scalars().all()

    # 按日期聚合
    daily_data: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    for r in reports:
        created = r.created_at
        if created:
            if created.tzinfo is not None:
                date_key = created.strftime("%Y-%m-%d")
            else:
                date_key = created.strftime("%Y-%m-%d")
        else:
            continue
        daily_data[date_key]["total"] += r.total_count or 0
        daily_data[date_key]["passed"] += r.pass_count or 0
        daily_data[date_key]["failed"] += r.fail_count or 0

    # 填充缺失的日期
    trend_list = []
    for d in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - d)).strftime("%Y-%m-%d")
        entry = daily_data.get(date, {"total": 0, "passed": 0, "failed": 0})
        trend_list.append({
            "date": date,
            "total": entry["total"],
            "passed": entry["passed"],
            "failed": entry["failed"],
        })

    return success({"data": trend_list})


@router.get(
    "/{report_id}",
    summary="报告详情",
    description="获取指定测试报告的详细数据和步骤结果",
)
async def get_report(
    project_id: int,
    report_id: int,
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ReportService(db)
    r = await s.get(report_id)
    if r.project_id != project_id:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)
    return success(await s.get_detail(report_id))


@router.delete("/{report_id}", summary="删除报告", description="删除指定的测试报告")
async def delete_report(
    project_id: int,
    report_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    # 检查报告状态
    from app.models.test_report import TestReport
    result = await db.execute(select(TestReport).where(TestReport.id == report_id, TestReport.project_id == project_id))
    report = result.scalar_one_or_none()
    if not report:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)
    if report.status == "running":
        raise_biz(ErrorCodes.PARAM_ERROR, "报告正在运行中，无法删除")

    s = ReportService(db)
    await s.delete(report_id)
    return success(message="报告已删除")


@router.get(
    "/{report_id}/compare",
    summary="报告对比",
    description="对比两次测试报告的执行结果差异，支持指定对比报告ID",
)
async def compare_report(
    project_id: int,
    report_id: int,
    compare_with: Optional[int] = Query(None, description="指定要对比的报告ID，为空则自动查找上一个报告"),
    current_user: User | None = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ReportService(db)
    r = await s.get(report_id)
    if r.project_id != project_id:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)
    return success(await s.compare(report_id, compare_with))


@router.get(
    "/{report_id}/share",
    summary="获取分享 Token",
    description="获取测试报告的分享链接 Token",
)
async def get_share_token(
    project_id: int,
    report_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    s = ReportService(db)
    r = await s.get(report_id)
    if r.project_id != project_id:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)
    return success({"share_token": r.share_token or None})


@router.post(
    "/{report_id}/share", summary="创建分享", description="为测试报告创建对外分享链接"
)
async def create_share_report(
    report_id: int,
    project_id: int,
    expires_in_days: int = Query(7, ge=0, le=365, description="过期天数，默认7天，0表示永不过期"),
    password: Optional[str] = Query(None, max_length=64, description="访问密码（可选）"),
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = ReportService(db)
    r = await s.get(report_id)
    if r.project_id != project_id:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)
    token = await s.create_share_token(
        report_id,
        expires_in_days=expires_in_days if expires_in_days > 0 else None,
        password=password,
    )
    return success({"share_token": token})


@router.delete(
    "/{report_id}/share", summary="撤销分享", description="撤销测试报告的分享链接"
)
async def revoke_share_report(
    project_id: int,
    report_id: int,
    current_user: User = Depends(get_current_user),
    _project: Project = Depends(check_write_access),
    db: AsyncSession = Depends(get_db),
):
    s = ReportService(db)
    r = await s.get(report_id)
    if r.project_id != project_id:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)
    await s.revoke_share_token(report_id)
    return success(message="分享已撤销")



@router.get(
    "/{report_id}/export/excel",
    summary="导出 Excel",
    description="将测试报告导出为 Excel 格式",
)
async def export_report_excel_endpoint(
    project_id: int,
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import BizError
    s = ReportService(db)
    detail = await s.get_detail(report_id)  # 报告不存在时 raise BizError(REPORT_NOT_FOUND) -> 404
    try:
        excel_data = await export_report_excel(detail)
    except BizError:
        raise
    except Exception as e:
        logger.error("导出 Excel 失败 (report_id=%d): %s", report_id, e, exc_info=True)
        raise_biz(ErrorCodes.INTERNAL_ERROR, f"导出 Excel 失败: {str(e)}")
    return StreamingResponse(
        iter([excel_data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=report_{report_id}.xlsx"
        },
    )


@router.get(
    "/{report_id}/export/pdf",
    summary="导出 PDF",
    description="将测试报告导出为 PDF 格式",
)
async def export_report_pdf_endpoint(
    project_id: int,
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import BizError
    s = ReportService(db)
    detail = await s.get_detail(report_id)  # 报告不存在时 raise BizError(REPORT_NOT_FOUND) -> 404
    try:
        pdf_data = await export_report_pdf(detail)
    except BizError:
        raise
    except Exception as e:
        logger.error("导出 PDF 失败 (report_id=%d): %s", report_id, e, exc_info=True)
        raise_biz(ErrorCodes.INTERNAL_ERROR, f"导出 PDF 失败: {str(e)}")
    return StreamingResponse(
        iter([pdf_data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.pdf"},
    )


@router.get("/{report_id}/export", summary="Export report")
async def export_report(
    project_id: int,
    report_id: int,
    format: str = "markdown",
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import BizError
    try:
        from app.services.report_export_service import ReportExportService

        svc = ReportExportService(db)
        if format == "html":
            from fastapi.responses import HTMLResponse

            content = await svc.export_html(report_id)
            return HTMLResponse(content)
        elif format == "markdown":
            from fastapi.responses import PlainTextResponse

            content = await svc.export_markdown(report_id)
            return PlainTextResponse(content)
        elif format == "json":
            from fastapi.responses import PlainTextResponse

            content = await svc.export_json(report_id)
            return PlainTextResponse(content, media_type="application/json")
        elif format == "csv":
            content = await svc.export_csv(report_id)
            return StreamingResponse(
                iter([content]),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{report_id}.csv"
                },
            )
        elif format == "junit":
            content = await svc.export_junit_xml(report_id)
            return Response(
                content=content,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f'attachment; filename="report-{report_id}.xml"',
                },
            )
        elif format == "excel":
            s = ReportService(db)
            detail = await s.get_detail(report_id)
            excel_data = await export_report_excel(detail)
            return StreamingResponse(
                iter([excel_data]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{report_id}.xlsx"
                },
            )
        elif format == "pdf":
            s = ReportService(db)
            detail = await s.get_detail(report_id)
            pdf_data = await export_report_pdf(detail)
            return StreamingResponse(
                iter([pdf_data]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.pdf"},
            )
        else:
            raise_biz(ErrorCodes.PARAM_ERROR, "不支持的导出格式")
    except BizError:
        raise
    except Exception as e:
        logger.error("导出失败 (report_id=%d): %s", report_id, e, exc_info=True)
        raise_biz(ErrorCodes.INTERNAL_ERROR, f"导出失败: {str(e)}")


@router.get(
    "/{report_id}/export/csv",
    summary="导出 CSV",
    description="将测试报告导出为 CSV 格式（步骤详情）",
)
async def export_report_csv(
    project_id: int,
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        from app.services.report_export_service import ReportExportService

        svc = ReportExportService(db)
        content = await svc.export_csv(report_id)
        return StreamingResponse(
            iter([content]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=report_{report_id}_detail.csv"
            },
        )
    except Exception as e:
        logger.error("导出 CSV 失败 (report_id=%d): %s", report_id, e, exc_info=True)
        raise_biz(ErrorCodes.INTERNAL_ERROR, "导出失败，请稍后重试")


@router.get(
    "/{report_id}/export/junit",
    summary="导出 JUnit XML（CI 集成）",
    description="将测试报告导出为 JUnit XML 格式，兼容 Jenkins/CircleCI/GitLab CI",
)
async def export_report_junit(
    report_id: int,
    project_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        from app.services.report_export_service import ReportExportService

        svc = ReportExportService(db)
        content = await svc.export_junit_xml(report_id)
        return Response(
            content=content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="report-{report_id}.xml"',
            },
        )
    except Exception as e:
        logger.error("导出 JUnit XML 失败 (report_id=%d): %s", report_id, e, exc_info=True)
        raise_biz(ErrorCodes.INTERNAL_ERROR, f"导出 JUnit XML 失败: {str(e)}")


@router.get(
    "/{report_id}/export/csv/summary",
    summary="导出 CSV 汇总",
    description="将测试报告汇总导出为 CSV 格式",
)
async def export_report_csv_summary(
    project_id: int,
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    _project: Project = Depends(check_read_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        from app.services.report_export_service import ReportExportService

        svc = ReportExportService(db)
        content = await svc.export_csv_summary(report_id)
        return StreamingResponse(
            iter([content]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=report_{report_id}_summary.csv"
            },
        )
    except Exception as e:
        logger.error("导出 CSV 汇总失败 (report_id=%d): %s", report_id, e, exc_info=True)
        raise_biz(ErrorCodes.INTERNAL_ERROR, "导出失败，请稍后重试")


async def _validate_shared_report(
    token: str,
    password: str | None,
    db: AsyncSession,
) -> "TestReport":
    """Validate and return a shared report, checking expiry and password."""
    from datetime import datetime, timezone
    import hashlib

    result = await db.execute(
        select(TestReport).where(
            TestReport.share_token == token, TestReport.share_enabled.is_(True)
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise_biz(ErrorCodes.REPORT_NOT_FOUND)

    # 检查分享链接是否已过期（统一为 aware UTC，避免 naive vs aware 比较错误）
    if report.share_token_expire_at:
        expire_at = report.share_token_expire_at
        if expire_at.tzinfo is None:
            expire_at = expire_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expire_at:
            raise_biz(ErrorCodes.REPORT_LINK_EXPIRED, "分享链接已过期")

    # 检查密码
    if report.share_password:
        if not password:
            raise_biz(ErrorCodes.PARAM_ERROR, "此分享链接需要输入密码")
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash != report.share_password:
            raise_biz(ErrorCodes.PARAM_ERROR, "密码错误")

    return report


@router.get("/shared/{token}", summary="获取分享报告数据")
@limiter.limit("60/minute")
async def get_shared_report(
    project_id: int, token: str, request: Request,
    password: Optional[str] = Query(None, description="访问密码（如果设置了的话）"),
    db: AsyncSession = Depends(get_db),
):
    report = await _validate_shared_report(token, password, db)

    return success(
        {
            "id": report.id,
            "name": report.name,
            "scene_id": report.scene_id,
            "status": report.status,
            "total": report.total_count,
            "passed": report.pass_count,
            "failed": report.fail_count,
            "created_at": str(report.created_at),
        }
    )


# 公共分享路由（无需 project_id，用于分享链接）
public_router = APIRouter(prefix="/reports", tags=["Public Reports"])

# 敏感 header 关键字（小写匹配），分享报告中需过滤
_SENSITIVE_HEADER_KEYS = {
    "authorization", "cookie", "set-cookie", "x-api-key",
    "x-auth-token", "x-csrf-token", "api-key", "proxy-authorization",
}


def _sanitize_headers(headers):
    """过滤敏感 header，支持 dict、JSON 字符串、None。"""
    if not headers:
        return headers
    import json
    if isinstance(headers, str):
        try:
            parsed = json.loads(headers)
        except (json.JSONDecodeError, TypeError):
            return headers
        if isinstance(parsed, dict):
            return json.dumps(
                {k: v for k, v in parsed.items() if k.lower() not in _SENSITIVE_HEADER_KEYS},
                ensure_ascii=False,
            )
        return headers
    if isinstance(headers, dict):
        return {k: v for k, v in headers.items() if k.lower() not in _SENSITIVE_HEADER_KEYS}
    return headers


def _sanitize_report_data(data):
    """递归过滤报告数据中的敏感 header（authorization/cookie/x-api-key 等）。"""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            key_lower = k.lower() if isinstance(k, str) else k
            if key_lower in ("headers", "request_headers", "response_headers", "cookies"):
                sanitized[k] = _sanitize_headers(v)
            else:
                sanitized[k] = _sanitize_report_data(v)
        return sanitized
    if isinstance(data, list):
        return [_sanitize_report_data(item) for item in data]
    return data


@public_router.get("/shared/{token}", summary="获取分享报告数据（公开）")
@limiter.limit("60/minute")
async def get_shared_report_public(
    token: str, request: Request,
    password: Optional[str] = Query(None, description="访问密码（如果设置了的话）"),
    db: AsyncSession = Depends(get_db),
):
    """公开的分享报告接口，无需登录和 project_id"""
    report = await _validate_shared_report(token, password, db)

    # 返回完整步骤数据（含 steps 详情），但过滤敏感 header
    detail = await ReportService(db).get_detail(report.id)
    return success(_sanitize_report_data(detail))
