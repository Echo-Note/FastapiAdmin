from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class InstitutionOutSchema(BaseSchema, UserBySchema):
    """机构响应模型"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="机构名称")
    type: str = Field(description="机构类型(等级医院/基层医疗/民营医疗/零售药店/商业公司)")
    level: str | None = Field(default=None, description="等级(如三甲/二级)")
    region: str | None = Field(default=None, description="所在区域")
    address: str | None = Field(default=None, description="详细地址")
    contact: str | None = Field(default=None, description="联系人")
    contact_phone: str | None = Field(default=None, description="联系电话")
    status: int = Field(default=0, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class InstitutionCreateSchema(BaseModel):
    """创建机构"""

    name: str = Field(min_length=1, max_length=128, description="机构名称")
    type: str = Field(min_length=1, max_length=32, description="机构类型")
    level: str | None = Field(default=None, max_length=32, description="等级(如三甲/二级)")
    region: str | None = Field(default=None, max_length=64, description="所在区域")
    address: str | None = Field(default=None, max_length=255, description="详细地址")
    contact: str | None = Field(default=None, max_length=32, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=20, description="联系电话")
    status: int = Field(default=0, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class InstitutionUpdateSchema(BaseModel):
    """更新机构"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="机构名称")
    type: str | None = Field(default=None, min_length=1, max_length=32, description="机构类型")
    level: str | None = Field(default=None, max_length=32, description="等级(如三甲/二级)")
    region: str | None = Field(default=None, max_length=64, description="所在区域")
    address: str | None = Field(default=None, max_length=255, description="详细地址")
    contact: str | None = Field(default=None, max_length=32, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=20, description="联系电话")
    status: int | None = Field(default=None, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class InstitutionQueryParam(BaseQueryParam, UserByQueryParam):
    """机构查询参数"""

    name: str | None = Field(default=None, description="机构名称", json_schema_extra={"q": "like"})
    type: str | None = Field(default=None, description="机构类型", json_schema_extra={"q": "eq"})
    region: str | None = Field(default=None, description="所在区域", json_schema_extra={"q": "eq"})
    status: int | None = Field(default=None, description="状态", json_schema_extra={"q": "eq"})
