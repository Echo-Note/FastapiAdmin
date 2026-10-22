from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import JSONType, ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.company.model import CompanyModel


class ReportModel(ModelMixin, UserMixin):
    """报告

    归集后按医药公司维度打包生成交付物，汇总各任务类型完成量 + 结算金额 + 明细附件。
    一期导出打包（人工/邮件提交），二期平台在线交付。
    """

    __tablename__: str = "market_report"
    __table_args__: dict[str, str] = {"comment": "报告表"}

    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_company.id", ondelete="RESTRICT"), nullable=False, index=True, comment="医药公司ID")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10)")
    summary: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="各任务类型完成量/金额汇总(JSON)")
    attachment: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="明细附件路径")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="报告状态")

    company: Mapped["CompanyModel"] = relationship()
