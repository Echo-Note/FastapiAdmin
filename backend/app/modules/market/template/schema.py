
from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.modules.market.form_schema import FormSchemaField


class TemplateOutSchema(BaseSchema, UserBySchema):
    """采集模板响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="模板唯一编码(如 grade_hospital_manage)")
    name: str = Field(description="模板名(如 等级医院管理采集模板)")
    scope: str = Field(description="覆盖计价项任务号范围(如 5-17)")
    form_schema: list[FormSchemaField] = Field(default_factory=list, description="采集字段 Schema")


class TemplateCreateSchema(BaseModel):
    """创建采集模板"""

    code: str = Field(min_length=1, max_length=64, description="模板唯一编码(如 grade_hospital_manage)")
    name: str = Field(min_length=1, max_length=128, description="模板名(如 等级医院管理采集模板)")
    scope: str = Field(min_length=1, max_length=16, description="覆盖计价项任务号范围(如 5-17)")
    form_schema: list[FormSchemaField] = Field(default_factory=list, description="采集字段 Schema")


class TemplateUpdateSchema(BaseModel):
    """更新采集模板"""

    code: str | None = Field(default=None, min_length=1, max_length=64, description="模板唯一编码")
    name: str | None = Field(default=None, min_length=1, max_length=128, description="模板名")
    scope: str | None = Field(default=None, min_length=1, max_length=16, description="覆盖计价项任务号范围")
    form_schema: list[FormSchemaField] | None = Field(default=None, description="采集字段 Schema")


class TemplateQueryParam(BaseQueryParam, UserByQueryParam):
    """采集模板查询参数"""

    code: str | None = Field(default=None, description="模板唯一编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="模板名", json_schema_extra={"q": "like"})
