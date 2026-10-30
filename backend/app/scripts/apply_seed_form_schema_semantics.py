"""一次性脚本：改造两张 market 种子 JSON 中 form_schema 的 region/executor 字段语义。

改造规则见 ``app.scripts.form_schema_semantics``，与库内数据迁移脚本共用同一套规则。
幂等：重复执行不会叠加 options / autofill。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.apply_seed_form_schema_semantics
"""

from __future__ import annotations

import json
from typing import Any

from app.config.path_conf import SCRIPT_DIR
from app.scripts.form_schema_semantics import transform_config

# 需要改造的种子文件名（不含 .json 后缀），仅涉及含 form_schema 的叶子模板与三级任务
SEED_FILES: tuple[str, ...] = ("market_task_item", "market_task_template")


def _load(filename: str) -> list[dict[str, Any]]:
    """读取种子 JSON 文件，返回记录列表（缺文件时报错）。"""
    path = SCRIPT_DIR / f"{filename}.json"
    if not path.exists():
        raise FileNotFoundError(f"种子文件不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """改造两张种子 JSON 并写回，打印每文件改造记录数与字段数。"""
    for filename in SEED_FILES:
        data = _load(filename)
        records_changed = 0
        fields_changed = 0
        for record in data:
            config = record.get("config")
            if not isinstance(config, dict):
                continue
            changed = transform_config(config)
            if changed:
                records_changed += 1
                fields_changed += changed

        path = SCRIPT_DIR / f"{filename}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✅ {filename}: 改造 {records_changed} 条记录 / {fields_changed} 个字段")


if __name__ == "__main__":
    main()
