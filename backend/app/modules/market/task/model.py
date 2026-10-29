"""任务管理域数据模型。

任务三级层级：一级分类（TaskCategoryModel）→ 二级模板（TaskTemplateModel）→
三级任务（TaskItemModel）。模板承载通用采集字段（TaskConfig JSON），任务承载
专属采集字段（TaskItemConfig JSON），任务实例（TaskModel）引用模板执行，
执行过程产生分派（AssignmentModel）与成果提交（SubmissionModel）。

状态机取值见 ``app.modules.market.enums``。
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import JSONType, ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.institution.model import InstitutionModel


class TaskCategoryModel(ModelMixin, UserMixin):
    """一级任务分类（如 机构管理 / 调研 / 宣传 / 会议）。"""

    __tablename__: str = "market_task_category"
    __table_args__: dict[str, str] = {"comment": "一级任务分类表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="分类编号")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="分类名")
    sort: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="排序(越小越靠前)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="分类描述")

    templates: Mapped[list["TaskTemplateModel"]] = relationship(back_populates="category")


class TaskTemplateModel(ModelMixin, UserMixin):
    """二级任务模板（TO C 类型，承载 TaskConfig 通用采集字段设计）。"""

    __tablename__: str = "market_task_template"
    __table_args__: dict[str, str] = {"comment": "二级任务模板表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="模板编号")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="模板名")
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task_category.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属一级分类ID"
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="任务设计配置(TaskConfig 结构)")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")

    category: Mapped["TaskCategoryModel"] = relationship(back_populates="templates")
    items: Mapped[list["TaskItemModel"]] = relationship(back_populates="template")
    tasks: Mapped[list["TaskModel"]] = relationship(back_populates="template")


class TaskItemModel(ModelMixin, UserMixin):
    """三级任务（TO C 任务，承载 TaskItemConfig 专属采集字段设计）。"""

    __tablename__: str = "market_task_item"
    __table_args__: dict[str, str] = {"comment": "三级任务表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="任务编号")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="任务名")
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task_template.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属二级模板ID"
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="任务设计配置(TaskItemConfig 结构)")
    sort: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="排序(越小越靠前)")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")

    template: Mapped["TaskTemplateModel"] = relationship(back_populates="items")


class TaskModel(ModelMixin, UserMixin):
    """任务实例（运营发布、C 端执行的最小执行单元）。"""

    __tablename__: str = "market_task"
    __table_args__ = (
        # template_id 外键索引显式命名：默认 ix_market_task_template_id 会与
        # market_task_template.id（ModelMixin 主键 index=True）生成的同名索引冲突
        Index("ix_market_task_template_fk", "template_id"),
        {"comment": "任务实例表"},
    )

    task_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="任务编号(唯一，如 TK-001)")
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_project.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属项目ID"
    )
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task_template.id", ondelete="RESTRICT"), nullable=False, comment="所属二级模板ID"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True, comment="C端显示名(如 一心坦-等级医院管理)")
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="截止日期(继承项目截止日期)")
    assign_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="direct", index=True, comment="分配方式(direct 定向分派/open 公开大厅)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="任务状态")
    publisher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="发布人ID"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="发布时间")

    template: Mapped["TaskTemplateModel"] = relationship(back_populates="tasks")
    assignments: Mapped[list["AssignmentModel"]] = relationship(back_populates="task")


class AssignmentModel(ModelMixin, UserMixin):
    """任务分配/接收（一个任务对一个用户的一次执行委派）。"""

    __tablename__: str = "market_assignment"
    __table_args__: dict[str, str] = {"comment": "任务分配/接收表"}

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_task.id", ondelete="RESTRICT"), nullable=False, index=True, comment="任务ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False, index=True, comment="执行用户ID"
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="assigned", index=True, comment="来源(assigned 运营分派/claimed 大厅接单)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True, comment="分配状态")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="接收时间")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="提交时间")

    task: Mapped["TaskModel"] = relationship(back_populates="assignments")
    submissions: Mapped[list["SubmissionModel"]] = relationship(back_populates="assignment")


class SubmissionModel(ModelMixin, UserMixin):
    """成果提交（一次提交 = 一个对象 × 一份采集表单，驳回可修改重提版本 +1）。"""

    __tablename__: str = "market_submission"
    __table_args__: dict[str, str] = {"comment": "成果提交表"}

    assignment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_assignment.id", ondelete="RESTRICT"), nullable=False, index=True, comment="分配ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False, index=True, comment="提交用户ID"
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, default="institution", index=True, comment="采集对象类型(institution/staff/patient/meeting)")
    institution_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("market_institution.id", ondelete="RESTRICT"), nullable=True, index=True, comment="机构ID(对象为机构时)"
    )
    subject_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="对象名称(非机构对象时)")
    region: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="所在区域")
    archive_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="档案编号")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="提交月份(如 2026-03)")
    form_data: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, comment="采集表单数据")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="成果状态")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="版本号(驳回重提 +1)")
    reviewer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="审核人ID"
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审核时间")
    ai_check_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="AI 预检状态")
    ai_check_result: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True, comment="AI 预检结果")

    assignment: Mapped["AssignmentModel"] = relationship(back_populates="submissions")
    institution: Mapped["InstitutionModel"] = relationship()


__all__ = [
    "TaskCategoryModel",
    "TaskTemplateModel",
    "TaskItemModel",
    "TaskModel",
    "AssignmentModel",
    "SubmissionModel",
]
