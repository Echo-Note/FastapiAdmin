from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.modules.market.company.schema import CompanyOutSchema


class ReportOutSchema(BaseSchema, UserBySchema):
    """报告响应模型"""

    model_config = ConfigDict(from_attributes=True)

    company_id: int = Field(description="医药公司ID")
    company: CompanyOutSchema | None = Field(default=None, description="医药公司")
    period: str = Field(description="周期(如 2026-10)")
    summary: dict[str, Any] = Field(default_factory=dict, description="各任务类型完成量/金额汇总")
    attachment: str | None = Field(default=None, description="明细附件路径")
    status: str = Field(description="报告状态")


class ReportCreateSchema(BaseModel):
    """生成报告（按医药公司 × 周期打包）"""

    company_id: int = Field(gt=0, description="医药公司ID")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")


class ReportQueryParam(BaseQueryParam, UserByQueryParam):
    """报告查询参数"""

    company_id: int | None = Field(default=None, description="医药公司ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="报告状态", json_schema_extra={"q": "eq"})
