"""项目（对外）与项目-任务归集的 Schema 定义。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.modules.market.company.schema import CompanyOutSchema


class ProjectOutSchema(BaseSchema, UserBySchema):
    """项目响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="唯一编码")
    name: str = Field(description="项目名")
    company_id: int = Field(description="委托方(医药公司)ID")
    company: CompanyOutSchema | None = Field(default=None, description="委托方(医药公司)")
    amount: float = Field(description="项目对外金额(与任务金额不挂钩)")
    period: str = Field(description="周期(如 2026-10)")
    status: str = Field(description="项目状态")
    publisher_id: int | None = Field(default=None, description="发布人ID")
    task_ids: list[int] = Field(default_factory=list, description="归集的任务ID列表")


class ProjectCreateSchema(BaseModel):
    """创建项目"""

    code: str = Field(min_length=1, max_length=64, description="唯一编码")
    name: str = Field(min_length=1, max_length=128, description="项目名")
    company_id: int = Field(gt=0, description="委托方(医药公司)ID")
    amount: float = Field(default=0, ge=0, description="项目对外金额(与任务金额不挂钩)")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")
    task_ids: list[int] = Field(default_factory=list, description="归集的任务ID列表(可为空)")


class ProjectUpdateSchema(BaseModel):
    """更新项目"""

    code: str | None = Field(default=None, min_length=1, max_length=64, description="唯一编码")
    name: str | None = Field(default=None, min_length=1, max_length=128, description="项目名")
    company_id: int | None = Field(default=None, gt=0, description="委托方(医药公司)ID")
    amount: float | None = Field(default=None, ge=0, description="项目对外金额(与任务金额不挂钩)")
    period: str | None = Field(default=None, min_length=1, max_length=16, description="周期")
    task_ids: list[int] | None = Field(default=None, description="归集的任务ID列表(缺省不修改)")


class ProjectQueryParam(BaseQueryParam, UserByQueryParam):
    """项目查询参数"""

    code: str | None = Field(default=None, description="唯一编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="项目名", json_schema_extra={"q": "like"})
    company_id: int | None = Field(default=None, description="委托方(医药公司)ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="项目状态", json_schema_extra={"q": "eq"})


class ProjectTaskCreateSchema(BaseModel):
    """项目-任务归集记录（内部 CRUD 使用）"""

    project_id: int = Field(gt=0, description="项目ID")
    task_id: int = Field(gt=0, description="任务ID")


class ProjectAddTaskSchema(BaseModel):
    """把任务归集到项目（对外入参）"""

    task_id: int = Field(gt=0, description="任务ID")


class ProjectStatusUpdateSchema(BaseModel):
    """项目状态流转（完成/关闭）"""

    status: Literal["IN_PROGRESS", "COMPLETED", "CLOSED"] = Field(description="目标状态")
