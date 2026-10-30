"""market 域 —— C 端路由的认证依赖。

`/market/mini/*` 的语义是「登录用户即可用」，但**登录用户不等于 C 端成员**：这个系统里
运营和 C 端共用一张 `sys_user`。本依赖把「C 端身份」显式化：

1. 取当前登录用户（复用基座的 ``get_current_user``）；
2. **首次访问自动建档**（lazy ensure）——无论用户是微信登录、手机号登录还是直接调接口，
   第一个 C 端请求就会落下 `market_member` 记录，不依赖客户端配合；
3. 已停用的成员直接拒绝。

`db_getter` 与路由里用的是同一个依赖，FastAPI 在一次请求内会复用同一会话。
"""

from typing import Annotated

from fastapi import Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.dependencies import db_getter, get_current_user

from .service import MemberService


async def require_market_member(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> AuthSchema:
    """要求登录且是启用状态的 C 端成员；首次访问时自动建档。"""
    await MemberService(auth, db).ensure_active(user_id=auth.user.id)
    return auth


__all__ = ["require_market_member"]
