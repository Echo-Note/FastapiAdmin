from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class CompanyOutSchema(BaseSchema, UserBySchema):
    """医药公司响应模型"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="公司名称")
    code: str | None = Field(default=None, description="公司编码")
    credit_code: str | None = Field(default=None, description="统一社会信用代码")
    contact: str | None = Field(default=None, description="联系人")
    contact_phone: str | None = Field(default=None, description="联系电话")
    address: str | None = Field(default=None, description="公司地址")
    status: int = Field(default=0, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class CompanyCreateSchema(BaseModel):
    """创建医药公司"""

    name: str = Field(min_length=1, max_length=128, description="公司名称")
    code: str | None = Field(default=None, max_length=64, description="公司编码")
    credit_code: str | None = Field(default=None, max_length=32, description="统一社会信用代码")
    contact: str | None = Field(default=None, max_length=32, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=20, description="联系电话")
    address: str | None = Field(default=None, max_length=255, description="公司地址")
    status: int = Field(default=0, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class CompanyUpdateSchema(BaseModel):
    """更新医药公司"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="公司名称")
    code: str | None = Field(default=None, max_length=64, description="公司编码")
    credit_code: str | None = Field(default=None, max_length=32, description="统一社会信用代码")
    contact: str | None = Field(default=None, max_length=32, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=20, description="联系电话")
    address: str | None = Field(default=None, max_length=255, description="公司地址")
    status: int | None = Field(default=None, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class CompanyQueryParam(BaseQueryParam, UserByQueryParam):
    """医药公司查询参数"""

    name: str | None = Field(default=None, description="公司名称", json_schema_extra={"q": "like"})
    credit_code: str | None = Field(default=None, description="统一社会信用代码", json_schema_extra={"q": "eq"})
    status: int | None = Field(default=None, description="状态", json_schema_extra={"q": "eq"})
