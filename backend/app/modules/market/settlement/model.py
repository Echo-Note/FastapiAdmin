from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.task.model import TaskModel


class SettlementModel(ModelMixin, UserMixin):
    """归集结算单（头）

    任务截止后，对「用户 × 任务」下所有审核通过的成果汇总，按结算单结构计算金额。
    一期只计算应发金额、不打款；实发金额/支付状态字段预留二期支付。
    """

    __tablename__: str = "market_settlement"
    __table_args__: dict[str, str] = {"comment": "归集结算单表"}

    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_task.id", ondelete="RESTRICT"), nullable=False, index=True, comment="任务ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False, index=True, comment="C端用户ID")
    qty: Mapped[int] = mapped_column(Integer, nullable=False, comment="归集成果数量")
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="应发金额")
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, comment="实发金额(预留,二期支付)")
    pay_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="支付状态(预留,二期支付)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True, comment="结算单状态")

    task: Mapped["TaskModel"] = relationship()
    items: Mapped[list["SettlementItemModel"]] = relationship(back_populates="settlement", cascade="all, delete-orphan")


class SettlementItemModel(ModelMixin):
    """结算明细（行）

    对应附件结算单行结构：序号 | 服务项目(类型/项目/任务) | 费用标准(单位/单价) | 执行要求 | 实际执行。
    """

    __tablename__: str = "market_settlement_item"
    __table_args__: dict[str, str] = {"comment": "结算明细表"}

    settlement_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_settlement.id", ondelete="CASCADE"), nullable=False, index=True, comment="结算单ID")
    service_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="服务项目-类型")
    service_item: Mapped[str] = mapped_column(String(64), nullable=False, comment="服务项目-项目")
    service_task: Mapped[str] = mapped_column(String(64), nullable=False, comment="服务项目-任务")
    unit: Mapped[str] = mapped_column(String(32), nullable=False, comment="计价单位")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="单价")
    qty: Mapped[int] = mapped_column(Integer, nullable=False, comment="数量")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="金额")

    settlement: Mapped["SettlementModel"] = relationship(back_populates="items")
