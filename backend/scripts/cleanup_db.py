"""数据库清理脚本：删除 admin 以外的用户数据，保留 admin 和种子数据。

用法：
    uv run python scripts/cleanup_db.py [--dry-run]

选项：
    --dry-run  仅显示将删除的内容，不实际删除
"""

import sys
import argparse

# 确保可以导入 app 模块
sys.path.insert(0, str(__file__).rsplit('scripts', 1)[0])

from sqlalchemy import text
from app.database import engine
from app.utils.password import hash_password


ADMIN_PASSWORD = "fzd123"


async def cleanup_database(dry_run: bool = True):
    """清理数据库：删除 admin 以外的用户及其关联数据"""
    
    async with engine.begin() as conn:
        # 1. 查找 admin 用户
        admin_result = await conn.execute(
            text("SELECT id, username, email FROM users WHERE username = 'admin'")
        )
        admin_row = admin_result.fetchone()
        
        if not admin_row:
            print("❌ 未找到 admin 用户，请先启动一次服务以初始化数据")
            return False
        
        admin_id = admin_row[0]
        print(f"✅ 找到 admin 用户 (id={admin_id})")
        
        # 2. 查找所有非 admin 用户
        users_result = await conn.execute(
            text("SELECT id, username, email, role FROM users WHERE username != 'admin'")
        )
        other_users = users_result.fetchall()
        
        print(f"\n📋 非 admin 用户数量: {len(other_users)}")
        for user in other_users:
            print(f"   - id={user[0]}, username={user[1]}, email={user[2]}, role={user[3]}")
        
        if dry_run:
            print("\n⚠️  [Dry Run 模式] 以下操作将被跳过")
        else:
            print("\n🗑️  开始清理数据...")
        
        # 3. 对于每个非 admin 用户，收集其项目
        for user in other_users:
            user_id = user[0]
            username = user[1]
            
            # 查找该用户的项目
            projects_result = await conn.execute(
                text("SELECT id, name, global_demo FROM projects WHERE created_by = :uid"),
                {"uid": user_id}
            )
            projects = projects_result.fetchall()
            
            print(f"\n👤 用户: {username} (id={user_id})")
            print(f"   项目数量: {len(projects)}")
            
            for proj in projects:
                proj_id = proj[0]
                proj_name = proj[1]
                is_global = proj[2]
                
                if is_global == 1:
                    print(f"   ⚠️  项目 '{proj_name}' (id={proj_id}) 是全局种子项目，将保留")
                else:
                    print(f"   📦 项目 '{proj_name}' (id={proj_id}) - 将删除")
                    
                    if not dry_run:
                        # 删除项目关联数据（按依赖顺序）
                        await _delete_project_data(conn, proj_id)
                        # 删除项目
                        await conn.execute(
                            text("DELETE FROM projects WHERE id = :pid"),
                            {"pid": proj_id}
                        )
                        print("      ✅ 项目已删除")
            
            # 删除用户（非 admin）
            if not dry_run:
                # 先删除用户关联的项目成员
                await conn.execute(
                    text("DELETE FROM project_members WHERE user_id = :uid"),
                    {"uid": user_id}
                )
                # 删除 refresh_tokens
                await conn.execute(
                    text("DELETE FROM refresh_tokens WHERE user_id = :uid"),
                    {"uid": user_id}
                )
                # 删除用户
                await conn.execute(
                    text("DELETE FROM users WHERE id = :uid"),
                    {"uid": user_id}
                )
                print(f"   ✅ 用户 '{username}' 已删除")
        
        # 4. 确保 admin 密码为 fzd123
        admin_password_hash = hash_password(ADMIN_PASSWORD)
        if not dry_run:
            await conn.execute(
                text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"),
                {"hash": admin_password_hash}
            )
            print(f"\n✅ admin 密码已重置为 '{ADMIN_PASSWORD}'")
        else:
            print(f"\n⚠️  [Dry Run] admin 密码将重置为 '{ADMIN_PASSWORD}'")
        
        # 5. 删除 admin 的私有项目（只保留种子项目）
        if not dry_run:
            admin_private_result = await conn.execute(
                text("SELECT id, name FROM projects WHERE created_by = :uid AND global_demo = 0"),
                {"uid": admin_id}
            )
            admin_private_projects = admin_private_result.fetchall()
            
            if admin_private_projects:
                print(f"\n🗑️  删除 admin 的私有项目 ({len(admin_private_projects)} 个):")
                for proj_id, proj_name in admin_private_projects:
                    print(f"   删除: {proj_name} (id={proj_id})")
                    await _delete_project_data(conn, proj_id)
                    await conn.execute(
                        text("DELETE FROM projects WHERE id = :pid"),
                        {"pid": proj_id}
                    )
                print("   ✅ admin 私有项目已清理")
            else:
                print("\nℹ️  admin 没有私有项目需要清理")
        else:
            admin_private_result = await conn.execute(
                text("SELECT id, name FROM projects WHERE created_by = :uid AND global_demo = 0"),
                {"uid": admin_id}
            )
            admin_private_projects = admin_private_result.fetchall()
            if admin_private_projects:
                print(f"\n⚠️  [Dry Run] admin 的 {len(admin_private_projects)} 个私有项目将删除")

        # 6. 显示清理后的状态
        print("\n" + "=" * 60)
        print("📊 清理后的数据库状态")
        print("=" * 60)
        
        final_users = await conn.execute(text("SELECT id, username, email, role FROM users"))
        print(f"\n用户总数: {len(final_users.fetchall())}")
        for row in (await conn.execute(text("SELECT id, username, email, role FROM users"))).fetchall():
            print(f"   - id={row[0]}, username={row[1]}, email={row[2]}, role={row[3]}")
        
        projects_count = await conn.execute(text("SELECT COUNT(*) FROM projects WHERE global_demo = 1"))
        private_projects = await conn.execute(text("SELECT COUNT(*) FROM projects WHERE global_demo = 0"))
        print(f"\n种子项目 (global_demo=1): {projects_count.fetchone()[0]} 个")
        print(f"私有项目 (global_demo=0): {private_projects.fetchone()[0]} 个")
        
    return True


async def _delete_project_data(conn, project_id: int):
    """按依赖顺序删除项目关联数据"""
    
    # 注意：外键约束应该能自动处理级联删除，但为了确保安全，手动按顺序删除
    
    # 1. 删除报告步骤 (report_steps)
    await conn.execute(
        text("DELETE FROM report_steps WHERE report_id IN (SELECT id FROM test_reports WHERE project_id = :pid)"),
        {"pid": project_id}
    )
    
    # 2. 删除报告 (test_reports)
    await conn.execute(
        text("DELETE FROM test_reports WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 3. 删除场景连线 (scene_edges) - 通过场景
    await conn.execute(
        text("DELETE FROM scene_edges WHERE scene_id IN (SELECT id FROM test_scenes WHERE project_id = :pid)"),
        {"pid": project_id}
    )
    
    # 4. 删除场景步骤 (scene_steps) - 通过场景
    await conn.execute(
        text("DELETE FROM scene_steps WHERE scene_id IN (SELECT id FROM test_scenes WHERE project_id = :pid)"),
        {"pid": project_id}
    )
    
    # 5. 删除场景 (test_scenes)
    await conn.execute(
        text("DELETE FROM test_scenes WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 6. 删除场景分类 (scene_categories)
    await conn.execute(
        text("DELETE FROM scene_categories WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 7. 删除测试用例 (test_cases)
    await conn.execute(
        text("DELETE FROM test_cases WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 8. 删除接口定义 (api_definitions)
    await conn.execute(
        text("DELETE FROM api_definitions WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 9. 删除接口目录 (api_categories)
    await conn.execute(
        text("DELETE FROM api_categories WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 10. 删除环境 (environments)
    await conn.execute(
        text("DELETE FROM environments WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 11. 删除 Mock 规则 (mock_rules)
    await conn.execute(
        text("DELETE FROM mock_rules WHERE project_id = :pid"),
        {"pid": project_id}
    )
    
    # 12. 删除变量 (variables) - scope=project
    await conn.execute(
        text("DELETE FROM variables WHERE scope = 'project' AND scope_id = :pid"),
        {"pid": project_id}
    )
    
    # 13. 删除项目成员 (project_members)
    await conn.execute(
        text("DELETE FROM project_members WHERE project_id = :pid"),
        {"pid": project_id}
    )


async def main():
    parser = argparse.ArgumentParser(description='清理数据库：删除 admin 以外的用户')
    parser.add_argument('--dry-run', action='store_true', help='仅显示将删除的内容，不实际删除')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔧 API Pilot 数据库清理工具")
    print("=" * 60)
    print(f"模式: {'Dry Run (不实际删除)' if args.dry_run else '正式删除'}")
    print("=" * 60 + "\n")
    
    success = await cleanup_database(dry_run=args.dry_run)
    
    if success:
        if args.dry_run:
            print("\n✅ Dry Run 完成。如需实际删除，请移除 --dry-run 参数")
        else:
            print("\n✅ 数据库清理完成")
        return 0
    else:
        print("\n❌ 清理失败")
        return 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
