from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import JSONType, ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.assignment.model import AssignmentModel
    from app.modules.market.institution.model import InstitutionModel


class SubmissionModel(ModelMixin, UserMixin):
    """成果提交

    C 端用户针对一个对象（一家医院/药店/商业公司）提交的一份采集表/问卷。
    支持草稿暂存；驳回后可修改重新提交（version +1，保留历史版本）。
    预留 AI 智能体检查字段（一期为空实现）。
    """

    __tablename__: str = "market_submission"
    __table_args__: dict[str, str] = {"comment": "成果提交表"}

    assignment_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_assignment.id", ondelete="RESTRICT"), nullable=False, index=True, comment="归属任务实例ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False, index=True, comment="提交人ID")
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_institution.id", ondelete="RESTRICT"), nullable=False, index=True, comment="对象机构ID")
    region: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="区域")
    archive_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="开发档案编号")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="提交月份(用于周期性任务单月一次约束)")
    form_data: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="采集表单数据(异构)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="成果状态")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="版本(驳回重提+1)")
    reviewer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="审核人ID")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审核时间")
    ai_check_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="AI检查状态(预留)")
    ai_check_result: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True, comment="AI检查结果(预留)")

    assignment: Mapped["AssignmentModel"] = relationship(back_populates="submissions")
    institution: Mapped["InstitutionModel"] = relationship()
