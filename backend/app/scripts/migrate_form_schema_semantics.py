"""一次性数据迁移：改造库内 ``market_task_item`` / ``market_task_template`` 的 form_schema 语义。

改造规则见 ``app.scripts.form_schema_semantics``（与种子改造脚本共用同一套规则）。
不 TRUNCATE、不清库，仅就地更新 ``config`` JSONB 列；幂等，重复执行不会叠加 options / autofill。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.migrate_form_schema_semantics
"""

from __future__ import annotations

import asyncio
import copy

from sqlalchemy import select

from app.core.base_model import MappedBase
from app.core.database import async_db_session
from app.modules.market.task.model import TaskItemModel, TaskTemplateModel
from app.scripts.form_schema_semantics import transform_config
from app.utils.import_util import ImportUtil

# 全量注册模型：确保 relationship 字符串引用可解析，且所有表进入 metadata
_ = ImportUtil.find_models(MappedBase)

# 迁移目标模型（表顺序：先模板后任务，与种子依赖顺序一致）
MIGRATE_MODELS: tuple[type, ...] = (TaskTemplateModel, TaskItemModel)


async def _migrate_table(model: type) -> tuple[int, int, int]:
    """迁移单表所有记录的 config，返回 (总记录数, 改造记录数, 改造字段数)。

    参数:
    - model (type): 目标 ORM 模型（config 列为 JSONB）。

    返回:
    - tuple[int, int, int]: (总记录数, 改造记录数, 改造字段数)。
    """
    total = 0
    rows_changed = 0
    fields_changed = 0
    async with async_db_session() as db, db.begin():
        result = await db.execute(select(model))
        for record in result.scalars():
            total += 1
            config = record.config
            if not isinstance(config, dict):
                continue
            # 深拷贝后改造再回写：就地改 dict 不会被 JSONB 列识别为变更（JSON 类型 mutable=False）
            new_config = copy.deepcopy(config)
            changed = transform_config(new_config)
            if changed:
                record.config = new_config
                rows_changed += 1
                fields_changed += changed
    return total, rows_changed, fields_changed


async def main() -> None:
    """遍历两张表执行迁移并打印改造统计。"""
    for model in MIGRATE_MODELS:
        total, rows_changed, fields_changed = await _migrate_table(model)
        print(f"✅ {model.__tablename__}: 共 {total} 条，改造 {rows_changed} 条 / {fields_changed} 个字段")


if __name__ == "__main__":
    asyncio.run(main())
