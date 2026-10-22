from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class QuotaConfigModel(ModelMixin, UserMixin):
    """限额配置

    单用户单周期可结算金额上限（如 10000 / 20000），运营端可配置。
    """

    __tablename__: str = "market_quota_config"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_market_quota_config_user_period"),
        {"comment": "限额配置表"},
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, index=True, comment="C端用户ID")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10)")
    quota_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="限额额度")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")


class QuotaUsageModel(ModelMixin):
    """限额使用（累计）

    系统按「用户 × 周期」累计：累计接收金额、累计应发金额、累计超限金额。
    一期只计算与展示，不做实际打款。
    """

    __tablename__: str = "market_quota_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_market_quota_usage_user_period"),
        {"comment": "限额使用表"},
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, index=True, comment="C端用户ID")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10)")
    received_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="累计接收金额")
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="累计应发金额")
    over_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="累计超限金额")


class QuotaCarryoverModel(ModelMixin):
    """顺延金额明细

    应发金额超出限额的部分滚入下一周期，优先于下一周期新增应发金额结算。
    """

    __tablename__: str = "market_quota_carryover"
    __table_args__: dict[str, str] = {"comment": "顺延金额表"}

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, index=True, comment="C端用户ID")
    from_period: Mapped[str] = mapped_column(String(16), nullable=False, comment="来源周期(如 2026-10)")
    to_period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="顺延至周期(如 2026-11)")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="顺延金额")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True, comment="顺延状态(待结算/已结算)")
