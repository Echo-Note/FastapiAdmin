from pydantic import ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class SettlementItemOutSchema(BaseSchema):
    """结算明细响应模型"""

    model_config = ConfigDict(from_attributes=True)

    settlement_id: int = Field(description="结算单ID")
    service_type: str = Field(description="服务项目-类型")
    service_item: str = Field(description="服务项目-项目")
    service_task: str = Field(description="服务项目-任务")
    unit: str = Field(description="计价单位")
    price: float = Field(description="单价")
    qty: int = Field(description="数量")
    amount: float = Field(description="金额")


class SettlementOutSchema(BaseSchema, UserBySchema):
    """结算单响应模型"""

    model_config = ConfigDict(from_attributes=True)

    task_id: int = Field(description="任务ID")
    user_id: int = Field(description="C端用户ID")
    qty: int = Field(description="归集成果数量")
    payable_amount: float = Field(description="应发金额")
    paid_amount: float | None = Field(default=None, description="实发金额(预留)")
    pay_status: str | None = Field(default=None, description="支付状态(预留)")
    status: str = Field(description="结算单状态")
    items: list[SettlementItemOutSchema] = Field(default_factory=list, description="结算明细")


class SettlementQueryParam(BaseQueryParam, UserByQueryParam):
    """结算单查询参数"""

    task_id: int | None = Field(default=None, description="任务ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="结算单状态", json_schema_extra={"q": "eq"})
