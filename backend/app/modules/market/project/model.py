"""项目管理（对外）与医药公司主数据、项目-二级模板关联、月度报告的数据模型。

本模块是后台「项目管理」模块的后端支撑，收编三类实体：
- 医药公司主数据（委托方/甲方）：``CompanyModel``
- 项目（对外的交付/结算单元）：``ProjectModel``
- 项目-二级模板关联（多对多）：``ProjectTemplateModel``
- 月度报告（按项目×二级任务按月聚合）：``ReportModel``

项目发布时按关联的二级模板批量生成任务实例（``market_task``），
二级模板实体 ``TaskTemplateModel`` 定义于 ``..task.model``（任务管理模块），
此处仅以字符串引用，避免模块间强耦合导入。
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import JSONType, ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.task.model import TaskTemplateModel


class CompanyModel(ModelMixin, UserMixin):
    """医药公司主数据（委托方/甲方）

    项目发布方（医药公司），项目金额与任务的归集口径以该公司为对外结算对象。
    """

    __tablename__: str = "market_company"
    __table_args__: dict[str, str] = {"comment": "医药公司主数据表"}

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True, comment="公司名称")
    code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, comment="公司编码")
    credit_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="统一社会信用代码")
    contact: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="公司地址")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启用 1:停用)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class ProjectModel(ModelMixin, UserMixin):
    """项目（对外）

    对外的交付/结算单元，通常对应委托方（医药公司）的一单业务。
    状态机见 ``ProjectStatus``：草稿 → 进行中 → 已完成 → 已关闭。
    """

    __tablename__: str = "market_project"
    __table_args__: dict[str, str] = {"comment": "项目表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="项目编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="项目名(如药品名)")
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_company.id", ondelete="RESTRICT"), nullable=False, index=True, comment="委托方(医药公司)ID"
    )
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="项目周期(如 2026 全年)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="项目状态")
    publisher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="发布人ID"
    )

    company: Mapped["CompanyModel"] = relationship()
    template_links: Mapped[list["ProjectTemplateModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def template_ids(self) -> list[int]:
        """关联的二级模板ID列表（需预加载 ``template_links``，否则异步环境会触发懒加载）。"""
        return [link.template_id for link in self.template_links]


class ProjectTemplateModel(ModelMixin, UserMixin):
    """项目-二级模板关联（多对多关联表）"""

    __tablename__: str = "market_project_template"
    __table_args__ = (
        UniqueConstraint("project_id", "template_id", name="uq_market_project_template_project_template"),
        {"comment": "项目-二级模板关联表"},
    )

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_project.id", ondelete="CASCADE"), nullable=False, index=True, comment="项目ID"
    )
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task_template.id", ondelete="CASCADE"), nullable=False, index=True, comment="二级模板ID"
    )

    project: Mapped["ProjectModel"] = relationship(back_populates="template_links")
    template: Mapped["TaskTemplateModel"] = relationship()


class ReportModel(ModelMixin, UserMixin):
    """月度报告（提交甲方）

    按「项目 × 二级任务」按月聚合当月审核通过的成果，生成报告提交给项目发布方。
    ``template_id`` 为空表示全项目汇总报告。
    """

    __tablename__: str = "market_report"
    __table_args__: dict[str, str] = {"comment": "月度报告表"}

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_project.id", ondelete="RESTRICT"), nullable=False, index=True, comment="项目ID"
    )
    template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("market_task_template.id", ondelete="SET NULL"), nullable=True, index=True, comment="二级模板ID(可空:全项目汇总)"
    )
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="报告月份(如 2026-03)")
    summary: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="当月完成量/金额汇总")
    attachment: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="报告附件路径")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="报告状态")

    project: Mapped["ProjectModel"] = relationship()
    template: Mapped["TaskTemplateModel"] = relationship()


__all__ = ["CompanyModel", "ProjectModel", "ProjectTemplateModel", "ReportModel"]
