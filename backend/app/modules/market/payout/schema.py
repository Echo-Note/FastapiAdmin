"""发放管理域（归集结算 / 发放额度 / 个人任务津贴）的 Schema 定义。"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.modules.market.member import MarketUserBriefSchema


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
    user: MarketUserBriefSchema | None = Field(default=None, description="C端用户摘要(昵称/账号/手机号)")
    period: str = Field(description="结算月份(如 2026-03)")
    qty: int = Field(description="归集成果数量")
    payable_amount: Decimal = Field(description="应发金额")
    paid_amount: Decimal | None = Field(default=None, description="实发金额(受当月发放额度封顶，未归集时为空)")
    pay_status: str | None = Field(default=None, description="支付状态(SCHEDULED=已算出待打款)")
    status: str = Field(description="结算单状态")
    items: list[SettlementItemOutSchema] = Field(default_factory=list, description="结算明细")


class SettlementQueryParam(BaseQueryParam, UserByQueryParam):
    """结算单查询参数"""

    task_id: int | None = Field(default=None, description="任务ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="结算月份", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="结算单状态", json_schema_extra={"q": "eq"})


class PayoutResultOutSchema(BaseModel):
    """发放结果（用户 × 周期）响应模型。

    口径见 ``service.py`` 顶部注释：
    ``待发 = 应发 + 期初津贴``，``实发 = min(待发, 额度)``，``期末津贴 = 待发 - 实发``。
    """

    user_id: int = Field(description="C端用户ID")
    user: MarketUserBriefSchema | None = Field(default=None, description="C端用户摘要(昵称/账号/手机号)")
    period: str = Field(description="周期(如 2026-10)")
    payable: Decimal = Field(description="当月应发合计(跨任务的结算单 payable 之和)")
    prev_balance: Decimal = Field(description="期初津贴余额(上期期末未发放额)")
    limit: Decimal = Field(description="当月发放额度")
    paid: Decimal = Field(description="当月实发(受额度封顶)")
    rollover: Decimal = Field(description="期末津贴余额(滚入下月)")


class PayoutResultQueryParam(BaseModel):
    """发放结果查询参数（按用户 / 周期筛，均为等值）。"""

    user_id: int | None = Field(default=None, ge=1, description="C端用户ID")
    period: str | None = Field(default=None, max_length=16, description="周期(如 2026-10)")


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


class MyPayoutSettlementOutSchema(BaseModel):
    """C 端收益明细的一行：该周期的一条结算单 + 这笔钱由哪个任务产生。"""

    id: int = Field(description="结算单ID")
    task_id: int = Field(description="任务ID")
    task_no: str = Field(description="任务编号(如 TK-001)")
    task_name: str = Field(description="任务名(C端显示名，即收益来源)")
    category_name: str | None = Field(default=None, description="一级任务分类名(来自结算明细快照)")
    template_name: str | None = Field(default=None, description="二级任务名(来自结算明细快照)")
    unit: str | None = Field(default=None, description="计价单位")
    price: Decimal | None = Field(default=None, description="单价")
    qty: int = Field(description="归集成果数量")
    payable: Decimal = Field(description="应发金额")
    paid: Decimal = Field(description="实发金额(受当月发放额度封顶; 未归集时为 0)")
    pay_status: str | None = Field(default=None, description="支付状态(SCHEDULED=已算出待打款)")


class MyPayoutOutSchema(BaseModel):
    """C 端「我的收益」按月视图：切月即换一套数字。

    口径与 ``PayoutService.my_payout`` 一致——应发/实发/期末滚存都取**该周期**的结算单与
    津贴账本，不从全量历史里挑；页面顶部切月只改 ``period``，其余由后端按周期给出。
    """

    user_id: int = Field(description="C端用户ID")
    period: str = Field(description="周期(如 2026-10)")
    payable: Decimal = Field(description="当月应发合计(该周期结算单 payable 之和)")
    paid: Decimal = Field(description="当月实发合计(该周期结算单 paid 之和)")
    payout_limit: Decimal = Field(description="当月发放额度")
    prev_balance: Decimal = Field(description="期初津贴余额(上期期末未发放额)")
    allowance_balance: Decimal = Field(description="期末津贴余额(该期未结算时等于期初)")
    settlements: list[MyPayoutSettlementOutSchema] = Field(
        default_factory=list, description="该周期结算单(收益来源，按结算单ID升序)"
    )
