"""项目（对外）与项目-任务归集数据模型。

项目是面向委托方（医药公司）的交付/结算单元，任务是对内执行单元。
一个项目可归集多个任务，一个任务可归集到多个项目（多对多），项目金额与任务金额不挂钩。
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.company.model import CompanyModel
    from app.modules.market.task.model import TaskModel


class ProjectModel(ModelMixin, UserMixin):
    """项目（对外）

    对外的交付/结算单元，通常对应委托方（医药公司）的一单业务。
    状态机见 ``ProjectStatus``。
    """

    __tablename__: str = "market_project"
    __table_args__: dict[str, str] = {"comment": "项目表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="唯一编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="项目名")
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_company.id", ondelete="RESTRICT"), nullable=False, index=True, comment="委托方(医药公司)ID"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, comment="项目对外金额(与任务金额不挂钩)")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="项目状态")
    publisher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="发布人ID"
    )

    company: Mapped["CompanyModel"] = relationship()
    task_links: Mapped[list["ProjectTaskModel"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    @property
    def task_ids(self) -> list[int]:
        """归集的任务ID列表（需预加载 ``task_links``，否则异步环境会触发懒加载）。"""
        return [link.task_id for link in self.task_links]


class ProjectTaskModel(ModelMixin, UserMixin):
    """项目-任务归集（多对多关联表）"""

    __tablename__: str = "market_project_task"
    __table_args__ = (
        UniqueConstraint("project_id", "task_id", name="uq_market_project_task_project_task"),
        {"comment": "项目-任务归集表"},
    )

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_project.id", ondelete="CASCADE"), nullable=False, index=True, comment="项目ID"
    )
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task.id", ondelete="CASCADE"), nullable=False, index=True, comment="任务ID"
    )

    project: Mapped["ProjectModel"] = relationship(back_populates="task_links")
    task: Mapped["TaskModel"] = relationship(back_populates="project_links")


__all__ = ["ProjectModel", "ProjectTaskModel"]
