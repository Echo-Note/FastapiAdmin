from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.submission.model import SubmissionModel
    from app.modules.market.task.model import TaskModel


class AssignmentModel(ModelMixin, UserMixin):
    """任务分派/接收

    任务分派给某个 C 端用户后形成的一对一执行关系。状态机见 AssignmentStatus。
    """

    __tablename__: str = "market_assignment"
    __table_args__: dict[str, str] = {"comment": "任务分派/接收表"}

    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_task.id", ondelete="RESTRICT"), nullable=False, index=True, comment="任务ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False, index=True, comment="C端用户ID")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="assigned", index=True, comment="来源(assigned 运营分派/claimed 大厅接单)")
    assign_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, comment="本单接收金额(=单价×数量)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True, comment="分派状态")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="接收时间")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="首次提交时间")

    task: Mapped["TaskModel"] = relationship(back_populates="assignments")
    submissions: Mapped[list["SubmissionModel"]] = relationship(back_populates="assignment")
