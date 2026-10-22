from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateTimeStr
from app.modules.market.company.schema import CompanyOutSchema


class TaskTypeOutSchema(BaseSchema, UserBySchema):
    """任务类型模板响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="唯一编码(如 hospital_manage)")
    name: str = Field(description="任务类型名")
    service_type: str = Field(description="结算单三级-类型")
    service_item: str = Field(description="结算单三级-项目")
    service_task: str = Field(description="结算单三级-任务")
    unit: str = Field(description="计价单位(家/月、份、次)")
    default_price: float = Field(description="默认单价")
    exec_standard: str | None = Field(default=None, description="执行标准")
    required: bool = Field(default=False, description="是否必选")
    form_schema: list[dict[str, Any]] = Field(default_factory=list, description="采集字段 JSON Schema")


class TaskTypeCreateSchema(BaseModel):
    """创建任务类型模板"""

    code: str = Field(min_length=1, max_length=64, description="唯一编码(如 hospital_manage)")
    name: str = Field(min_length=1, max_length=128, description="任务类型名")
    service_type: str = Field(min_length=1, max_length=64, description="结算单三级-类型")
    service_item: str = Field(min_length=1, max_length=64, description="结算单三级-项目")
    service_task: str = Field(min_length=1, max_length=64, description="结算单三级-任务")
    unit: str = Field(min_length=1, max_length=32, description="计价单位")
    default_price: float = Field(ge=0, description="默认单价")
    exec_standard: str | None = Field(default=None, description="执行标准")
    required: bool = Field(default=False, description="是否必选")
    form_schema: list[dict[str, Any]] = Field(default_factory=list, description="采集字段 JSON Schema")


class TaskTypeUpdateSchema(BaseModel):
    """更新任务类型模板"""

    code: str | None = Field(default=None, min_length=1, max_length=64, description="唯一编码")
    name: str | None = Field(default=None, min_length=1, max_length=128, description="任务类型名")
    service_type: str | None = Field(default=None, min_length=1, max_length=64, description="结算单三级-类型")
    service_item: str | None = Field(default=None, min_length=1, max_length=64, description="结算单三级-项目")
    service_task: str | None = Field(default=None, min_length=1, max_length=64, description="结算单三级-任务")
    unit: str | None = Field(default=None, min_length=1, max_length=32, description="计价单位")
    default_price: float | None = Field(default=None, ge=0, description="默认单价")
    exec_standard: str | None = Field(default=None, description="执行标准")
    required: bool | None = Field(default=None, description="是否必选")
    form_schema: list[dict[str, Any]] | None = Field(default=None, description="采集字段 JSON Schema")


class TaskTypeQueryParam(BaseQueryParam, UserByQueryParam):
    """任务类型模板查询参数"""

    code: str | None = Field(default=None, description="唯一编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="任务类型名", json_schema_extra={"q": "like"})


class TaskOutSchema(BaseSchema, UserBySchema):
    """任务响应模型"""

    model_config = ConfigDict(from_attributes=True)

    task_no: str = Field(description="任务号")
    task_type_id: int = Field(description="任务类型模板ID")
    task_type: TaskTypeOutSchema | None = Field(default=None, description="任务类型模板")
    company_id: int = Field(description="委托医药公司ID")
    company: CompanyOutSchema | None = Field(default=None, description="委托医药公司")
    period: str = Field(description="周期(如 2026-10)")
    unit_price: float = Field(description="本期单价")
    exec_qty: int = Field(description="执行数量")
    status: str = Field(description="任务状态")
    publisher_id: int | None = Field(default=None, description="发布人ID")
    published_at: DateTimeStr | None = Field(default=None, description="发布时间")
    deadline_at: DateTimeStr | None = Field(default=None, description="截止时间")


class TaskCreateSchema(BaseModel):
    """创建任务"""

    task_no: str = Field(min_length=1, max_length=32, description="任务号(对应附件 1-4、5-17…)")
    task_type_id: int = Field(gt=0, description="任务类型模板ID")
    company_id: int = Field(gt=0, description="委托医药公司ID")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")
    unit_price: float | None = Field(default=None, ge=0, description="本期单价(缺省取模板默认)")
    exec_qty: int = Field(gt=0, description="执行数量")
    deadline_at: DateTimeStr | None = Field(default=None, description="截止时间")


class TaskUpdateSchema(BaseModel):
    """更新任务"""

    task_no: str | None = Field(default=None, min_length=1, max_length=32, description="任务号")
    period: str | None = Field(default=None, min_length=1, max_length=16, description="周期")
    unit_price: float | None = Field(default=None, ge=0, description="本期单价")
    exec_qty: int | None = Field(default=None, gt=0, description="执行数量")
    deadline_at: DateTimeStr | None = Field(default=None, description="截止时间")


class TaskPublishSchema(BaseModel):
    """发布任务"""

    deadline_at: DateTimeStr | None = Field(default=None, description="截止时间(缺省不修改)")


class TaskQueryParam(BaseQueryParam, UserByQueryParam):
    """任务查询参数"""

    task_no: str | None = Field(default=None, description="任务号", json_schema_extra={"q": "like"})
    task_type_id: int | None = Field(default=None, description="任务类型模板ID", json_schema_extra={"q": "eq"})
    company_id: int | None = Field(default=None, description="委托医药公司ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="任务状态", json_schema_extra={"q": "eq"})
