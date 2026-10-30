"""项目管理（对外）、医药公司主数据、项目-二级模板关联、月度报告的 Schema 定义。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateStr


class CompanyOutSchema(BaseSchema, UserBySchema):
    """医药公司响应模型"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="公司名称")
    code: str = Field(description="公司编号")
    credit_code: str | None = Field(default=None, description="统一社会信用代码")
    contact: str | None = Field(default=None, description="联系人")
    contact_phone: str | None = Field(default=None, description="联系电话")
    address: str | None = Field(default=None, description="公司地址")
    status: int = Field(default=0, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class CompanyCreateSchema(BaseModel):
    """创建医药公司"""

    name: str = Field(min_length=1, max_length=128, description="公司名称")
    credit_code: str | None = Field(default=None, max_length=32, description="统一社会信用代码")
    contact: str | None = Field(default=None, max_length=32, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=20, description="联系电话")
    address: str | None = Field(default=None, max_length=255, description="公司地址")
    status: int = Field(default=0, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class CompanyUpdateSchema(BaseModel):
    """更新医药公司"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="公司名称")
    credit_code: str | None = Field(default=None, max_length=32, description="统一社会信用代码")
    contact: str | None = Field(default=None, max_length=32, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=20, description="联系电话")
    address: str | None = Field(default=None, max_length=255, description="公司地址")
    status: int | None = Field(default=None, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, description="备注")


class CompanyQueryParam(BaseQueryParam, UserByQueryParam):
    """医药公司查询参数"""

    name: str | None = Field(default=None, description="公司名称", json_schema_extra={"q": "like"})
    code: str | None = Field(default=None, description="公司编号", json_schema_extra={"q": "like"})
    credit_code: str | None = Field(default=None, description="统一社会信用代码", json_schema_extra={"q": "eq"})
    status: int | None = Field(default=None, description="状态", json_schema_extra={"q": "eq"})


class ProjectOutSchema(BaseSchema, UserBySchema):
    """项目响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="项目编号")
    name: str = Field(description="项目名(如药品名)")
    company_id: int = Field(description="委托方(医药公司)ID")
    company: CompanyOutSchema | None = Field(default=None, description="委托方(医药公司)")
    period: DateStr = Field(description="项目截止日期(如 2026-12-31)")
    status: str = Field(description="项目状态")
    publisher_id: int | None = Field(default=None, description="发布人ID")
    item_ids: list[int] = Field(default_factory=list, description="关联的任务ID列表")
    template_ids: list[int] = Field(default_factory=list, description="关联的叶子模板ID列表(无任务时即模板)")


class ProjectCreateSchema(BaseModel):
    """创建项目"""

    name: str = Field(min_length=1, max_length=128, description="项目名(如药品名)")
    company_id: int = Field(gt=0, description="委托方(医药公司)ID")
    period: DateStr = Field(description="项目截止日期(如 2026-12-31)")
    item_ids: list[int] = Field(default_factory=list, description="关联的三级任务ID列表(可为空)")
    template_ids: list[int] = Field(default_factory=list, description="关联的叶子模板ID列表(可为空)")


class ProjectUpdateSchema(BaseModel):
    """更新项目"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="项目名(如药品名)")
    company_id: int | None = Field(default=None, gt=0, description="委托方(医药公司)ID")
    period: DateStr | None = Field(default=None, description="项目截止日期(如 2026-12-31)")
    item_ids: list[int] | None = Field(default=None, description="关联的三级任务ID列表(缺省不修改)")
    template_ids: list[int] | None = Field(default=None, description="关联的叶子模板ID列表(缺省不修改)")


class ProjectQueryParam(BaseQueryParam, UserByQueryParam):
    """项目查询参数"""

    code: str | None = Field(default=None, description="项目编号", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="项目名", json_schema_extra={"q": "like"})
    company_id: int | None = Field(default=None, description="委托方(医药公司)ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="项目周期", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="项目状态", json_schema_extra={"q": "eq"})


class ProjectStatusUpdateSchema(BaseModel):
    """项目状态流转（进行中/已完成/已关闭）"""

    status: Literal["IN_PROGRESS", "COMPLETED", "CLOSED"] = Field(description="目标状态")


class ProjectItemCreateSchema(BaseModel):
    """项目-任务单元关联记录（内部 CRUD 使用，item_id / template_id 恰好一个非空）"""

    project_id: int = Field(gt=0, description="项目ID")
    item_id: int | None = Field(default=None, gt=0, description="三级任务ID")
    template_id: int | None = Field(default=None, gt=0, description="叶子模板ID")


class ReportOutSchema(BaseSchema, UserBySchema):
    """月度报告响应模型"""

    model_config = ConfigDict(from_attributes=True)

    project_id: int = Field(description="项目ID")
    template_id: int | None = Field(default=None, description="二级模板ID(可空:全项目汇总)")
    period: str = Field(description="报告月份(如 2026-03)")
    summary: dict[str, Any] = Field(description="当月完成量/金额汇总")
    attachment: str | None = Field(default=None, description="报告附件路径")
    status: str = Field(description="报告状态")


class ReportCreateSchema(BaseModel):
    """创建月度报告"""

    project_id: int = Field(gt=0, description="项目ID")
    template_id: int | None = Field(default=None, description="二级模板ID(可空:全项目汇总)")
    period: str = Field(min_length=1, max_length=16, description="报告月份(如 2026-03)")
    summary: dict[str, Any] = Field(description="当月完成量/金额汇总")
    attachment: str | None = Field(default=None, max_length=500, description="报告附件路径")
    status: str = Field(default="DRAFT", description="报告状态")


class ReportUpdateSchema(BaseModel):
    """更新月度报告"""

    template_id: int | None = Field(default=None, description="二级模板ID(可空:全项目汇总)")
    summary: dict[str, Any] | None = Field(default=None, description="当月完成量/金额汇总")
    attachment: str | None = Field(default=None, max_length=500, description="报告附件路径")
    status: str | None = Field(default=None, description="报告状态")


class ReportQueryParam(BaseQueryParam, UserByQueryParam):
    """月度报告查询参数"""

    project_id: int | None = Field(default=None, description="项目ID", json_schema_extra={"q": "eq"})
    template_id: int | None = Field(default=None, description="二级模板ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="报告月份", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="报告状态", json_schema_extra={"q": "eq"})
