from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.assignment.model import AssignmentModel
    from app.modules.market.project.model import ProjectTaskModel
    from app.modules.market.template.model import TemplateModel


class TaskTypeModel(ModelMixin, UserMixin):
    """任务类型（= 对内计价项）

    对应结算单中的一行（任务号 1–44）。它绑定一个采集模板（``template_id``），
    用三级 ``service_type / service_item / service_task`` 表达服务归属，是**对内计价项**。
    采集表单结构（form_schema）挂在 ``market_template`` 层，不再挂在每个计价项上。
    """

    __tablename__: str = "market_task_type"
    __table_args__: dict[str, str] = {"comment": "任务类型(计价项)表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="唯一编码(如 hospital_delivery)")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="任务类型名")
    task_no: Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True, index=True, comment="任务号(1-44，对应结算单任务序号)")
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_template.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属采集模板ID")
    service_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="结算单三级-类型(如 医院管理)")
    service_item: Mapped[str] = mapped_column(String(64), nullable=False, comment="结算单三级-项目(如 等级医院)")
    service_task: Mapped[str] = mapped_column(String(64), nullable=False, comment="结算单三级-任务(如 等级医院管理)")
    unit: Mapped[str] = mapped_column(String(32), nullable=False, comment="计价单位(家/月、份、次)")
    default_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="默认单价")
    exec_standard: Mapped[str | None] = mapped_column(Text, nullable=True, comment="执行标准")
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否必选")
    min_qty: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="必选最低执行数量(如 1家起的1)")
    max_per_period: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="周期内执行次数上限(如 每月不超过20次)")
    dedup_rule: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="去重约束(如 单个医务人员单月单项目只能调研一次)")
    default_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="periodic", comment="默认任务分类(periodic 周期性/quota 定额)")

    template: Mapped["TemplateModel"] = relationship(back_populates="task_types")
    tasks: Mapped[list["TaskModel"]] = relationship(back_populates="task_type")


class TaskModel(ModelMixin, UserMixin):
    """任务（对内）

    运营端创建并发布，分派给 C 端用户执行，可归集到多个项目。状态机见 TaskStatus。
    """

    __tablename__: str = "market_task"
    __table_args__: dict[str, str] = {"comment": "任务表"}

    task_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="运行期任务流水号(唯一，如 TK202610-001)")
    task_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_task_type.id", ondelete="RESTRICT"), nullable=False, index=True, comment="任务类型/计价项ID")
    task_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="periodic", index=True, comment="任务分类(periodic 周期性/quota 定额)")
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="周期(如 2026-10，默认自然月)")
    exec_time_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="定额任务限定时间-开始(周期任务可空)")
    exec_time_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="定额任务限定时间-结束(周期任务可空)")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="本期单价(可覆盖模板默认)；任务金额仅对内")
    exec_qty: Mapped[int] = mapped_column(Integer, nullable=False, comment="执行数量(定额任务为总份数限量；周期任务不限)")
    assign_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="direct", index=True, comment="分配方式(direct 定向分派/open 公开大厅)")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True, comment="任务状态")
    completed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, comment="完成判定人ID(运营)")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="完成判定时间")
    publisher_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="发布人ID")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="发布时间")

    task_type: Mapped["TaskTypeModel"] = relationship(back_populates="tasks")
    assignments: Mapped[list["AssignmentModel"]] = relationship(back_populates="task")
    project_links: Mapped[list["ProjectTaskModel"]] = relationship(back_populates="task")

    @property
    def project_ids(self) -> list[int]:
        """归集到的项目ID列表（需预加载 ``project_links``，否则异步环境会触发懒加载）。"""
        return [link.project_id for link in self.project_links]
