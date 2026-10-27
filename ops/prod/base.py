"""生产环境初始化脚本公共模块。

供 ``ops/prod/`` 下各初始化脚本 import，统一提供：
- 模型全量注册（确保含 FK 的 mapper 可完整解析）
- 异步数据库会话 ``async_db_session``
- 密码哈希 ``PwdUtil``
- 环境变量读取辅助 ``env``（自动加载脚本同目录的 ``.env``）
- 菜单/角色辅助（``ensure_menu`` / ``collect_subtree_ids`` / ``bind_menus_to_role``）

执行方式（需在后端容器内运行，app 包位于 ``/home/app``）：
    docker exec -w /home -e PYTHONPATH=/home:/tmp/ops_prod foxwork-backend \\
        python /tmp/ops_prod/init_xxx.py
"""
import os
from pathlib import Path

from sqlalchemy import select

from app.core.base_model import MappedBase
from app.core.database import async_db_session
from app.utils.import_util import ImportUtil
from app.utils.password_util import PwdUtil

# 全量注册模型：确保 StorageNodeModel/UserModel/RoleModel/MenuModel 等含 FK 的 mapper 可完整解析
ImportUtil.find_models(MappedBase)

from app.modules.system.menu.model import MenuModel  # noqa: E402
from app.modules.system.role.model import RoleMenusModel, RoleModel  # noqa: E402


def load_env() -> None:
    """从脚本同目录的 ``.env`` 加载环境变量（已存在的环境变量优先，不覆盖）。"""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default: str = "") -> str:
    """读取环境变量，未设置时返回默认值。"""
    return os.environ.get(name, default)


async def ensure_menu(
    db,
    *,
    name: str,
    menu_type: int,
    route_path: str,
    component_path: str | None = None,
    permission: str | None = None,
    parent_id: int | None = None,
    icon: str | None = None,
    route_name: str | None = None,
    scope: str = "web",
    order: int = 999,
) -> MenuModel:
    """按 ``route_path + parent_id`` 幂等获取菜单，不存在则创建。"""
    menu = (
        await db.execute(
            select(MenuModel).where(
                MenuModel.route_path == route_path,
                MenuModel.parent_id == parent_id,
            )
        )
    ).scalar_one_or_none()
    if menu is None:
        menu = MenuModel(
            name=name,
            type=menu_type,
            route_path=route_path,
            component_path=component_path,
            permission=permission,
            parent_id=parent_id,
            icon=icon,
            route_name=route_name,
            scope=scope,
            order=order,
            status=0,
            title=name,
        )
        db.add(menu)
        await db.flush()
        print(f"  新建菜单：{name}")
    else:
        print(f"  菜单已存在：{name}")
    return menu


def collect_subtree_ids(menu_rows: list[MenuModel], root_id: int) -> list[int]:
    """收集 ``root_id`` 及其所有后代菜单 ID（按 parent_id 建映射做 BFS）。"""
    children: dict[int | None, list[int]] = {}
    for m in menu_rows:
        children.setdefault(m.parent_id, []).append(m.id)
    result: list[int] = []
    stack = [root_id]
    while stack:
        cur = stack.pop()
        result.append(cur)
        stack.extend(children.get(cur, []))
    return result


async def bind_menus_to_role(db, role: RoleModel, menu_ids: list[int]) -> int:
    """把菜单 ID 列表关联到角色（幂等，返回本次新增数量）。"""
    bound = set(
        (
            await db.execute(
                select(RoleMenusModel.menu_id).where(RoleMenusModel.role_id == role.id)
            )
        ).scalars().all()
    )
    added = 0
    for mid in menu_ids:
        if mid not in bound:
            db.add(RoleMenusModel(role_id=role.id, menu_id=mid))
            added += 1
    return added


# import 本模块时自动加载 .env，使各脚本无需手动 export
load_env()

__all__ = [
    "MappedBase",
    "ImportUtil",
    "async_db_session",
    "PwdUtil",
    "env",
    "ensure_menu",
    "collect_subtree_ids",
    "bind_menus_to_role",
]
