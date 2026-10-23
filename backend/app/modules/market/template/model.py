from typing import TYPE_CHECKING, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import JSONType, ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.task.model import TaskTypeModel


class TemplateModel(ModelMixin, UserMixin):
    """采集模板（form_schema 宿主）

    对应素材中一个**采集工作簿**（如「等级医院管理采集模板」），定义采集表单结构。
    与「任务类型（计价项）」是 1:N —— 一个模板下含多个计价项，共享同一套表单结构。
    ``form_schema`` 挂在本层（支持 section 分节 / table 多行子表），不再挂在每个计价项上。
    """

    __tablename__: str = "market_template"
    __table_args__: dict[str, str] = {"comment": "采集模板表"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="模板唯一编码(如 grade_hospital_manage)")
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="模板名(如 等级医院管理采集模板)")
    scope: Mapped[str] = mapped_column(String(16), nullable=False, comment="覆盖计价项任务号范围(如 5-17)")
    form_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False, comment="采集字段 JSON Schema(驱动动态表单)")

    task_types: Mapped[list["TaskTypeModel"]] = relationship(back_populates="template")
