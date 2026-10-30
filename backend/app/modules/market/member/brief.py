"""market 域的 C 端用户摘要。

market 只持有 `sys_user.id`（没有跨域 relationship），但运营端的所有列表都要回答「这是谁」。
只写 ``user_id`` 等于让前端拿一个自增数字认人——重名、改名、多个 `普通用户` 时无法区分，
手机号才是医药业务里真正的识别手段。

因此本模块提供两样东西，供结算 / 发放等出参复用：

- :class:`MarketUserBriefSchema`：``{id, name, username, mobile}`` 的稳定摘要结构；
- :func:`load_user_briefs`：按 id 批量取摘要（一次查询，避免逐行 N+1）。

口径：**用户摘要一律由后端带回，前端不再自己拉全量用户表去反查**。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.user.model import UserModel


class MarketUserBriefSchema(BaseModel):
    """C 端用户摘要（出参用）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="用户ID")
    name: str = Field(description="昵称")
    username: str = Field(description="登录账号")
    mobile: str | None = Field(default=None, description="手机号")


async def load_user_briefs(db: AsyncSession, user_ids: Any) -> dict[int, MarketUserBriefSchema]:
    """按 id 批量取用户摘要，返回 ``{user_id: brief}``；查不到的 id 不出现在结果里。

    :param db: 数据库会话
    :param user_ids: 任意可迭代的用户 id 集合（会自动去重、过滤空值）
    """
    ids = {int(uid) for uid in user_ids if uid}
    if not ids:
        return {}
    rows = await db.execute(select(UserModel).where(UserModel.id.in_(ids)))
    return {user.id: MarketUserBriefSchema.model_validate(user) for user in rows.scalars()}


__all__ = ["MarketUserBriefSchema", "load_user_briefs"]
