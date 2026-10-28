"""发放管理域（归集结算 / 发放额度 / 个人任务津贴）的 Schema 定义。"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class SettlementItemOutSchema(BaseSchema):
    """结算明细响应模型"""

    model_config = ConfigDict(from_attributes=True)

    settlement_id: int = Field(description="结算单ID")
    category_name: str = Field(description="一级任务分类名")
    template_name: str = Field(description="二级任务名")
    unit: str = Field(description="计价单位")
    price: Decimal = Field(description="单价")
    qty: int = Field(description="数量")
    amount: Decimal = Field(description="金额")


class SettlementOutSchema(BaseSchema, UserBySchema):
    """结算单响应模型"""

    model_config = ConfigDict(from_attributes=True)

    task_id: int = Field(description="任务ID")
    user_id: int = Field(description="C端用户ID")
    period: str = Field(description="结算月份(如 2026-03)")
    qty: int = Field(description="归集成果数量")
    payable_amount: Decimal = Field(description="应发金额")
    paid_amount: Decimal | None = Field(default=None, description="实发金额(预留)")
    pay_status: str | None = Field(default=None, description="支付状态(预留)")
    status: str = Field(description="结算单状态")
    items: list[SettlementItemOutSchema] = Field(default_factory=list, description="结算明细")


class SettlementQueryParam(BaseQueryParam, UserByQueryParam):
    """结算单查询参数"""

    task_id: int | None = Field(default=None, description="任务ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="结算月份", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="结算单状态", json_schema_extra={"q": "eq"})


class PayoutConfigOutSchema(BaseSchema, UserBySchema):
    """发放额度配置响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    period: str = Field(description="周期(如 2026-10)")
    payout_limit: Decimal = Field(description="每月发放额度(默认 20000)")
    enabled: bool = Field(default=True, description="是否启用")


class PayoutConfigCreateSchema(BaseModel):
    """创建发放额度配置"""

    user_id: int = Field(gt=0, description="C端用户ID")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")
    payout_limit: Decimal = Field(gt=0, description="每月发放额度(如 10000/20000)")
    enabled: bool = Field(default=True, description="是否启用")


class PayoutConfigUpdateSchema(BaseModel):
    """更新发放额度配置"""

    payout_limit: Decimal | None = Field(default=None, gt=0, description="每月发放额度")
    enabled: bool | None = Field(default=None, description="是否启用")


class PayoutConfigQueryParam(BaseQueryParam, UserByQueryParam):
    """发放额度配置查询参数"""

    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    enabled: bool | None = Field(default=None, description="是否启用", json_schema_extra={"q": "eq"})


class AllowanceOutSchema(BaseSchema, UserBySchema):
    """个人任务津贴账户响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    balance: Decimal = Field(description="累计未发放金额")


class AllowanceDetailOutSchema(BaseSchema):
    """津贴明细响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    from_period: str = Field(description="来源周期(如 2026-10)")
    amount: Decimal = Field(description="未发放金额")
    status: str = Field(description="状态(待发/已发)")
    paid_at: str | None = Field(default=None, description="发放时间(二期)")
