"""market 域一键重置脚本：清空全部 ``market_`` 表并重播种种子数据。

**为什么需要**：种子初始化 ``InitializeData.__init_data`` 是幂等的（表已有数据即整体跳过），
因此改动 market 域种子文件（``market_task_category.json`` / ``market_task_template.json`` /
``market_task_item.json``）或 ``form_schema`` 结构后，库内旧数据不会被覆盖，会出现
「代码改了、库还是旧的」假象（如三级任务分节缺失）。本脚本清库重播种，一步到位。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.reseed_market

或（仓库根目录）：

    PYTHONPATH=backend uv run python -m app.scripts.reseed_market

非 DEV 环境默认拒绝执行，需显式追加 ``--force``（防误清生产库）。

注意：会清空 market 域**全部**表（含项目/机构/分派/成果/结算等业务数据），仅重播种
「任务分类 → 任务模板 → 三级任务」三张种子表。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.common.enums import EnvironmentEnum
from app.config.path_conf import SCRIPT_DIR
from app.config.setting import settings
from app.core.base_model import MappedBase
from app.core.database import async_db_session
from app.modules.market.task.model import TaskCategoryModel, TaskItemModel, TaskTemplateModel
from app.utils.import_util import ImportUtil

# 全量注册模型：确保 relationship 字符串引用可解析，且所有 market_ 表进入 metadata
_ = ImportUtil.find_models(MappedBase)

# 按依赖顺序重播种（分类 → 模板 → 三级任务），文件名与 __tablename__ 一致
SEED_ORDER: list[tuple[type, str]] = [
    (TaskCategoryModel, "market_task_category"),
    (TaskTemplateModel, "market_task_template"),
    (TaskItemModel, "market_task_item"),
]


def _market_tables() -> list[str]:
    """收集全部 ``market_`` 前缀表名（来自已注册模型 metadata）。"""
    return sorted(name for name in MappedBase.metadata.tables if name.startswith("market_"))


def _load_seed(filename: str) -> list[dict[str, Any]]:
    """读取种子 JSON 文件，返回记录列表（缺文件时报错）。"""
    path: Path = SCRIPT_DIR / f"{filename}.json"
    if not path.exists():
        raise FileNotFoundError(f"种子文件不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


async def main() -> None:
    """清空全部 market_ 表并重播种三张种子表。"""
    if settings.ENVIRONMENT != EnvironmentEnum.DEV and "--force" not in sys.argv:
        print(f"❌ 当前环境为 {settings.ENVIRONMENT}，非 DEV 环境禁止清库。若确认无误，请追加 --force 重新执行。")
        raise SystemExit(1)

    tables = _market_tables()
    if not tables:
        print("⚠️ 未发现任何 market_ 表，请确认模型已正确注册。")
        raise SystemExit(1)

    async with async_db_session() as db, db.begin():
        _ = await db.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"))
        for model, filename in SEED_ORDER:
            data = _load_seed(filename)
            db.add_all([model(**item) for item in data])
            print(f"✅ 已重播种 {filename}: {len(data)} 条")
        await db.flush()

    print(f"✅ market 域已重置：清空 {len(tables)} 张表，重播种 3 张种子表。")


if __name__ == "__main__":
    asyncio.run(main())
