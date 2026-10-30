"""一次性脚本：把机构管理 5 类采集表的 ``form_schema`` 对齐到真实 Excel 采集表。

字段定义见 ``app.modules.market.task.collection_schema``（种子与库内订正共用同一份生成源）。
两件事分开做，按需执行：

- ``--seed``：按三级任务编号重写 ``backend/sql/market_task_item.json`` 的 ``config.form_schema``
  （只动对齐范围内的 26 条，其余字段与记录原样保留）；
- ``--db``：就地把已初始化库里的 ``market_task_item.config.form_schema`` 换成对齐后的结构
  （深拷贝后回写，JSONB 列才识别为变更；已提交成果的 ``form_data`` 不动）。

幂等：重复执行结果一致；``--dry-run`` 只打印将要变更的编号。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.apply_collection_schema --seed --db
    PYTHONPATH=. uv run python -m app.scripts.apply_collection_schema --db --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
from typing import Any

from sqlalchemy import select

from app.config.path_conf import SCRIPT_DIR
from app.core.base_model import MappedBase
from app.core.database import async_db_session
from app.modules.market.task.collection_schema import ITEM_FORM_SCHEMAS
from app.modules.market.task.model import TaskItemModel
from app.utils.import_util import ImportUtil

# 全量注册模型：确保 relationship 字符串引用可解析
_ = ImportUtil.find_models(MappedBase)

SEED_FILE = "market_task_item.json"


def _prune(value: Any) -> Any:
    """递归去掉 False 的 ``required`` 与空值，让种子 JSON 与旧格式一样只保留有意义的键。"""
    if isinstance(value, dict):
        return {k: _prune(v) for k, v in value.items() if not (k == "required" and v is False) and v is not None}
    if isinstance(value, list):
        return [_prune(item) for item in value]
    return value


def _dump(schema: Any) -> list[dict[str, Any]]:
    """把 pydantic ``FormSchema`` 转成可直接写 JSON 的纯字典列表（排除 None 值与 False 的 required）。"""
    return [_prune(section.model_dump(exclude_none=True)) for section in schema]


def _aligned_codes() -> list[str]:
    return sorted(ITEM_FORM_SCHEMAS)


def apply_seed(*, dry_run: bool) -> int:
    """把对齐后的 ``form_schema`` 写回种子 JSON，返回变更的记录数。"""
    path = SCRIPT_DIR / SEED_FILE
    if not path.exists():
        raise FileNotFoundError(f"种子文件不存在: {path}")

    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for record in data:
        code = record.get("code")
        schema = ITEM_FORM_SCHEMAS.get(str(code))
        if schema is None:
            continue
        config = record.get("config")
        if not isinstance(config, dict):
            continue
        new_schema = _dump(schema)
        if config.get("form_schema") == new_schema:
            continue
        config["form_schema"] = new_schema
        changed += 1

    if not dry_run and changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'[dry-run] ' if dry_run else ''}✅ 种子 {SEED_FILE}: 变更 {changed} 条 / 对齐范围 {len(ITEM_FORM_SCHEMAS)} 条")
    return changed


async def apply_db(*, dry_run: bool) -> int:
    """把对齐后的 ``form_schema`` 写回库中 ``market_task_item`` 记录，返回变更的记录数。"""
    codes = _aligned_codes()
    changed = 0
    async with async_db_session() as db, db.begin():
        result = await db.execute(select(TaskItemModel).where(TaskItemModel.code.in_(codes)))
        for record in result.scalars():
            schema = ITEM_FORM_SCHEMAS[record.code]
            new_schema = _dump(schema)
            config = record.config
            if not isinstance(config, dict) or config.get("form_schema") == new_schema:
                continue
            if dry_run:
                print(f"[dry-run] 将订正 {record.code} {record.name}")
                changed += 1
                continue
            # 深拷贝后回写：就地改 dict 不会被 JSONB 列识别为变更（JSON 类型 mutable=False）
            new_config = copy.deepcopy(config)
            new_config["form_schema"] = new_schema
            record.config = new_config
            changed += 1
    print(f"{'[dry-run] ' if dry_run else ''}✅ 库内 market_task_item: 变更 {changed} 条 / 对齐范围 {len(codes)} 条")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="对齐机构管理采集表的 form_schema（种子 / 库内）")
    parser.add_argument("--seed", action="store_true", help="重写 backend/sql/market_task_item.json")
    parser.add_argument("--db", action="store_true", help="订正库里已有的 market_task_item 记录")
    parser.add_argument("--dry-run", action="store_true", help="只打印将变更的记录，不落盘/不提交")
    args = parser.parse_args()

    if not args.seed and not args.db:
        parser.error("至少指定 --seed 或 --db")

    if args.seed:
        apply_seed(dry_run=args.dry_run)
    if args.db:
        asyncio.run(apply_db(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
