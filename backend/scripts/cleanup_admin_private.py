"""删除 admin 创建的私有项目，只保留种子项目"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine

async def cleanup():
    async with engine.begin() as conn:
        # 删除 admin 创建的所有私有项目（非种子）
        result = await conn.execute(text(
            "SELECT id, name FROM projects WHERE created_by = 1 AND global_demo = 0"
        ))
        projects = result.fetchall()

        print(f'发现 {len(projects)} 个 admin 的私有项目')

        for proj_id, proj_name in projects:
            print(f'  删除: {proj_name} (id={proj_id})')
            # 删除关联数据
            await conn.execute(text('DELETE FROM report_steps WHERE report_id IN (SELECT id FROM test_reports WHERE project_id = :pid)'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM test_reports WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM scene_edges WHERE scene_id IN (SELECT id FROM test_scenes WHERE project_id = :pid)'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM scene_steps WHERE scene_id IN (SELECT id FROM test_scenes WHERE project_id = :pid)'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM test_scenes WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM scene_categories WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM test_cases WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM api_definitions WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM api_categories WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM environments WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM mock_rules WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text("DELETE FROM variables WHERE scope = 'project' AND scope_id = :pid"), {'pid': proj_id})
            await conn.execute(text('DELETE FROM project_members WHERE project_id = :pid'), {'pid': proj_id})
            await conn.execute(text('DELETE FROM projects WHERE id = :pid'), {'pid': proj_id})

        # 验证
        print()
        print('清理后项目列表:')
        result = await conn.execute(text('SELECT id, name, global_demo FROM projects'))
        for row in result.fetchall():
            print(f'  id={row[0]}, name={row[1]}, global_demo={row[2]}')

        print()
        print('✅ 清理完成')

if __name__ == "__main__":
    asyncio.run(cleanup())
