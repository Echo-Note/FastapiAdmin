"""把「市场管理 → 成员管理」菜单同步进已初始化的库。

**为什么需要**：种子初始化是按「表已有数据就整体跳过」实现的，因此改了 ``sql/sys_menu.json``
只对新库生效，已上线的库拿不到新菜单——页面写好了却点不进去。

本脚本以 ``sql/sys_menu.json`` 为唯一真相源，按「父节点名 + 节点名」幂等 upsert
``成员管理`` 及其按钮子节点（已存在则更新 permission/路由等字段，不重复插入）。

超管账号（``is_superuser=true``）默认可见全部菜单，无需额外授权；非超管角色仍需在
「系统管理 → 角色管理」里勾选新菜单（脚本会把这一步提示出来）。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.sync_member_menu            # dry-run
    PYTHONPATH=. uv run python -m app.scripts.sync_member_menu --apply    # 落库
"""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import select

from app.config.path_conf import SCRIPT_DIR
from app.core.base_model import MappedBase
from app.core.database import async_db_session
from app.modules.system.menu.model import MenuModel
from app.utils.import_util import ImportUtil

_ = ImportUtil.find_models(MappedBase)

SEED_FILE = "sys_menu.json"
PARENT_NAME = "市场管理"
NODE_NAME = "成员管理"

# 允许写库的字段（其余如 id/parent_id 由脚本按层级决定）
_FIELDS = (
    "name",
    "type",
    "order",
    "permission",
    "icon",
    "route_name",
    "route_path",
    "component_path",
    "redirect",
    "hidden",
    "keep_alive",
    "always_show",
    "title",
    "params",
    "affix",
    "link",
    "is_iframe",
    "is_hide_tab",
    "active_path",
    "show_badge",
    "show_text_badge",
    "status",
    "description",
)


def _load_node() -> dict:
    """从种子文件里取出「成员管理」节点定义。"""
    path = SCRIPT_DIR / SEED_FILE
    data = json.loads(path.read_text(encoding="utf-8"))

    def find(nodes: list[dict], name: str) -> dict | None:
        for node in nodes:
            if node.get("name") == name:
                return node
            found = find(node.get("children") or [], name)
            if found is not None:
                return found
        return None

    parent = find(data, PARENT_NAME)
    if parent is None:
        raise SystemExit(f"种子文件里找不到「{PARENT_NAME}」")
    node = next((child for child in parent.get("children") or [] if child.get("name") == NODE_NAME), None)
    if node is None:
        raise SystemExit(f"种子文件里找不到「{PARENT_NAME} → {NODE_NAME}」")
    return node


async def _upsert(db, parent_id: int | None, node: dict, *, apply: bool) -> int:
    """按 (parent_id, name) upsert 一个节点，返回其 id（dry-run 时不存在则返回 0）。"""
    existing = await db.scalar(
        select(MenuModel).where(MenuModel.name == node["name"], MenuModel.parent_id == parent_id)
    )
    values = {key: node.get(key) for key in _FIELDS if key in node}
    if existing is None:
        if not apply:
            print(f"[dry-run] 将新增菜单「{node['name']}」（父节点 id={parent_id}）")
            return 0
        menu = MenuModel(**values, parent_id=parent_id)
        db.add(menu)
        await db.flush()
        print(f"✅ 新增菜单「{node['name']}」id={menu.id}")
        return menu.id

    changed = [key for key, value in values.items() if getattr(existing, key) != value]
    if changed:
        if apply:
            for key, value in values.items():
                setattr(existing, key, value)
            print(f"✅ 更新菜单「{node['name']}」字段: {changed}")
        else:
            print(f"[dry-run] 将更新菜单「{node['name']}」字段: {changed}")
    else:
        print(f"⏭️  菜单「{node['name']}」已是最新")
    return existing.id


async def sync(*, apply: bool) -> None:
    node = _load_node()
    async with async_db_session() as db, db.begin():
        parent = await db.scalar(select(MenuModel).where(MenuModel.name == PARENT_NAME, MenuModel.parent_id.is_(None)))
        if parent is None:
            parent = await db.scalar(select(MenuModel).where(MenuModel.name == PARENT_NAME))
        if parent is None:
            raise SystemExit(f"库里找不到「{PARENT_NAME}」菜单，请先在菜单管理里创建")

        menu_id = await _upsert(db, parent.id, node, apply=apply)
        for child in node.get("children") or []:
            await _upsert(db, menu_id or 0, child, apply=apply)

    print(
        "\n提示：超管（is_superuser=true）无需授权即可看到新菜单；"
        "其他角色请到「系统管理 → 角色管理」勾选「市场管理 → 成员管理」。"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="同步「市场管理 → 成员管理」菜单到已有库")
    parser.add_argument("--apply", action="store_true", help="真正写库；缺省只打印将变更的内容")
    args = parser.parse_args()
    asyncio.run(sync(apply=args.apply))


if __name__ == "__main__":
    main()
