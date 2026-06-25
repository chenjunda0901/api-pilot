"""种子数据运行器 — 创建演示项目及数据。

数据构建函数在 seed_data.py 中定义，本模块负责数据库交互逻辑。
"""

import json
import logging
from datetime import datetime, UTC

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.models.test_scene import TestScene
from app.models.scene_category import SceneCategory
from app.models.scene_step import SceneStep
from app.models.scene_edge import SceneEdge
from app.models.environment import Environment
from app.models.variable import Variable
from app.models.report_step import ReportStep
from app.models.mock_rule import MockRule
from app.utils.password import hash_password
from app.config import settings

# 从 seed_data 导入数据构建函数
from app.utils.seed_data import (
    DEMO_PROJECT_NAME,
    _build_api_definitions,
    _build_test_cases,
    _build_environments,
    _build_scenes,
    _build_mock_rules,
    _build_reports,
)

logger = logging.getLogger("seed")


async def seed_demo_data(db: AsyncSession, auto_migrate: bool = False):
    """初始化演示数据。

    Args:
        db: 数据库会话
        auto_migrate: 是否自动为所有用户创建私有副本。
    """
    # 1. 检查并创建模板（如果需要）
    result = await db.execute(select(Project).where(Project.global_demo == 1).limit(1))
    has_template = result.scalar_one_or_none() is not None

    if not has_template:
        logger.info("Creating seed template...")
        if not settings.is_production:
            await _seed_fresh(db)
            await db.commit()
            logger.info("Seed template created!")
        else:
            logger.info("Production environment — skipping seed template creation")
    else:
        logger.info("Seed template already exists, skipping")

    # 2. 可选：自动迁移用户
    if auto_migrate:
        await _migrate_all_users(db)
        await db.commit()


async def _seed_fresh(db: AsyncSession):
    """初始种子数据 - 完整电商平台演示"""
    try:
        # ----------------------------------------
        # 1. 用户
        # ----------------------------------------
        admin = await _get_or_create_admin(db)
        await db.flush()

        # ----------------------------------------
        # 2. 演示项目
        # ----------------------------------------
        project = Project(
            name=DEMO_PROJECT_NAME,
            description="模拟真实电商系统的 API 接口项目，覆盖商品管理、用户认证、订单交易、支付退款、物流配送、数据统计六大模块，用于演示 API Pilot 的完整功能",
            created_by=admin.id,
            global_demo=1,
            is_public=True,
        )
        db.add(project)
        await db.flush()
        pid = project.id

        # 设置全局变量和全局参数（项目设置页演示数据）
        project.global_variables = json.dumps([
            {"key": "base_url", "value": "http://localhost:5000", "enabled": True, "description": "API 基础地址"},
            {"key": "auth_token", "value": "", "enabled": True, "description": "认证令牌（登录后自动填充）"},
            {"key": "merchant_id", "value": "10086", "enabled": True, "description": "商户 ID"},
            {"key": "timeout", "value": "30000", "enabled": True, "description": "请求超时时间(ms)"},
        ], ensure_ascii=False)
        project.global_params = json.dumps({
            "retry_count": 2,
            "follow_redirects": True,
            "validate_certs": False,
            "headers": [
                {"key": "X-Request-Source", "value": "api-pilot", "enabled": True, "description": "请求来源标识"},
                {"key": "Accept", "value": "application/json", "enabled": True, "description": "默认响应格式"},
            ],
        }, ensure_ascii=False)

        # 将 admin 添加为种子项目 owner（其他用户在注册/启动时通过 _migrate_all_users 获得私有副本）
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == pid, ProjectMember.user_id == admin.id
        )
        if not (await db.execute(stmt)).scalar_one_or_none():
            db.add(ProjectMember(project_id=pid, user_id=admin.id, role="owner"))
        await db.flush()

        # ----------------------------------------
        # 3. 接口接口目录（6 个）
        # ----------------------------------------
        cat_map = {}
        cat_objs = []
        for i, name in enumerate(
            ["商品管理", "用户与认证", "订单管理", "支付与退款", "物流配送", "数据统计"]
        ):
            c = ApiCategory(project_id=pid, name=name, sort_order=i, is_seed=True)
            db.add(c)
            cat_objs.append((name, c))
        await db.flush()
        for name, c in cat_objs:
            cat_map[name] = c.id

        # ----------------------------------------
        # 4. 接口定义（18 个）
        # ----------------------------------------
        api_map = {}  # name → id

        apis = _build_api_definitions(pid, cat_map)
        api_objs = []
        for api_args in apis:
            api = ApiDefinition(is_seed=True, **api_args)
            db.add(api)
            api_objs.append(api)
        await db.flush()
        for api in api_objs:
            api_map[api.name] = api.id

        # ----------------------------------------
        # 5. 接口用例（扩展到 30+ 用例，覆盖更多场景）
        # ----------------------------------------
        cases = _build_test_cases(pid, api_map)
        for case_args in cases:
            db.add(TestCase(is_seed=True, **case_args))
        await db.flush()

        # ----------------------------------------
        # 6. 场景接口目录
        # ----------------------------------------
        scat_map = {}
        scat_objs = []
        for i, name in enumerate(["端到端流程", "功能验证", "异常场景", "条件与循环"]):
            sc = SceneCategory(project_id=pid, name=name, sort_order=i)
            db.add(sc)
            scat_objs.append((name, sc))
        await db.flush()
        for name, sc in scat_objs:
            scat_map[name] = sc.id

        # ----------------------------------------
        # 7. 环境（3 个）
        # ----------------------------------------
        env_map = {}
        envs = _build_environments(pid)
        env_objs = []
        for env_args in envs:
            env = Environment(**env_args)
            db.add(env)
            env_objs.append(env)
        await db.flush()
        for env in env_objs:
            env_map[env.name] = env.id

        # ----------------------------------------
        # 7.5 变量（5 层作用域演示）
        # ----------------------------------------

        # 全局变量（scope=global, scope_id=NULL）
        for name, value, desc in [
            ("app_name", "API Pilot", "应用名称"),
            ("default_timeout", "30000", "默认超时时间(ms)"),
        ]:
            db.add(Variable(scope="global", scope_id=None, name=name, value=value, is_secret=0, description=desc))
        await db.flush()

        # 项目变量（scope=project）
        for name, value, desc in [
            ("merchant_id", "10086", "商户 ID"),
            ("shop_name", "API Pilot 数码旗舰店", "店铺名称"),
        ]:
            db.add(Variable(scope="project", scope_id=pid, name=name, value=value, is_secret=0, description=desc))
        await db.flush()

        # 加密变量（is_secret=true）
        db.add(Variable(scope="project", scope_id=pid, name="api_key", value="sk-demo-key-xxxxxxxxxxxx", is_secret=1, description="API 密钥（加密存储）"))
        await db.flush()

        # 环境变量（scope=env）
        env_vars = {
            env_map.get("开发环境 (Dev)"): [("debug", "true", "调试模式"), ("log_level", "debug", "日志级别")],
            env_map.get("测试环境 (Mock)"): [("mock_mode", "true", "Mock 模式"), ("log_level", "info", "日志级别")],
            env_map.get("预发布环境 (Staging)"): [("debug", "false", "调试模式"), ("log_level", "warn", "日志级别")],
        }
        for eid, vars_list in env_vars.items():
            if eid:
                for name, value, desc in vars_list:
                    db.add(Variable(scope="env", scope_id=eid, name=name, value=value, is_secret=0, description=desc))
        await db.flush()

        # 用例变量（scope=case）
        case_vars_map = {
            "正确账号密码登录": [("login_username", "demo_merchant", "登录用户名")],
        }
        for case_name, vars_list in case_vars_map.items():
            case_result = await db.execute(
                select(TestCase).where(TestCase.project_id == pid, TestCase.name == case_name).limit(1)
            )
            case_obj = case_result.scalar_one_or_none()
            if case_obj:
                for name, value, desc in vars_list:
                    db.add(Variable(scope="case", scope_id=case_obj.id, name=name, value=value, is_secret=0, description=desc))
        await db.flush()

        # ----------------------------------------
        # 8. 场景测试（3 个）
        # ----------------------------------------
        scene_map = {}
        scenes = _build_scenes(pid, scat_map, env_map, api_map)
        for scene_args, steps, edges in scenes:
            scene = scene_args
            scene.is_seed = True
            db.add(scene)
            await db.flush()
            scene_map[scene.name] = scene.id

            # 场景步骤
            for step_args in steps:
                db.add(SceneStep(scene_id=scene.id, is_seed=True, **step_args))
            # 场景连线
            for edge_args in edges:
                db.add(SceneEdge(scene_id=scene.id, is_seed=True, **edge_args))
        await db.flush()

        # ----------------------------------------
        # 9. Mock 规则
        # ----------------------------------------
        for mock_args in _build_mock_rules(pid):
            db.add(MockRule(is_seed=True, **mock_args))
        await db.flush()

        # ----------------------------------------
        # 10. 测试报告（6 条历史）
        # ----------------------------------------
        now = datetime.now(UTC)
        reports = _build_reports(pid, admin.id, scene_map, env_map, api_map, now)
        for report_args, steps_data in reports:
            report = report_args
            db.add(report)
            await db.flush()
            for step_args in steps_data:
                db.add(ReportStep(report_id=report.id, **step_args))
        await db.flush()
    except Exception:
        logger.exception("Error during seed data creation, rolling back")
        await db.rollback()
        raise


async def _get_or_create_admin(db: AsyncSession) -> "User | None":
    """创建/获取 admin 用户（内部 Demo 部署专用）。

    - 密码硬编码为 ``fzd123``（用户要求「admin 密码必须是 fzd123，不变」）
    - 不再从环境变量 ``SEED_ADMIN_PASSWORD`` 读取
    - 不再随机生成密码
    """
    result = await db.execute(select(User).where(User.username == "admin").limit(1))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        username="admin",
        password_hash=hash_password(ADMIN_PASSWORD),
        nickname="管理员",
        email="admin@apipilot.dev",
        role="admin",
    )
    db.add(user)
    await db.flush()
    logger.info(
        "[seed] admin created with default password 'fzd123' (internal demo build)"
    )
    return user


# 内部 Demo 部署：admin 密码硬编码，禁止外部修改
ADMIN_PASSWORD = "fzd123"


async def _migrate_all_users(db: AsyncSession):
    """为所有没有独立项目副本的用户从种子模板深拷贝一份项目数据。

    每个用户获得自己的私有副本（global_demo=0），修改互不影响。
    种子模板（global_demo=1）作为只读母版，不直接被任何用户访问。
    """
    result = await db.execute(select(Project).where(Project.global_demo == 1).limit(1))
    template = result.scalar_one_or_none()
    if not template:
        logger.warning("Seed template not found, skipping user migration")
        return

    # 仅查询 user id，避免触发关联加载（refresh_tokens 等表可能缺少列）
    users_result = await db.execute(select(User.id, User.username, User.nickname))
    all_users = users_result.all()

    migrated = 0
    for row in all_users:
        uid, username, nickname = row

        # 检查用户是否已有非模板项目（global_demo=0）
        existing_proj = (await db.execute(
            select(Project).where(
                Project.created_by == uid,
                Project.global_demo == 0,
            ).limit(1)
        )).scalar_one_or_none()

        if existing_proj:
            continue

        try:
            await copy_project_to_user(db, template.id, uid, nickname=nickname or username)
            migrated += 1
            logger.info(f"Migrated seed project to user {username} (id={uid})")
        except Exception as e:
            logger.warning(f"Failed to migrate project to user {username} (id={uid}): {e}")

    if migrated > 0:
        logger.info(f"Migrated {migrated} users to new seed project copies")
    else:
        logger.info("All users already have project copies, skipping migration")

    # 修正历史数据：私有副本的 is_seed 必须为 0
    await _normalize_private_copy_seed_flags(db)


async def _normalize_private_copy_seed_flags(db: AsyncSession) -> None:
    """修正历史数据：私有副本（global_demo=0）下所有子条目的 is_seed 必须为 0。

    旧版 copy_project_to_user 直接把 is_seed=True 从种子模板复制到用户的私有副本，
    导致私有副本里的子条目错误地携带了"种子"标记。本函数将其归零（幂等）。

    影响的表：api_categories, api_definitions, test_cases, test_scenes, scene_steps, scene_edges, mock_rules
    （scene_categories 模型本身没有 is_seed 字段，跳过）
    """
    affected_total = 0

    # 直接有 project_id 列的表
    direct_tables = (
        "api_categories", "api_definitions", "test_cases", "test_scenes", "mock_rules",
    )
    for table_name in direct_tables:
        result = await db.execute(
            text(
                f"UPDATE {table_name} SET is_seed = 0 "
                f"WHERE project_id IN (SELECT id FROM projects WHERE global_demo = 0) "
                f"AND is_seed != 0"
            )
        )
        if result.rowcount and result.rowcount > 0:
            affected_total += result.rowcount
            logger.info(f"Normalized {result.rowcount} rows in {table_name} (private copies)")

    # 通过 scene_id 间接关联到 project_id 的表
    indirect_tables = ("scene_steps", "scene_edges")
    for table_name in indirect_tables:
        result = await db.execute(
            text(
                f"UPDATE {table_name} SET is_seed = 0 "
                f"WHERE scene_id IN ("
                f"  SELECT id FROM test_scenes "
                f"  WHERE project_id IN (SELECT id FROM projects WHERE global_demo = 0)"
                f") AND is_seed != 0"
            )
        )
        if result.rowcount and result.rowcount > 0:
            affected_total += result.rowcount
            logger.info(f"Normalized {result.rowcount} rows in {table_name} (private copies)")

    if affected_total > 0:
        await db.commit()
        logger.info(f"Seed flag normalization: {affected_total} rows updated in private copies")


async def copy_project_to_user(
    db: AsyncSession, template_project_id: int, user_id: int, nickname: str = ""
) -> int:
    """从种子模板深拷贝完整数据到用户私有项目

    复制范围：项目、分类、接口、用例、场景分类、场景、场景步骤、场景连线、环境、Mock规则、测试报告、变量

    Returns: 新项目 ID
    """
    logger.info(
        f"Copying demo project (id={template_project_id}) to user (id={user_id}, nickname={nickname})"
    )

    # ── 幂等性检查：用户是否已有私有项目副本 ──
    existing = await db.execute(
        select(Project)
        .where(Project.created_by == user_id, Project.global_demo == 0)
        .limit(1)
    )
    existing_proj = existing.scalar_one_or_none()
    if existing_proj:
        logger.info(
            f"User {user_id} already has project {existing_proj.id}, skipping copy"
        )
        return existing_proj.id

    try:
        # ── 1. 复制项目 ──
        result = await db.execute(
            select(Project).where(Project.id == template_project_id).limit(1)
        )
        template = result.scalar_one_or_none()
        if not template:
            logger.error(f"Template project (id={template_project_id}) not found!")
            raise ValueError(f"Template project not found: {template_project_id}")

        suffix = f" - {nickname}" if nickname else ""
        new_project = Project(
            name=template.name + suffix,
            description=template.description,
            global_variables=template.global_variables,
            global_params=template.global_params,
            created_by=user_id,
            global_demo=0,
            is_public=False,
        )
        db.add(new_project)
        await db.flush()
        new_pid = new_project.id

        # 将用户添加为项目所有者（确保用户可以访问自己的私有项目）
        # 防并发重复插入：先检查是否已存在
        from sqlalchemy import select as sa_select
        exists = await db.scalar(
            sa_select(ProjectMember).where(
                ProjectMember.project_id == new_pid,
                ProjectMember.user_id == user_id,
            )
        )
        if not exists:
            db.add(ProjectMember(project_id=new_pid, user_id=user_id, role="owner"))
            await db.flush()

        # ── 2. 复制接口目录 ──
        cat_result = await db.execute(
            select(ApiCategory)
            .where(ApiCategory.project_id == template_project_id)
            .order_by(ApiCategory.id)
        )
        old_cats = cat_result.scalars().all()
        cat_map: dict[int, int] = {}
        new_cats: list[tuple[ApiCategory, ApiCategory]] = []
        for old in old_cats:
            new = ApiCategory(
                project_id=new_pid,
                name=old.name,
                parent_id=None,
                sort_order=old.sort_order,
            )
            db.add(new)
            new_cats.append((old, new))
        await db.flush()
        for old, new in new_cats:
            cat_map[old.id] = new.id
        for old, new in new_cats:
            if old.parent_id and old.parent_id in cat_map:
                new.parent_id = cat_map[old.parent_id]
        await db.flush()

        # ── 3. 复制接口定义 ──
        api_result = await db.execute(
            select(ApiDefinition)
            .where(ApiDefinition.project_id == template_project_id)
            .order_by(ApiDefinition.id)
        )
        old_apis = api_result.scalars().all()
        api_map: dict[int, int] = {}
        api_objs: list[tuple[int, ApiDefinition]] = []
        for old in old_apis:
            new = ApiDefinition(
                project_id=new_pid,
                category_id=cat_map.get(old.category_id) if old.category_id else None,
                name=old.name,
                method=old.method,
                path=old.path,
                description=old.description,
                headers=old.headers,
                params=old.params,
                body=old.body,
                auth_type=old.auth_type,
                response_schema=old.response_schema,
                response_examples=old.response_examples,
                pre_script=old.pre_script,
                post_script=old.post_script,
                cookies=old.cookies,
                auth=old.auth,
                settings=old.settings,
                is_seed=0,  # 私有副本不带种子标记（种子项目语义仅属于 global_demo=1）
            )
            db.add(new)
            api_objs.append((old.id, new))
        await db.flush()
        for old_id, new in api_objs:
            api_map[old_id] = new.id

        # ── 4. 复制用例 ──
        case_result = await db.execute(
            select(TestCase)
            .where(TestCase.project_id == template_project_id)
            .order_by(TestCase.id)
        )
        old_cases = case_result.scalars().all()
        case_map: dict[int, int] = {}
        case_objs: list[tuple[int, TestCase]] = []
        for old in old_cases:
            new = TestCase(
                project_id=new_pid,
                api_id=api_map.get(old.api_id),
                name=old.name,
                description=old.description,
                priority=old.priority,
                status=old.status,
                case_type=old.case_type,
                tags=old.tags,
                request_body=old.request_body,
                assertions=old.assertions,
                extract_vars=old.extract_vars,
                is_seed=0,
            )
            db.add(new)
            case_objs.append((old.id, new))
        await db.flush()
        for old_id, new in case_objs:
            case_map[old_id] = new.id

        # ── 5. 复制场景分类 ──
        scat_result = await db.execute(
            select(SceneCategory)
            .where(SceneCategory.project_id == template_project_id)
            .order_by(SceneCategory.id)
        )
        old_scats = scat_result.scalars().all()
        scat_map: dict[int, int] = {}
        new_scats: list[tuple[SceneCategory, SceneCategory]] = []
        for old in old_scats:
            new = SceneCategory(
                project_id=new_pid, name=old.name, parent_id=None, sort_order=old.sort_order
            )
            db.add(new)
            new_scats.append((old, new))
        await db.flush()
        for old, new in new_scats:
            scat_map[old.id] = new.id
        for old, new in new_scats:
            if old.parent_id and old.parent_id in scat_map:
                new.parent_id = scat_map[old.parent_id]
        await db.flush()

        # ── 6. 复制场景 ──
        scene_result = await db.execute(
            select(TestScene)
            .where(TestScene.project_id == template_project_id)
            .order_by(TestScene.id)
        )
        old_scenes = scene_result.scalars().all()
        scene_map: dict[int, int] = {}
        scene_objs: list[tuple[int, TestScene]] = []
        for old in old_scenes:
            new = TestScene(
                project_id=new_pid,
                category_id=scat_map.get(old.category_id) if old.category_id else None,
                name=old.name,
                description=old.description,
                env_id=None,
                loop_count=old.loop_count,
                thread_count=old.thread_count,
                delay=old.delay,
                on_failure=old.on_failure,
                on_error=old.on_error,
                save_detail=old.save_detail,
                save_vars=old.save_vars,
                global_cookie=old.global_cookie,
                retry_count=old.retry_count,
                save_cookie_to_global=old.save_cookie_to_global,
                is_seed=0,
            )
            db.add(new)
            scene_objs.append((old.id, new))
        await db.flush()
        for old_id, new in scene_objs:
            scene_map[old_id] = new.id

        # ── 7. 复制场景步骤 ──
        step_result = await db.execute(
            select(SceneStep)
            .where(SceneStep.scene_id.in_(list(scene_map.keys())))
            .order_by(SceneStep.id)
        )
        old_steps = step_result.scalars().all()
        step_map: dict[int, int] = {}
        step_objs: list[tuple[int, SceneStep]] = []
        for old in old_steps:
            new = SceneStep(
                scene_id=scene_map.get(old.scene_id),
                node_id=old.node_id,
                node_type=old.node_type,
                label=old.label,
                position_x=old.position_x,
                position_y=old.position_y,
                api_id=api_map.get(old.api_id) if old.api_id else None,
                test_case_id=case_map.get(old.test_case_id) if old.test_case_id else None,
                sort_order=old.sort_order,
                enabled=old.enabled,
                timeout=old.timeout,
                retry_count=old.retry_count,
                request_body=old.request_body,
                headers=old.headers,
                query_params=old.query_params,
                assertions=old.assertions,
                extract_vars=old.extract_vars,
                condition_expression=old.condition_expression,
                loop_count=old.loop_count,
                loop_variable=old.loop_variable,
                wait_duration=old.wait_duration,
            )
            db.add(new)
            step_objs.append((old.id, new))
        await db.flush()
        for old_id, new in step_objs:
            step_map[old_id] = new.id

        # ── 8. 复制场景连线 ──
        edge_result = await db.execute(
            select(SceneEdge)
            .where(SceneEdge.scene_id.in_(list(scene_map.keys())))
            .order_by(SceneEdge.id)
        )
        old_edges = edge_result.scalars().all()
        for old in old_edges:
            new = SceneEdge(
                scene_id=scene_map.get(old.scene_id),
                edge_id=old.edge_id,
                source_node_id=old.source_node_id,
                target_node_id=old.target_node_id,
                source_handle=old.source_handle,
                label=old.label,
            )
            db.add(new)
        await db.flush()

        # ── 9. 复制环境 ──
        env_result = await db.execute(
            select(Environment)
            .where(Environment.project_id == template_project_id)
            .order_by(Environment.id)
        )
        old_envs = env_result.scalars().all()
        env_map: dict[int, int] = {}
        env_objs: list[tuple[int, Environment]] = []
        for old in old_envs:
            new = Environment(
                project_id=new_pid,
                name=old.name,
                services=old.services,
                variables=old.variables,
                headers=old.headers,
            )
            db.add(new)
            env_objs.append((old.id, new))
        await db.flush()
        for old_id, new in env_objs:
            env_map[old_id] = new.id

        # ── 10. 复制 Mock 规则 ──
        mock_result = await db.execute(
            select(MockRule)
            .where(MockRule.project_id == template_project_id)
            .order_by(MockRule.id)
        )
        old_mocks = mock_result.scalars().all()
        for old in old_mocks:
            new = MockRule(
                project_id=new_pid,
                name=old.name,
                enabled=old.enabled,
                priority=old.priority,
                match_method=old.match_method,
                match_path=old.match_path,
                response_status=old.response_status,
                response_headers=old.response_headers,
                response_body=old.response_body,
                response_delay=old.response_delay,
            )
            db.add(new)
        await db.flush()

        # ── 11. 复制测试报告（原生 SQL） ──
        old_reports = (
            await db.execute(
                text(
                    "SELECT id, name, scene_id, environment_id, status, pass_count, fail_count, skip_count, total_count, duration, executor_id, created_at FROM test_reports WHERE project_id = :tpid ORDER BY id"
                ),
                {"tpid": template_project_id},
            )
        ).all()
        report_map: dict[int, int] = {}
        for old in old_reports:
            await db.execute(
                text(
                    "INSERT INTO test_reports (project_id, scene_id, environment_id, name, status, pass_count, fail_count, skip_count, total_count, duration, executor_id, created_at, share_enabled) VALUES (:pid, :sid, :eid, :name, :st, :pc, :fc, :sc, :tc, :dur, :eid2, :cat, 1)"
                ),
                {
                    "pid": new_pid,
                    "sid": scene_map.get(old.scene_id) if old.scene_id else None,
                    "eid": env_map.get(old.environment_id) if old.environment_id else None,
                    "name": old.name or (f"{old.scene_id}_{old.created_at}" if old.scene_id else "unnamed"),
                    "st": old.status,
                    "pc": old.pass_count,
                    "fc": old.fail_count,
                    "sc": old.skip_count,
                    "tc": old.total_count,
                    "dur": old.duration,
                    "eid2": old.executor_id,
                    "cat": old.created_at,
                },
            )
            new_id = (await db.execute(text("SELECT last_insert_rowid()"))).scalar()
            report_map[old.id] = new_id

        # ── 12. 复制报告步骤（原生 SQL） ──
        if report_map:
            rids_str = ",".join(str(r) for r in report_map.keys())
            old_rpt_steps = (
                await db.execute(
                    text(
                        f"SELECT id, report_id, scene_step_id, scene_id, api_id, sort_order, status, duration, request_url, request_method, request_headers, request_body, response_status, response_headers, response_body, assertions, error_message FROM report_steps WHERE report_id IN ({rids_str}) ORDER BY id"
                    )
                )
            ).all()
            for old in old_rpt_steps:
                await db.execute(
                    text(
                        "INSERT INTO report_steps (report_id, scene_step_id, scene_id, api_id, sort_order, status, duration, request_url, request_method, request_headers, request_body, response_status, response_headers, response_body, assertions, error_message) VALUES (:rid, :ssid, :sid, :aid, :so, :st, :dur, :ru, :rm, :rh, :rb, :rps, :rph, :rpb, :asst, :err)"
                    ),
                    {
                        "rid": report_map.get(old.report_id),
                        "ssid": step_map.get(old.scene_step_id)
                        if old.scene_step_id
                        else None,
                        "sid": scene_map.get(old.scene_id) if old.scene_id else None,
                        "aid": api_map.get(old.api_id) if old.api_id else None,
                        "so": old.sort_order,
                        "st": old.status,
                        "dur": old.duration,
                        "ru": old.request_url,
                        "rm": old.request_method,
                        "rh": old.request_headers,
                        "rb": old.request_body,
                        "rps": old.response_status,
                        "rph": old.response_headers,
                        "rpb": old.response_body,
                        "asst": old.assertions,
                        "err": old.error_message,
                    },
                )

        # ── 13. 复制变量 ──
        # 需要使用新环境ID和新用例ID，而不是旧的
        set(env_map.values())
        set(case_map.values())

        var_result = await db.execute(
            select(Variable)
            .where(
                Variable.scope.in_(["project", "env", "case"]),
                Variable.scope_id.in_(
                    [template_project_id]  # project scope (old project id)
                    + list(env_map.keys())  # env scope (old env ids)
                    + list(case_map.keys())  # case scope (old case ids)
                )
            )
            .order_by(Variable.id)
        )
        old_vars = var_result.scalars().all()
        for old in old_vars:
            new_scope_id = None
            if old.scope == "project":
                new_scope_id = new_pid
            elif old.scope == "env":
                # 映射旧环境ID到新环境ID
                new_scope_id = env_map.get(old.scope_id)
            elif old.scope == "case":
                # 映射旧用例ID到新用例ID
                new_scope_id = case_map.get(old.scope_id)

            if new_scope_id is None and old.scope != "global":
                continue

            # 检查是否已存在相同的变量（避免重复插入）
            existing_var = await db.execute(
                select(Variable).where(
                    Variable.scope == old.scope,
                    Variable.scope_id == new_scope_id,
                    Variable.name == old.name,
                )
            )
            if existing_var.scalar_one_or_none() is not None:
                continue

            db.add(Variable(
                scope=old.scope,
                scope_id=new_scope_id,
                name=old.name,
                value=old.value,
                is_secret=old.is_secret,
                description=old.description,
            ))
        await db.flush()

        logger.info(
            f"Demo project copied to user (new_project_id={new_pid}): "
            f"{len(cat_map)} categories, {len(api_map)} apis, {len(case_map)} cases, "
            f"{len(scene_map)} scenes, {len(env_map)} envs, {len(old_vars)} vars"
        )

        return new_pid
    except Exception:
        logger.exception("Error during project copy, rolling back")
        await db.rollback()
        raise
