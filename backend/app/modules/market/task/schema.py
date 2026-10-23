from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateTimeStr
from app.modules.market.template.schema import TemplateOutSchema


class TaskTypeOutSchema(BaseSchema, UserBySchema):
    """任务类型（对内计价项）响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="唯一编码(如 hospital_delivery)")
    name: str = Field(description="任务类型名")
    task_no: int = Field(description="任务号(1-44)")
    template_id: int = Field(description="所属采集模板ID")
    template: TemplateOutSchema | None = Field(default=None, description="所属采集模板(含 form_schema)")
    service_type: str = Field(description="结算单三级-类型")
    service_item: str = Field(description="结算单三级-项目")
    service_task: str = Field(description="结算单三级-任务")
    unit: str = Field(description="计价单位(家/月、份、次)")
    default_price: float = Field(description="默认单价")
    default_kind: str = Field(default="periodic", description="默认任务分类(periodic 周期性/quota 定额)")
    exec_standard: str | None = Field(default=None, description="执行标准")
    required: bool = Field(default=False, description="是否必选")
    min_qty: int | None = Field(default=None, description="必选最低执行数量")
    max_per_period: int | None = Field(default=None, description="周期内执行次数上限")
    dedup_rule: str | None = Field(default=None, description="去重约束")


class TaskTypeCreateSchema(BaseModel):
    """创建任务类型（计价项）"""

    code: str = Field(min_length=1, max_length=64, description="唯一编码(如 hospital_delivery)")
    name: str = Field(min_length=1, max_length=128, description="任务类型名")
    task_no: int = Field(ge=1, le=32767, description="任务号(1-44 为内置计价项序号，新增可延续)")
    template_id: int = Field(gt=0, description="所属采集模板ID")
    service_type: str = Field(min_length=1, max_length=64, description="结算单三级-类型")
    service_item: str = Field(min_length=1, max_length=64, description="结算单三级-项目")
    service_task: str = Field(min_length=1, max_length=64, description="结算单三级-任务")
    unit: str = Field(min_length=1, max_length=32, description="计价单位")
    default_price: float = Field(ge=0, description="默认单价")
    default_kind: Literal["periodic", "quota"] = Field(default="periodic", description="默认任务分类(periodic 周期性/quota 定额)")
    exec_standard: str | None = Field(default=None, description="执行标准")
    required: bool = Field(default=False, description="是否必选")
    min_qty: int | None = Field(default=None, ge=0, description="必选最低执行数量")
    max_per_period: int | None = Field(default=None, ge=0, description="周期内执行次数上限")
    dedup_rule: str | None = Field(default=None, max_length=128, description="去重约束")


class TaskTypeUpdateSchema(BaseModel):
    """更新任务类型（计价项）"""

    code: str | None = Field(default=None, min_length=1, max_length=64, description="唯一编码")
    name: str | None = Field(default=None, min_length=1, max_length=128, description="任务类型名")
    task_no: int | None = Field(default=None, ge=1, le=32767, description="任务号(1-44 为内置序号，新增可延续)")
    template_id: int | None = Field(default=None, gt=0, description="所属采集模板ID")
    service_type: str | None = Field(default=None, min_length=1, max_length=64, description="结算单三级-类型")
    service_item: str | None = Field(default=None, min_length=1, max_length=64, description="结算单三级-项目")
    service_task: str | None = Field(default=None, min_length=1, max_length=64, description="结算单三级-任务")
    unit: str | None = Field(default=None, min_length=1, max_length=32, description="计价单位")
    default_price: float | None = Field(default=None, ge=0, description="默认单价")
    default_kind: Literal["periodic", "quota"] | None = Field(default=None, description="默认任务分类(periodic 周期性/quota 定额)")
    exec_standard: str | None = Field(default=None, description="执行标准")
    required: bool | None = Field(default=None, description="是否必选")
    min_qty: int | None = Field(default=None, ge=0, description="必选最低执行数量")
    max_per_period: int | None = Field(default=None, ge=0, description="周期内执行次数上限")
    dedup_rule: str | None = Field(default=None, max_length=128, description="去重约束")


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
    task_kind: str = Field(description="任务分类(periodic 周期性/quota 定额)")
    period: str = Field(description="周期(如 2026-10)")
    exec_time_start: DateTimeStr | None = Field(default=None, description="定额任务限定时间-开始")
    exec_time_end: DateTimeStr | None = Field(default=None, description="定额任务限定时间-结束")
    unit_price: float = Field(description="本期单价")
    exec_qty: int = Field(description="执行数量(定额任务为总份数限量)")
    assign_mode: str = Field(description="分配方式(direct 定向分派/open 公开大厅)")
    claimed_count: int = Field(default=0, description="已接单数(公开大厅，动态计算)")
    status: str = Field(description="任务状态")
    completed_at: DateTimeStr | None = Field(default=None, description="完成判定时间")
    publisher_id: int | None = Field(default=None, description="发布人ID")
    published_at: DateTimeStr | None = Field(default=None, description="发布时间")
    project_ids: list[int] = Field(default_factory=list, description="归集到的项目ID列表(多对多)")


class TaskCreateSchema(BaseModel):
    """创建任务"""

    task_no: str = Field(min_length=1, max_length=32, description="任务号(对应附件 1-4、5-17…)")
    task_type_id: int = Field(gt=0, description="任务类型模板ID")
    task_kind: Literal["periodic", "quota"] | None = Field(default=None, description="任务分类(缺省取模板默认)")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")
    exec_time_start: DateTimeStr | None = Field(default=None, description="定额任务限定时间-开始")
    exec_time_end: DateTimeStr | None = Field(default=None, description="定额任务限定时间-结束")
    unit_price: float | None = Field(default=None, ge=0, description="本期单价(缺省取模板默认)")
    exec_qty: int = Field(gt=0, description="执行数量(定额任务为总份数限量)")
    assign_mode: Literal["direct", "open"] = Field(default="direct", description="分配方式(direct 定向分派/open 公开大厅)")
    project_ids: list[int] = Field(default_factory=list, description="归集到的项目ID列表(可为空)")


class TaskUpdateSchema(BaseModel):
    """更新任务"""

    task_no: str | None = Field(default=None, min_length=1, max_length=32, description="任务号")
    task_kind: Literal["periodic", "quota"] | None = Field(default=None, description="任务分类")
    period: str | None = Field(default=None, min_length=1, max_length=16, description="周期")
    exec_time_start: DateTimeStr | None = Field(default=None, description="定额任务限定时间-开始")
    exec_time_end: DateTimeStr | None = Field(default=None, description="定额任务限定时间-结束")
    unit_price: float | None = Field(default=None, ge=0, description="本期单价")
    exec_qty: int | None = Field(default=None, gt=0, description="执行数量")
    assign_mode: Literal["direct", "open"] | None = Field(default=None, description="分配方式(direct 定向分派/open 公开大厅)")
    project_ids: list[int] | None = Field(default=None, description="归集到的项目ID列表(缺省不修改)")


class TaskQueryParam(BaseQueryParam, UserByQueryParam):
    """任务查询参数"""

    task_no: str | None = Field(default=None, description="任务号", json_schema_extra={"q": "like"})
    task_type_id: int | None = Field(default=None, description="任务类型模板ID", json_schema_extra={"q": "eq"})
    task_kind: str | None = Field(default=None, description="任务分类", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    assign_mode: str | None = Field(default=None, description="分配方式", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="任务状态", json_schema_extra={"q": "eq"})
