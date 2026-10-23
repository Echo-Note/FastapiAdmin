"""发放额度与个人任务津贴数据模型。

接收/完成任务金额不设上限，但每月实际发放金额受「每月发放额度」封顶（默认 20000，运营可调）。
超出部分累计入「个人任务津贴」，顺延至下月发放。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class PayoutConfigModel(ModelMixin, UserMixin):
    """发放额度配置

    单用户单月实际发放金额上限（默认 20000，运营可调为 10000/20000）。
    """

    __tablename__: str = "market_payout_config"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_market_payout_config_user_period"),
        {"comment": "发放额度配置表"},
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, index=True, comment="C端用户ID")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10)")
    payout_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=20000, comment="每月发放额度(默认 20000)")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")


class AllowanceModel(ModelMixin, UserMixin):
    """个人任务津贴账户

    累计未发放金额，顺延至下月发放。一个用户一条记录。
    """

    __tablename__: str = "market_allowance"
    __table_args__: dict[str, str] = {"comment": "个人任务津贴账户表"}

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, unique=True, index=True, comment="C端用户ID"
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="累计未发放金额")


class AllowanceDetailModel(ModelMixin):
    """津贴明细

    每月结算产生的未发放增量，待下月发放。一期仅记录（不打款），PAID 状态二期支付时写入。
    """

    __tablename__: str = "market_allowance_detail"
    __table_args__: dict[str, str] = {"comment": "津贴明细表"}

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, index=True, comment="C端用户ID")
    from_period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="来源周期(如 2026-10)")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="未发放金额")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True, comment="状态(待发/已发)")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="发放时间(二期)")
