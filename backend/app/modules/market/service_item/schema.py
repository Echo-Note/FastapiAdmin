from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.modules.market.company.schema import CompanyOutSchema


class ServiceItemOutSchema(BaseSchema, UserBySchema):
    """对外服务项目价目响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="唯一编码")
    service_no: int = Field(description="服务项目号(1-37)")
    name: str = Field(description="服务项目名(如 等级医院用药数据收集)")
    service_type: str = Field(description="对外两级-类型(如 用药数据收集服务)")
    service_item: str = Field(description="对外两级-项目(如 等级医院用药数据收集)")
    unit: str = Field(description="计费单位(如 元/家/次)")
    price: float = Field(description="对外单价")
    company_id: int | None = Field(default=None, description="委托方(医药公司)ID")
    company: CompanyOutSchema | None = Field(default=None, description="委托方(医药公司)")
    task_type_ids: list[int] = Field(default_factory=list, description="映射的对内任务类型ID列表")


class ServiceItemCreateSchema(BaseModel):
    """创建对外服务项目价目"""

    code: str = Field(min_length=1, max_length=64, description="唯一编码")
    service_no: int = Field(ge=1, le=32767, description="服务项目号(1-37 为内置序号，新增可延续)")
    name: str = Field(min_length=1, max_length=128, description="服务项目名")
    service_type: str = Field(min_length=1, max_length=64, description="对外两级-类型")
    service_item: str = Field(min_length=1, max_length=64, description="对外两级-项目")
    unit: str = Field(min_length=1, max_length=32, description="计费单位")
    price: float = Field(ge=0, description="对外单价")
    company_id: int | None = Field(default=None, gt=0, description="委托方(医药公司)ID")
    task_type_ids: list[int] = Field(default_factory=list, description="映射的对内任务类型ID列表(可为空)")


class ServiceItemUpdateSchema(BaseModel):
    """更新对外服务项目价目"""

    code: str | None = Field(default=None, min_length=1, max_length=64, description="唯一编码")
    service_no: int | None = Field(default=None, ge=1, le=32767, description="服务项目号(1-37 为内置序号，新增可延续)")
    name: str | None = Field(default=None, min_length=1, max_length=128, description="服务项目名")
    service_type: str | None = Field(default=None, min_length=1, max_length=64, description="对外两级-类型")
    service_item: str | None = Field(default=None, min_length=1, max_length=64, description="对外两级-项目")
    unit: str | None = Field(default=None, min_length=1, max_length=32, description="计费单位")
    price: float | None = Field(default=None, ge=0, description="对外单价")
    company_id: int | None = Field(default=None, gt=0, description="委托方(医药公司)ID")
    task_type_ids: list[int] | None = Field(default=None, description="映射的对内任务类型ID列表(缺省不修改)")


class ServiceItemQueryParam(BaseQueryParam, UserByQueryParam):
    """对外服务项目价目查询参数"""

    code: str | None = Field(default=None, description="唯一编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="服务项目名", json_schema_extra={"q": "like"})
    service_type: str | None = Field(default=None, description="对外两级-类型", json_schema_extra={"q": "eq"})
    company_id: int | None = Field(default=None, description="委托方(医药公司)ID", json_schema_extra={"q": "eq"})
