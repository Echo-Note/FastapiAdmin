"""初始化 C 端账号与角色（幂等）。

功能：
  1. 确保角色「普通用户」(USER) 存在。
  2. 关联 USER 角色到 C 端专属菜单（scope=app：首页/同事/打卡/消息/我的），
     不授予任何管理端（web）菜单权限。
  3. 创建账号 user（角色 USER，非超管，data_scope=仅本人）。

环境变量：
    C_USER_USERNAME  C 端账号名（默认 user）
    C_USER_PASSWORD  C 端密码（必填）

执行（后端容器内）：
    C_USER_PASSWORD=xxx python init_c_account.py
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.dept.model import DeptModel
from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleModel
from app.modules.system.user.model import UserModel, UserRolesModel

from base import PwdUtil, async_db_session, bind_menus_to_role, env


async def ensure_role(db: AsyncSession, code: str, name: str, data_scope: int, description: str) -> RoleModel:
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


async def ensure_user(
    db: AsyncSession, username: str, password: str, name: str, dept_id: int | None, description: str
) -> UserModel:
    """按 username 幂等获取账号，不存在则创建（已存在则更新密码）。"""
    user = (
        await db.execute(select(UserModel).where(UserModel.username == username))
    ).scalar_one_or_none()
    if user is None:
        user = UserModel(
            username=username,
            password=PwdUtil.hash_password(password),
            name=name,
            is_superuser=False,
            dept_id=dept_id,
            status=0,
            description=description,
        )
        db.add(user)
        await db.flush()
        print(f"  新建账号：{username}")
    else:
        user.password = PwdUtil.hash_password(password)
        user.status = 0
        print(f"  账号已存在（更新密码）：{username}")
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
    username = env("C_USER_USERNAME", "user")
    password = env("C_USER_PASSWORD", "")

    if not password:
        raise SystemExit("缺少 C_USER_PASSWORD 环境变量")

    async with async_db_session() as db:
        dept = (
            await db.execute(select(DeptModel).where(DeptModel.code == "DEFAULT"))
        ).scalar_one_or_none()
        dept_id = dept.id if dept else None

        print("== 角色 ==")
        role = await ensure_role(db, "USER", "普通用户", 1, "C 端普通用户")

        # C 端专属菜单：scope=app（首页/同事/打卡/消息/我的）
        print("== 菜单关联 ==")
        app_menus = (
            await db.execute(select(MenuModel).where(MenuModel.scope == "app"))
        ).scalars().all()
        app_ids = [m.id for m in app_menus]
        added = await bind_menus_to_role(db, role, app_ids)
        print(f"  USER 角色关联 C 端菜单 {len(app_ids)} 个（本次新增 {added}）")

        print("== 账号 ==")
        user = await ensure_user(db, username, password, "普通用户", dept_id, "C 端普通用户账号")

        print("== 关联 ==")
        await bind_role(db, user, role)

        await db.commit()
        print("C 端账号与角色初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
