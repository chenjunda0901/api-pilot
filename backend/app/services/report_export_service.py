import csv
import io
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("api_pilot.services.report_export")


def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符。"""
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def _sanitize_cell(value: str | None) -> str:
    """防止 CSV/Excel 公式注入"""
    if value is None:
        return ''
    s = str(value).strip()
    # Excel 公式前缀字符：= + - @ \t (Tab)
    if s and s[0] in ('=', '+', '-', '@', '\t'):
        return "'" + s  # 添加单引号前缀强制作为纯文本
    return s


def _generate_export_filename(report_name: str, extension: str) -> str:
    """生成导出文件名：报告名称_YYYYMMDD_HHMMSS.ext"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in report_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')[:50]  # 限制长度
    return f"{safe_name}_{timestamp}.{extension}"


class ReportExportError(Exception):
    """报告导出异常"""
    pass


class ReportExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_junit_xml(self, report_id: int) -> str:
        """导出 JUnit XML 格式，兼容 Jenkins/CircleCI/GitLab CI。"""
        from app.models.test_report import TestReport
        from app.models.test_scene import TestScene
        from app.models.report_step import ReportStep

        result = await self.db.execute(
            select(TestReport).where(TestReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return '<?xml version="1.0"?><testsuite name="API Pilot" tests="0" failures="0" errors="0" />'

        scene_name = ""
        if report.scene_id:
            scene = await self.db.get(TestScene, report.scene_id)
            if scene:
                scene_name = scene.name

        # 显式查询 ReportStep 表（TestReport 无 steps 关系）
        steps_result = await self.db.execute(
            select(ReportStep)
            .where(ReportStep.report_id == report_id)
            .order_by(ReportStep.sort_order)
        )
        steps = steps_result.scalars().all()

        steps_xml = ""
        if steps:
            for step in steps:
                step_name = _escape_xml(step.request_url or "unknown")
                step_status = step.status or "unknown"
                duration = (step.duration or 0) / 1000.0  # ms → s
                error_msg = _escape_xml(step.error_message or "")
                if step_status == "success":
                    steps_xml += f'  <testcase name="{step_name}" time="{duration:.3f}">\n'
                    if error_msg:
                        steps_xml += f'    <failure message="{error_msg}"/>\n'
                    steps_xml += '  </testcase>\n'
                elif step_status == "failed":
                    steps_xml += f'  <testcase name="{step_name}" time="{duration:.3f}">\n'
                    steps_xml += f'    <failure message="{error_msg or "Step failed"}"/>\n'
                    steps_xml += '  </testcase>\n'
                else:
                    steps_xml += f'  <testcase name="{step_name}" time="{duration:.3f}">\n'
                    if error_msg:
                        steps_xml += f'    <error message="{error_msg}"/>\n'
                    steps_xml += '  </testcase>\n'

        failures = report.fail_count or 0
        total = report.total_count or 0
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += f'<testsuite name="{_escape_xml(scene_name or f"Report #{report.id}")}"\n'
        xml += f'  tests="{total}" failures="{failures}" errors="0" time="{report.duration:.3f}"\n'
        xml += f'  timestamp="{report.created_at}">\n'
        xml += steps_xml
        xml += '</testsuite>\n'
        return xml

    async def export_markdown(self, report_id: int) -> str:
        from app.models.test_report import TestReport
        from app.models.test_scene import TestScene

        result = await self.db.execute(
            select(TestReport).where(TestReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return "# Report not found"

        scene_name = ""
        if report.scene_id:
            scene = await self.db.get(TestScene, report.scene_id)
            if scene:
                scene_name = scene.name

        pass_rate = 0
        if report.total_count > 0:
            pass_rate = round(report.pass_count / report.total_count * 100, 1)

        lines = [
            f"# 测试报告 #{report.id}",
            f"**场景**: {scene_name or '未知'}",
            f"**执行时间**: {report.created_at}",
            f"**状态**: {'通过' if report.status == 'success' else '失败' if report.status == 'failed' else report.status}",
            "",
            "## 执行统计",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总数 | {report.total_count} |",
            f"| 通过 | {report.pass_count} |",
            f"| 失败 | {report.fail_count} |",
            f"| 跳过 | {report.skip_count} |",
            f"| 通过率 | {pass_rate}% |",
            f"| 耗时 | {report.duration:.2f}s |",
            "",
        ]
        return "\n".join(lines)

    async def export_html(self, report_id: int) -> str:
        md = await self.export_markdown(report_id)
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Test Report</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
h1 {{ color: #1a9f82; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
</style></head>
<body><pre>{md}</pre></body></html>"""
        return html

    async def export_pdf(self, report_id: int) -> bytes:
        """导出 PDF 格式（使用 HTML 转 PDF）"""
        html_content = await self.export_html(report_id)
        try:
            # 尝试使用 weasyprint 生成 PDF
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            # weasyprint 未安装时，返回 HTML 内容并提示
            logger.warning("weasyprint not installed, falling back to HTML")
            raise ReportExportError("PDF 导出需要安装 weasyprint: pip install weasyprint")
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise ReportExportError(f"导出失败：{str(e)}")

    async def export_json(self, report_id: int) -> str:
        """导出 JSON 格式"""
        import json
        from app.models.test_report import TestReport
        from app.models.test_scene import TestScene
        from app.models.report_step import ReportStep

        result = await self.db.execute(
            select(TestReport).where(TestReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ReportExportError("导出失败：报告数据不完整")

        scene_name = ""
        if report.scene_id:
            scene = await self.db.get(TestScene, report.scene_id)
            if scene:
                scene_name = scene.name

        # 获取步骤详情
        steps_result = await self.db.execute(
            select(ReportStep)
            .where(ReportStep.report_id == report_id)
            .order_by(ReportStep.sort_order)
        )
        steps = []
        for step in steps_result.scalars().all():
            steps.append({
                "sort_order": step.sort_order if hasattr(step, "sort_order") else 0,
                "request_url": step.request_url or "",
                "request_method": step.request_method or "",
                "status": step.status or "unknown",
                "duration_ms": int(float(step.duration or 0) * 1000),
                "response_status": step.response_status,
                "error_message": step.error_message or "",
                "request_headers": step.request_headers if hasattr(step, "request_headers") else None,
                "response_body": step.response_body if hasattr(step, "response_body") else None,
            })

        pass_rate = 0
        if report.total_count > 0:
            pass_rate = round(report.pass_count / report.total_count * 100, 1)

        data = {
            "report": {
                "id": report.id,
                "scene_name": scene_name,
                "status": report.status,
                "created_at": str(report.created_at),
                "duration": report.duration,
                "total_count": report.total_count,
                "pass_count": report.pass_count,
                "fail_count": report.fail_count,
                "skip_count": report.skip_count,
                "pass_rate": pass_rate,
            },
            "steps": steps,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    async def export_csv(self, report_id: int) -> bytes:
        """导出为 CSV 格式，使用 Python csv 模块确保正确转义特殊字符。
        返回 UTF-8 BOM + CSV 内容，确保 Excel 等工具正确识别中文编码。
        """
        from app.models.test_report import TestReport
        from app.models.report_step import ReportStep

        result = await self.db.execute(
            select(TestReport).where(TestReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ReportExportError("导出失败：报告数据不完整")

        if report.scene_id:
            from app.models.test_scene import TestScene

            scene = await self.db.get(TestScene, report.scene_id)
            if scene:
                pass

        # 获取步骤详情
        steps_result = await self.db.execute(
            select(ReportStep)
            .where(ReportStep.report_id == report_id)
            .order_by(ReportStep.sort_order)
        )
        steps = steps_result.scalars().all()

        # 使用 StringIO 和 csv.writer 确保正确转义
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # CSV 头部
        writer.writerow([
            "sort_order", "request_method", "request_url", "status",
            "duration_ms", "response_status", "error_message"
        ])

        for step in steps:
            sort_order = step.sort_order if hasattr(step, "sort_order") else ""
            status = (
                "success"
                if step.status == "success"
                else "failed"
                if step.status == "failed"
                else step.status or "unknown"
            )
            duration_ms = int(float(step.duration or 0) * 1000)
            response_status = step.response_status or 0
            # 清理换行符和特殊字符
            error_msg = _sanitize_cell((step.error_message or "").replace("\n", " ").replace("\r", " "))
            request_method = _sanitize_cell(step.request_method or "")
            request_url = _sanitize_cell(step.request_url or "")

            writer.writerow([
                sort_order, request_method, request_url, status,
                duration_ms, response_status, error_msg
            ])

        # UTF-8 BOM 确保中文在 Excel 中正确显示
        csv_content = output.getvalue()
        return b'\xef\xbb\xbf' + csv_content.encode("utf-8")

    async def export_csv_summary(self, report_id: int) -> bytes:
        """导出为汇总 CSV 格式（适合数据分析）。
        返回 UTF-8 BOM + CSV 内容，确保中文编码正确。
        """
        from app.models.test_report import TestReport

        result = await self.db.execute(
            select(TestReport).where(TestReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ReportExportError("导出失败：报告数据不完整")

        scene_name = ""
        if report.scene_id:
            from app.models.test_scene import TestScene

            scene = await self.db.get(TestScene, report.scene_id)
            if scene:
                scene_name = scene.name

        pass_rate = 0
        if report.total_count > 0:
            pass_rate = round(report.pass_count / report.total_count * 100, 1)

        # 单行汇总 CSV
        scene_display = _sanitize_cell(scene_name or "unknown")
        status_display = _sanitize_cell(report.status or "unknown")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["report_id", "scene_name", "created_at", "status", "total_count", "pass_count", "fail_count", "skip_count", "pass_rate", "duration"])
        writer.writerow([report.id, scene_display, report.created_at, status_display, report.total_count, report.pass_count, report.fail_count, report.skip_count, pass_rate, f"{report.duration or 0:.2f}"])

        csv_content = output.getvalue()
        return b'\xef\xbb\xbf' + csv_content.encode("utf-8")
