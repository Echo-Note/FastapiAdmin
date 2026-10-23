"""对外服务项目价目及其与对内任务类型的映射数据模型。"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.company.model import CompanyModel
    from app.modules.market.task.model import TaskTypeModel


class ServiceItemModel(ModelMixin, UserMixin):
    """对外服务项目价目

    对应「服务项目结算单」（甲方口径）的一行（服务项目号 1–37）。与对内任务价目独立，金额不挂钩。
    两级结构（类型/项目），无「任务」三级。
    """

    __tablename__: str = "market_service_item"
    __table_args__: dict[str, str] = {"comment": "对外服务项目价目表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="唯一编码")
    service_no: Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True, index=True, comment="服务项目号(1-37)")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="服务项目名(如 等级医院用药数据收集)")
    service_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="对外两级-类型(如 用药数据收集服务)")
    service_item: Mapped[str] = mapped_column(String(64), nullable=False, comment="对外两级-项目(如 等级医院用药数据收集)")
    unit: Mapped[str] = mapped_column(String(32), nullable=False, comment="计费单位(如 元/家/次)")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="对外单价")
    company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("market_company.id", ondelete="SET NULL"), nullable=True, index=True, comment="委托方(医药公司)ID"
    )

    company: Mapped["CompanyModel"] = relationship()
    task_type_links: Mapped[list["ServiceItemTaskModel"]] = relationship(back_populates="service_item", cascade="all, delete-orphan")

    @property
    def task_type_ids(self) -> list[int]:
        """映射的对内任务类型ID列表（需预加载 ``task_type_links``，否则异步环境会触发懒加载）。"""
        return [link.task_type_id for link in self.task_type_links]


class ServiceItemTaskModel(ModelMixin, UserMixin):
    """对内任务 ↔ 对外服务项目映射（多对多）"""

    __tablename__: str = "market_service_item_task"
    __table_args__ = (
        UniqueConstraint("service_item_id", "task_type_id", name="uq_market_service_item_task"),
        {"comment": "对内任务↔对外服务项目映射表"},
    )

    service_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_service_item.id", ondelete="CASCADE"), nullable=False, index=True, comment="对外服务项目ID"
    )
    task_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task_type.id", ondelete="CASCADE"), nullable=False, index=True, comment="对内任务类型(计价项)ID"
    )

    service_item: Mapped["ServiceItemModel"] = relationship(back_populates="task_type_links")
    task_type: Mapped["TaskTypeModel"] = relationship()


__all__ = ["ServiceItemModel", "ServiceItemTaskModel"]
