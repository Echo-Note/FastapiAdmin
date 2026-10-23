from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import JSONType, ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.company.model import CompanyModel
    from app.modules.market.service_item.model import ServiceItemModel
    from app.modules.market.task.model import TaskTypeModel


class ReportModel(ModelMixin, UserMixin):
    """报告

    按**服务项目/任务类型 × 周期**生成，每个服务项目一份独立报告（对应素材中的分析报告 pptx）。
    一期导出打包（人工/邮件提交），二期平台在线交付。
    """

    __tablename__: str = "market_report"
    __table_args__: dict[str, str] = {"comment": "报告表"}

    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_company.id", ondelete="RESTRICT"), nullable=False, index=True, comment="医药公司ID")
    service_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("market_service_item.id", ondelete="SET NULL"), nullable=True, index=True, comment="对外服务项目ID(报告针对的服务项目，可空)")
    task_type_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("market_task_type.id", ondelete="SET NULL"), nullable=True, index=True, comment="对内任务类型ID(报告针对的任务类型，可空)")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10)")
    summary: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="各任务类型完成量/金额汇总(JSON)")
    attachment: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="明细附件路径")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="报告状态")

    company: Mapped["CompanyModel"] = relationship()
    service_item: Mapped["ServiceItemModel"] = relationship()
    task_type: Mapped["TaskTypeModel"] = relationship()
