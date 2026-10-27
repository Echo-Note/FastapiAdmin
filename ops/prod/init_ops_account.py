"""初始化运营端账号与角色（幂等）。

功能：
  1. 确保角色「管理员」(ADMIN)、「运营」(OPERATOR) 存在。
  2. 确保「运营工作台」菜单（目录 + 工作台概览）存在。
  3. 运营角色关联：运营工作台 + 市场管理全部菜单（不含其它域）。
  4. 创建账号 admin（超管，角色 ADMIN）、operator（角色 OPERATOR，仅运营工作台 + 市场管理）。

环境变量：
    OPS_ADMIN_USERNAME    管理员账号名（默认 admin）
    OPS_ADMIN_PASSWORD    管理员密码（必填）
    OPS_OPERATOR_USERNAME 运营账号名（默认 operator）
    OPS_OPERATOR_PASSWORD 运营密码（必填）

执行（后端容器内）：
    OPS_ADMIN_PASSWORD=xxx OPS_OPERATOR_PASSWORD=xxx python init_ops_account.py
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.dept.model import DeptModel
from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleModel
from app.modules.system.user.model import UserModel, UserRolesModel

from base import (
    PasswordHash,
    async_db_session,
    bind_menus_to_role,
    collect_subtree_ids,
    ensure_menu,
    env,
)


async def ensure_role(
    db: AsyncSession, code: str, name: str, data_scope: int, description: str
) -> RoleModel:
    """按 code 幂等获取角色，不存在则创建。"""
    role = (
        await db.execute(select(RoleModel).where(RoleModel.code == code))
    ).scalar_one_or_none()
    if role is None:
        role = RoleModel(
            name=name,
            code=code,
            order=999,
            status=0,
            data_scope=data_scope,
            description=description,
        )
        db.add(role)
        await db.flush()
        print(f"  新建角色：{name}({code})")
    else:
        print(f"  角色已存在：{name}({code})")
    return role


async def ensure_dashboard_menu(db: AsyncSession) -> tuple[MenuModel, MenuModel]:
    """确保运营工作台菜单（目录 + 概览子菜单）存在，返回 (目录, 子菜单)。"""
    dash_dir = await ensure_menu(
        db,
        name="运营工作台",
        menu_type=1,
        route_path="/ops-dashboard",
        route_name="OpsDashboard",
        icon="ri:dashboard-line",
        order=0,
    )
    dash_overview = await ensure_menu(
        db,
        name="工作台概览",
        menu_type=2,
        route_path="overview",
        component_path="module_market/dashboard/index",
        permission="module_market:dashboard:query",
        route_name="OpsDashboardOverview",
        icon="ri:dashboard-3-line",
        parent_id=dash_dir.id,
        order=1,
    )
    return dash_dir, dash_overview


async def ensure_user(
    db: AsyncSession,
    username: str,
    password: str,
    name: str,
    is_superuser: bool,
    dept_id: int | None,
    description: str,
) -> UserModel:
    """按 username 幂等获取账号，不存在则创建（已存在则更新密码/状态）。"""
    user = (
        await db.execute(select(UserModel).where(UserModel.username == username))
    ).scalar_one_or_none()
    if user is None:
        user = UserModel(
            username=username,
            password=PasswordHash.hash_password(password),
            name=name,
            is_superuser=is_superuser,
            dept_id=dept_id,
            status=0,
            description=description,
        )
        db.add(user)
        await db.flush()
        print(f"  新建账号：{username}")
    else:
        user.password = PasswordHash.hash_password(password)
        user.name = name
        user.is_superuser = is_superuser
        user.status = 0
        print(f"  账号已存在（更新密码/状态）：{username}")
    return user


async def bind_role(db: AsyncSession, user: UserModel, role: RoleModel) -> None:
    """建立账号-角色关联（幂等）。"""
    bound = (
        await db.execute(
            select(UserRolesModel).where(
                UserRolesModel.user_id == user.id,
                UserRolesModel.role_id == role.id,
            )
        )
    ).scalar_one_or_none()
    if bound is None:
        db.add(UserRolesModel(user_id=user.id, role_id=role.id))
        print(f"  账号「{user.username}」关联角色「{role.name}」")


async def main() -> None:
    admin_username = env("OPS_ADMIN_USERNAME", "admin")
    admin_password = env("OPS_ADMIN_PASSWORD", "")
    operator_username = env("OPS_OPERATOR_USERNAME", "operator")
    operator_password = env("OPS_OPERATOR_PASSWORD", "")

    if not admin_password or not operator_password:
        raise SystemExit("缺少 OPS_ADMIN_PASSWORD / OPS_OPERATOR_PASSWORD 环境变量")

    async with async_db_session() as db:
        dept = (
            await db.execute(select(DeptModel).where(DeptModel.code == "DEFAULT"))
        ).scalar_one_or_none()
        dept_id = dept.id if dept else None

        print("== 角色 ==")
        admin_role = await ensure_role(db, "ADMIN", "管理员", 3, "运营端管理员")
        operator_role = await ensure_role(db, "OPERATOR", "运营", 3, "运营端运营人员")

        print("== 菜单 ==")
        dash_dir, dash_overview = await ensure_dashboard_menu(db)
        await db.flush()

        # 市场管理目录及其全部子菜单（含 type=3 按钮权限点）
        all_menus = (await db.execute(select(MenuModel))).scalars().all()
        market_dir = next(
            (m for m in all_menus if m.route_path == "/market" and m.parent_id is None),
            None,
        )
        market_ids = collect_subtree_ids(all_menus, market_dir.id) if market_dir else []

        # 运营角色只关联：运营工作台 + 市场管理
        print("== 菜单关联 ==")
        ops_menu_ids = [dash_dir.id, dash_overview.id, *market_ids]
        added = await bind_menus_to_role(db, operator_role, ops_menu_ids)
        print(f"  运营角色关联菜单 {len(ops_menu_ids)} 个（本次新增 {added}）")

        print("== 账号 ==")
        admin_user = await ensure_user(
            db, admin_username, admin_password, "管理员", True, dept_id, "运营端管理员账号"
        )
        operator_user = await ensure_user(
            db, operator_username, operator_password, "运营", False, dept_id, "运营端运营账号"
        )

        print("== 关联 ==")
        await bind_role(db, admin_user, admin_role)
        await bind_role(db, operator_user, operator_role)

        await db.commit()
        print("运营端账号与角色初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
