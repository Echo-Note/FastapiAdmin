"""把 ``sql/sys_menu.json`` 里的图标回填到已初始化的库。

**为什么需要**：种子初始化是「表已有数据就整体跳过」，所以改了 ``sql/sys_menu.json`` 的 ``icon``
只对新库生效；已上线的库看不到新图标，页面侧栏仍是一片空白方块。

本脚本只做一件事——**按「父节点名 → 子节点名」的完整路径匹配**，把种子里的 ``icon`` 覆盖到库里
不一致的菜单行，不动其它字段（避免覆盖运营在「菜单管理」里手改过的排序/名称等）。

幂等：已经是目标图标就跳过；``--dry-run`` 只打印要改的行。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.sync_menu_icons            # dry-run
    PYTHONPATH=. uv run python -m app.scripts.sync_menu_icons --apply    # 落库
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
# 只同步这些顶级目录下的图标（按需扩展）
ROOT_NAMES = ("市场管理",)


def _load_seed() -> tuple[list[dict], dict[str, dict]]:
    """返回 (种子树, {"父路径/名称": 节点})。"""
    data = json.loads((SCRIPT_DIR / SEED_FILE).read_text(encoding="utf-8"))
    flat: dict[str, dict] = {}

    def walk(nodes: list[dict], path: tuple[str, ...]) -> None:
        for node in nodes:
            flat["/".join((*path, node["name"]))] = node
            walk(node.get("children") or [], (*path, node["name"]))

    walk(data, ())
    return data, flat


async def _walk_db(db, nodes: list[MenuModel], path: tuple[str, ...], flat: dict[str, dict], *, apply: bool) -> int:
    """递归比对库内菜单与种子图标，返回变更条数。"""
    changed = 0
    for menu in nodes:
        full_path = "/".join((*path, menu.name))
        seed = flat.get(full_path)
        if seed is None:
            continue
        icon = seed.get("icon")
        if icon and menu.icon != icon:
            if apply:
                menu.icon = icon
                print(f"✅ {full_path}: {icon}")
            else:
                print(f"[dry-run] {full_path}: {menu.icon} → {icon}")
            changed += 1
        children = (
            await db.execute(select(MenuModel).where(MenuModel.parent_id == menu.id).order_by(MenuModel.order))
        ).scalars().all()
        changed += await _walk_db(db, list(children), (*path, menu.name), flat, apply=apply)
    return changed


async def sync(*, apply: bool) -> int:
    """把 ROOT_NAMES 下所有菜单的图标与种子对齐。"""
    _, flat = _load_seed()
    async with async_db_session() as db, db.begin():
        roots = (
            await db.execute(select(MenuModel).where(MenuModel.name.in_(ROOT_NAMES), MenuModel.parent_id.is_(None)))
        ).scalars().all()
        if not roots:
            raise SystemExit(f"库里找不到顶级菜单 {ROOT_NAMES}")
        changed = await _walk_db(db, list(roots), (), flat, apply=apply)
    print(f"{'' if apply else '[dry-run] '}✅ 共 {changed} 个菜单图标需要更新")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="把 sys_menu.json 的图标回填到已有库")
    parser.add_argument("--apply", action="store_true", help="真正写库；缺省只打印将变更的菜单")
    args = parser.parse_args()
    asyncio.run(sync(apply=args.apply))


if __name__ == "__main__":
    main()
