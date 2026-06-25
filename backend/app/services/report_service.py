import logging
import secrets

from datetime import datetime, timedelta, UTC

from sqlalchemy import select, func, delete as sa_delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_biz, ErrorCodes
from app.models.test_report import TestReport
from app.models.report_step import ReportStep
from app.models.test_scene import TestScene
from app.models.environment import Environment
from app.utils.json_helpers import safe_json_load

logger = logging.getLogger("report")


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def to_dict(self, r: TestReport, scene_name: str = "", env_name: str = "") -> dict:
        return {
            "id": r.id,
            "project_id": r.project_id,
            "name": r.name,
            "scene_id": r.scene_id,
            "environment_id": r.environment_id,
            "status": r.status,
            "pass_count": r.pass_count,
            "fail_count": r.fail_count,
            "skip_count": r.skip_count,
            "total_count": r.total_count,
            "duration": r.duration,
            "executor_id": r.executor_id,
            "created_at": str(r.created_at),
            "scene_name": scene_name,
            "env_name": env_name,
            "share_token": r.share_token or "",
        }

    async def get(self, report_id: int) -> TestReport:
        result = await self.db.execute(
            select(TestReport).where(TestReport.id == report_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise_biz(ErrorCodes.REPORT_NOT_FOUND)
        return r

    async def list(
        self,
        project_id: int,
        scene_id: int | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple:
        query = select(TestReport).where(TestReport.project_id == project_id)
        count_query = select(func.count(TestReport.id)).where(
            TestReport.project_id == project_id
        )
        if scene_id:
            query = query.where(TestReport.scene_id == scene_id)
            count_query = count_query.where(TestReport.scene_id == scene_id)
        if status:
            query = query.where(TestReport.status == status)
            count_query = count_query.where(TestReport.status == status)
        if start_date:
            query = query.where(TestReport.created_at >= start_date)
            count_query = count_query.where(TestReport.created_at >= start_date)
        if end_date:
            query = query.where(TestReport.created_at <= end_date)
            count_query = count_query.where(TestReport.created_at <= end_date)
        if keyword:
            escaped = keyword.replace("%", "\\%").replace("_", "\\_")
            kw = f"%{escaped}%"
            # 支持按报告ID搜索（纯数字时精确匹配）
            conditions = [
                TestReport.name.like(kw),
                TestReport.id == int(keyword) if keyword.isdigit() else False,
            ]
            # join scene表搜索场景名称
            scene_subq = select(TestScene.id).where(TestScene.name.like(kw))
            conditions.append(TestReport.scene_id.in_(scene_subq))
            query = query.where(or_(*conditions))
            count_query = count_query.where(or_(*conditions))
        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(
            query.order_by(TestReport.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        reports = result.scalars().all()

        # 批量获取场景名称和环境名称
        scene_ids = list({r.scene_id for r in reports if r.scene_id})
        env_ids = list({r.environment_id for r in reports if r.environment_id})
        scene_map: dict[int, str] = {}
        env_map: dict[int, str] = {}
        if scene_ids:
            s_res = await self.db.execute(
                select(TestScene.id, TestScene.name).where(TestScene.id.in_(scene_ids))
            )
            scene_map = dict(s_res.all())
        if env_ids:
            e_res = await self.db.execute(
                select(Environment.id, Environment.name).where(
                    Environment.id.in_(env_ids)
                )
            )
            env_map = dict(e_res.all())

        return [
            self.to_dict(
                r, scene_map.get(r.scene_id, ""), env_map.get(r.environment_id, "")
            )
            for r in reports
        ], total

    async def get_detail(self, report_id: int) -> dict:
        r = await self.get(report_id)
        from app.models.scene_step import SceneStep

        steps_result = await self.db.execute(
            select(ReportStep)
            .where(ReportStep.report_id == report_id)
            .order_by(ReportStep.sort_order)
        )
        report_steps = steps_result.scalars().all()

        # 批量加载关联的 SceneStep 获取 label
        step_ids = [rs.scene_step_id for rs in report_steps if rs.scene_step_id]
        scene_steps_map = {}
        if step_ids:
            ss_result = await self.db.execute(
                select(SceneStep).where(SceneStep.id.in_(step_ids))
            )
            for ss in ss_result.scalars().all():
                scene_steps_map[ss.id] = ss.label or ""

        steps = []
        required_step_fields = ("id", "report_id", "sort_order", "status")
        for idx, s in enumerate(report_steps):
            # 校验步骤必需字段存在性
            missing = [f for f in required_step_fields if getattr(s, f, None) is None]
            if missing:
                logger.warning(
                    "步骤 #%d (report_id=%s) 缺少必需字段: %s，已跳过",
                    idx,
                    report_id,
                    ", ".join(missing),
                )
                continue
            steps.append(
                {
                    "id": s.id,
                    "report_id": s.report_id,
                    "scene_step_id": s.scene_step_id,
                    "api_id": s.api_id,
                    "sort_order": s.sort_order,
                    "status": s.status,
                    "duration": s.duration,
                    "request_url": s.request_url,
                    "request_method": s.request_method,
                    "request_headers": s.request_headers,
                    "request_body": s.request_body,
                    "response_status": s.response_status,
                    "response_headers": s.response_headers,
                    "response_body": s.response_body,
                    "assertions": safe_json_load(s.assertions, []),
                    "error_message": s.error_message,
                    "label": scene_steps_map.get(s.scene_step_id, ""),
                    "script_output": s.script_output,
                    "script_error": s.script_error,
                }
            )

        # 根据实际 steps 重新计算统计数据，确保与步骤列表始终一致
        actual_pass = sum(1 for s in steps if s["status"] == "success")
        actual_fail = sum(1 for s in steps if s["status"] in ("failed", "error"))
        actual_skip = sum(1 for s in steps if s["status"] == "skipped")
        actual_total = len(steps)

        # 如果数据库聚合值与实际不一致，修正报告记录并记录日志
        if (
            r.pass_count != actual_pass
            or r.fail_count != actual_fail
            or r.skip_count != actual_skip
            or r.total_count != actual_total
        ):
            logger.info(
                "报告 #%d 统计数据不一致，已自动修正: "
                "pass_count %d→%d, fail_count %d→%d, skip_count %d→%d, total_count %d→%d",
                report_id,
                r.pass_count,
                actual_pass,
                r.fail_count,
                actual_fail,
                r.skip_count,
                actual_skip,
                r.total_count,
                actual_total,
            )
            r.pass_count = actual_pass
            r.fail_count = actual_fail
            r.skip_count = actual_skip
            r.total_count = actual_total
            r.status = "success" if actual_fail == 0 else "failed"
            await self.db.flush()

        metrics = self._compute_stress_metrics(steps, r.duration)
        # 查询场景名称和环境名称（与 list 方法保持一致）
        scene_name = ""
        env_name = ""
        if r.scene_id:
            scene = await self.db.get(TestScene, r.scene_id)
            if scene:
                scene_name = scene.name
        if r.environment_id:
            env = await self.db.get(Environment, r.environment_id)
            if env:
                env_name = env.name
        result = self.to_dict(r, scene_name=scene_name, env_name=env_name)
        # 确保返回值使用修正后的统计
        result["pass_count"] = actual_pass
        result["fail_count"] = actual_fail
        result["skip_count"] = actual_skip
        result["total_count"] = actual_total
        result["status"] = "success" if actual_fail == 0 else "failed"
        return {**result, "steps": steps, "stress_metrics": metrics}

    async def create_share_token(
        self,
        report_id: int,
        expires_in_days: int | None = 7,
        password: str | None = None,
    ) -> str:
        r = await self.get(report_id)
        token = secrets.token_urlsafe(32)
        r.share_token = token
        r.share_enabled = 1
        if expires_in_days is not None and expires_in_days > 0:
            r.share_token_expire_at = datetime.now(UTC) + timedelta(
                days=expires_in_days
            )
        else:
            r.share_token_expire_at = None
        if password:
            import hashlib

            salt = secrets.token_hex(16)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
            r.share_password = f"pbkdf2:sha256:100000:{salt}:{dk.hex()}"
        else:
            r.share_password = None
        await self.db.flush()
        return token

    async def get_by_share_token(self, token: str) -> dict:
        result = await self.db.execute(
            select(TestReport).where(TestReport.share_token == token)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise_biz(ErrorCodes.REPORT_LINK_INVALID)
        return await self.get_detail(r.id)

    async def revoke_share_token(self, report_id: int):
        r = await self.get(report_id)
        r.share_token = None
        await self.db.flush()

    async def compare(self, report_id: int, compare_with: int | None = None) -> dict:
        """增强版报告对比：支持指定对比报告，提供详细的对比分析

        Args:
            report_id: 当前报告ID
            compare_with: 可选，指定要对比的报告ID。如果为空，则自动查找同一场景的上一个报告

        Returns:
            包含对比分析的字典
        """
        r = await self.get(report_id)
        if not r.scene_id:
            raise_biz(ErrorCodes.REPORT_NO_SCENE)

        # 获取当前报告的详细信息
        current_detail = await self.get_detail(report_id)

        # 检查当前报告是否有步骤数据
        if not current_detail.get("steps"):
            return {
                "current": current_detail,
                "previous": None,
                "comparison": None,
                "message": "当前报告无步骤数据，无法进行对比",
            }

        # 确定对比报告
        prev_report_id = compare_with
        if not prev_report_id:
            # 自动查找上一个报告
            result = await self.db.execute(
                select(TestReport)
                .where(TestReport.scene_id == r.scene_id, TestReport.id < report_id)
                .order_by(TestReport.id.desc())
                .limit(1)
            )
            prev = result.scalar_one_or_none()
            if not prev:
                return {
                    "current": current_detail,
                    "previous": None,
                    "comparison": None,
                    "message": "未找到对比报告",
                }
            prev_report_id = prev.id

        # 获取对比报告的详细信息
        try:
            prev_detail = await self.get_detail(prev_report_id)
        except Exception as e:
            logger.warning("获取对比报告 #%d 失败: %s", prev_report_id, e)
            return {
                "current": current_detail,
                "previous": None,
                "comparison": None,
                "message": f"对比报告 #{prev_report_id} 不存在或无法访问",
            }

        # 检查对比报告是否有步骤数据
        if not prev_detail.get("steps"):
            return {
                "current": current_detail,
                "previous": prev_detail,
                "comparison": None,
                "message": "对比报告无步骤数据，无法进行对比",
            }

        # 执行对比分析
        comparison = self._analyze_comparison(current_detail, prev_detail)

        return {
            "current": current_detail,
            "previous": prev_detail,
            "comparison": comparison,
        }

    def _analyze_comparison(self, current: dict, previous: dict) -> dict:
        """分析两份报告的差异

        返回详细的对比分析结果，包括：
        - 总体统计对比
        - 步骤级对比
        - 性能对比
        - 稳定性分析
        """
        # 1. 总体统计对比
        current_stats = {
            "total": current.get("total_count", 0),
            "pass": current.get("pass_count", 0),
            "fail": current.get("fail_count", 0),
            "skip": current.get("skip_count", 0),
            "duration": current.get("duration", 0),
            "pass_rate": (
                current.get("pass_count", 0) / current.get("total_count", 1) * 100
            )
            if current.get("total_count", 0) > 0
            else 0,
        }
        previous_stats = {
            "total": previous.get("total_count", 0),
            "pass": previous.get("pass_count", 0),
            "fail": previous.get("fail_count", 0),
            "skip": previous.get("skip_count", 0),
            "duration": previous.get("duration", 0),
            "pass_rate": (
                previous.get("pass_count", 0) / previous.get("total_count", 1) * 100
            )
            if previous.get("total_count", 0) > 0
            else 0,
        }

        # 计算变化
        stats_comparison = {
            "total_change": current_stats["total"] - previous_stats["total"],
            "pass_change": current_stats["pass"] - previous_stats["pass"],
            "fail_change": current_stats["fail"] - previous_stats["fail"],
            "skip_change": current_stats["skip"] - previous_stats["skip"],
            "duration_change": round(
                current_stats["duration"] - previous_stats["duration"], 3
            ),
            "pass_rate_change": round(
                current_stats["pass_rate"] - previous_stats["pass_rate"], 2
            ),
            "pass_rate_trend": "improved"
            if current_stats["pass_rate"] > previous_stats["pass_rate"]
            else "declined"
            if current_stats["pass_rate"] < previous_stats["pass_rate"]
            else "unchanged",
        }

        # 2. 步骤级对比
        current_steps = {
            s.get("label", f"步骤{s.get('sort_order', '')}"): s
            for s in current.get("steps", [])
        }
        previous_steps = {
            s.get("label", f"步骤{s.get('sort_order', '')}"): s
            for s in previous.get("steps", [])
        }

        all_step_labels = set(current_steps.keys()) | set(previous_steps.keys())

        step_comparisons = []
        new_failed_steps = []
        fixed_steps = []

        for label in sorted(all_step_labels):
            curr = current_steps.get(label)
            prev = previous_steps.get(label)

            if curr and not prev:
                # 新增步骤
                step_comparisons.append(
                    {
                        "label": label,
                        "change_type": "added",
                        "current_status": curr.get("status"),
                        "previous_status": None,
                    }
                )
            elif not curr and prev:
                # 删除步骤
                step_comparisons.append(
                    {
                        "label": label,
                        "change_type": "removed",
                        "current_status": None,
                        "previous_status": prev.get("status"),
                    }
                )
            else:
                # 步骤存在，对比状态
                curr_status = curr.get("status") if curr else None
                prev_status = prev.get("status") if prev else None

                if curr_status != prev_status:
                    change_type = "status_changed"
                    if curr_status == "failed" and prev_status == "success":
                        new_failed_steps.append(label)
                    elif curr_status == "success" and prev_status == "failed":
                        fixed_steps.append(label)
                else:
                    change_type = "unchanged"

                step_comparisons.append(
                    {
                        "label": label,
                        "change_type": change_type,
                        "current_status": curr_status,
                        "previous_status": prev_status,
                        "duration_change": round(
                            (curr.get("duration", 0) if curr else 0)
                            - (prev.get("duration", 0) if prev else 0),
                            3,
                        ),
                    }
                )

        # 3. 稳定性评估
        stability_score = self._calculate_stability_score(
            current_stats, previous_stats, stats_comparison
        )

        # 4. 总结
        summary = self._generate_summary(
            stats_comparison, new_failed_steps, fixed_steps, stability_score
        )

        return {
            "stats_comparison": stats_comparison,
            "current_stats": current_stats,
            "previous_stats": previous_stats,
            "step_comparisons": step_comparisons,
            "new_failed_steps": new_failed_steps,
            "fixed_steps": fixed_steps,
            "stability_score": stability_score,
            "summary": summary,
        }

    def _calculate_stability_score(
        self, current: dict, previous: dict, comparison: dict
    ) -> int:
        """计算稳定性评分 (0-100)

        评分维度：
        - 通过率变化 (40分)
        - 失败步骤变化 (30分)
        - 执行耗时稳定性 (20分)
        - 新增失败步骤惩罚 (10分)
        """
        score = 100

        # 通过率下降扣分
        if comparison["pass_rate_trend"] == "declined":
            score -= int(40 * abs(comparison["pass_rate_change"]) / 100)
        elif comparison["pass_rate_trend"] == "improved":
            score += 10

        # 失败步骤增加扣分
        if comparison["fail_change"] > 0:
            score -= min(30, comparison["fail_change"] * 5)
        elif comparison["fail_change"] < 0:
            score += 15

        # 耗时稳定性
        if previous["duration"] > 0:
            duration_change_pct = (
                abs(comparison["duration_change"]) / previous["duration"] * 100
            )
            if duration_change_pct > 50:
                score -= 20
            elif duration_change_pct > 20:
                score -= 10

        return max(0, min(100, score))

    def _generate_summary(
        self, comparison: dict, new_failed: list, fixed: list, stability_score: int
    ) -> str:
        """生成人类可读的对比总结"""
        parts = []

        # 通过率变化
        if comparison["pass_rate_trend"] == "improved":
            parts.append(f"通过率提升 {abs(comparison['pass_rate_change']):.1f}%")
        elif comparison["pass_rate_trend"] == "declined":
            parts.append(f"通过率下降 {abs(comparison['pass_rate_change']):.1f}%")

        # 失败变化
        if comparison["fail_change"] > 0:
            parts.append(f"失败增加 {comparison['fail_change']} 个")
        elif comparison["fail_change"] < 0:
            parts.append(f"失败减少 {abs(comparison['fail_change'])} 个")

        # 新增失败步骤
        if new_failed:
            parts.append(f"新增失败步骤: {', '.join(new_failed[:3])}")
            if len(new_failed) > 3:
                parts[-1] += f" 等{len(new_failed)}个"

        # 修复步骤
        if fixed:
            parts.append(f"已修复: {', '.join(fixed[:3])}")
            if len(fixed) > 3:
                parts[-1] += f" 等{len(fixed)}个"

        # 稳定性评分
        parts.append(f"稳定性评分: {stability_score}/100")

        return "；".join(parts) if parts else "两份报告表现基本一致"

    async def delete(self, report_id: int):
        r = await self.get(report_id)
        await self.db.execute(
            sa_delete(ReportStep).where(ReportStep.report_id == report_id)
        )
        await self.db.delete(r)
        await self.db.flush()

    async def clean_old(self, days: int):
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(TestReport.id).where(TestReport.created_at < cutoff)
        )
        old_ids = [row[0] for row in result.fetchall()]
        if old_ids:
            await self.db.execute(
                sa_delete(ReportStep).where(ReportStep.report_id.in_(old_ids))
            )
            await self.db.execute(
                sa_delete(TestReport).where(TestReport.id.in_(old_ids))
            )
            await self.db.flush()
            logger.info(f"Cleaned {len(old_ids)} old reports")

    @staticmethod
    def _compute_stress_metrics(steps: list, report_duration: float = None) -> dict:
        """从报告步骤中计算压测性能指标。

        对 stress 模式的报告，从 ReportStep 的 duration 数据计算：
        - P50/P90/P95/P99 延迟（毫秒）
        - 吞吐量（请求/秒）
        - 错误率（%）
        - 最短/最长/平均耗时

        Args:
            steps: ReportStep 字典列表，每个包含 duration 和 status
            report_duration: 报告总耗时（秒），用于计算吞吐量

        Returns:
            性能指标字典，stress 模式的报告有数据，非 stress 返回空
        """
        durations = [s.get("duration", 0) for s in steps if s.get("duration", 0) > 0]
        if not durations or len(durations) < 5:
            return None

        sorted_d = sorted(durations)
        n = len(sorted_d)
        total_duration = sum(sorted_d)
        avg = total_duration / n

        def percentile(p: float) -> float:
            k = int(n * p / 100)
            return sorted_d[min(k, n - 1)]

        # 错误率
        fail_count = sum(1 for s in steps if s.get("status") == "failed")
        error_rate = round(fail_count / len(steps) * 100, 2) if steps else 0

        # 吞吐量（请求数 / 实际总执行时间）
        if report_duration and report_duration > 0:
            throughput = round(n / report_duration, 2)
        else:
            # 兜底：用最大步骤耗时
            wall_time = max(sorted_d) / 1000
            throughput = round(n / wall_time, 2) if wall_time > 0 else 0

        return {
            "p50": round(percentile(50), 2),
            "p90": round(percentile(90), 2),
            "p95": round(percentile(95), 2),
            "p99": round(percentile(99), 2),
            "avg": round(avg, 2),
            "min": round(sorted_d[0], 2),
            "max": round(sorted_d[-1], 2),
            "error_rate": error_rate,
            "throughput": throughput,
            "total_requests": n,
        }
