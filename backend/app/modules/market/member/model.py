"""C 端成员档案（market_member）。

## 为什么需要这张表

系统只有一张 `sys_user`，运营（B 端）与 C 端用户共用它。在此之前**没有任何地方能判定
「这个账号是不是 C 端」**：`/market/mini/*` 只校验登录，而微信小程序首次登录自动注册的用户
拿到的是默认角色（历史默认值是「管理员」）。于是「谁是 C 端用户」既无法查询、也无法校验。

本表把「C 端身份」从权限体系里独立出来：**存在一条 `market_member` 记录 = 该用户是 C 端成员**。
理由：

- 身份是单值语义，不该靠「碰巧拥有某个角色」推断（角色是多对多，一个运营可能也有普通角色）；
- C 端将来要专属档案（实名、收款账户——二期打款必需），需要一张自己的表；
- 归属在 market 域内，不侵入基座的 `sys_user`。

## 建档时机

- **C 端接口首访自动建档**（`get_market_member` 依赖里的 lazy ensure）——微信登录、手机号登录、
  直连接口全部覆盖，不依赖客户端配合；
- **微信小程序登录后主动补一手**（best-effort，失败不影响登录）；
- **运营端手动纳入**（成员管理页把已有 `sys_user` 建档）。

建档是幂等的：`user_id` 唯一，并发重复建档按唯一约束兜底回落查询。
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin

from ..enums import MemberStatus


class MemberModel(ModelMixin, UserMixin):
    """C 端成员档案（一个用户最多一条）。"""

    __tablename__: str = "market_member"
    __table_args__: dict[str, str] = {"comment": "C端成员档案表"}

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="C端用户ID(sys_user.id)",
    )
    member_no: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True, comment="成员编号(如 U-0001)"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=MemberStatus.ACTIVE.value, index=True, comment="成员状态(启用/停用)"
    )


__all__ = ["MemberModel"]
