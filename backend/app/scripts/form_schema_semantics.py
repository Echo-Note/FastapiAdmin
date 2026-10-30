"""采集表单字段语义改造规则（region/executor）的权威实现。

本模块被两处复用，确保「种子 JSON」与「库内存量数据」使用同一套改造规则，避免漂移：
- ``apply_seed_form_schema_semantics``：改造 ``backend/sql`` 下的两张种子 JSON。
- ``migrate_form_schema_semantics``：改造库内 ``market_task_item`` / ``market_task_template``。

改造规则（按字段名匹配，不按 label）：
- ``region``（区域）：自由填写 ``text`` → ``type=region``（全国省市区三级联动选择，前端内置行政区划数据渲染）。
- ``executor``（执行人）：新增 ``autofill=current_user``，前端据此自动填当前登录用户并只读。

所有函数幂等：重复执行不会重复叠加 autofill / 残留 options。
"""

from __future__ import annotations

from typing import Any

# 需要改造的字段名集合（按字段名匹配，而非 label）
_TARGET_FIELDS: frozenset[str] = frozenset({"region", "executor"})


def transform_field(name: str, field: dict[str, Any]) -> bool:
    """对单个字段定义应用语义改造，返回是否发生变更（幂等）。

    参数:
    - name (str): 字段名（region / executor）。
    - field (dict[str, Any]): 字段定义（就地修改）。

    返回:
    - bool: 是否发生实际变更。
    """
    if name == "region":
        changed = False
        if field.get("type") != "region":
            field["type"] = "region"
            changed = True
        # 移除旧版静态选项（七大区 → 省市区联动，不再需要 options）
        if "options" in field:
            field.pop("options")
            changed = True
        return changed
    if name == "executor":
        if field.get("autofill") != "current_user":
            field["autofill"] = "current_user"
            return True
        return False
    return False


def _transform_node(node: Any) -> int:
    """递归遍历 JSON 节点，对命中字段应用改造，返回改造字段数（幂等）。"""
    changed = 0
    if isinstance(node, dict):
        for key, value in list(node.items()):
            # 命中字段名（region/executor）且值为字段定义 dict 时改造
            if key in _TARGET_FIELDS and isinstance(value, dict):
                if transform_field(key, value):
                    changed += 1
            changed += _transform_node(value)
    elif isinstance(node, list):
        for item in node:
            changed += _transform_node(item)
    return changed


def transform_config(config: dict[str, Any]) -> int:
    """递归改造 ``config`` 中所有 region/executor 字段，返回改造字段数（幂等）。

    参数:
    - config (dict[str, Any]): 任务/模板的配置字典（就地修改）。

    返回:
    - int: 本次实际发生变更的字段数。
    """
    return _transform_node(config)
