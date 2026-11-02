"""发放额度与个人任务津贴的 Schema 定义。"""

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserBySchema


class PayoutConfigOutSchema(BaseSchema, UserBySchema):
    """发放额度配置响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    period: str = Field(description="周期(如 2026-10)")
    payout_limit: float = Field(description="每月发放额度(默认 20000)")
    enabled: bool = Field(default=True, description="是否启用")


class MyEarningsSummaryOutSchema(BaseModel):
    """C 端「我的收益」汇总（我的页顶部收益卡）

    只回答三个问题：这个月我能拿多少、卡在额度上的有多少、这个月的额度上限是多少。
    """

    period: str = Field(description="统计周期(如 2026-10)")
    month_payable: float = Field(description="本月应发金额(本月周期任务归属的结算单金额合计)")
    settlement_count: int = Field(default=0, description="本月结算单数量")
    allowance_balance: float = Field(default=0, description="个人任务津贴余额(超出额度未发、顺延下月)")
    payout_limit: float = Field(description="本月发放额度上限")


class PayoutConfigCreateSchema(BaseModel):
    """创建发放额度配置"""

    user_id: int = Field(gt=0, description="C端用户ID")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")
    payout_limit: float = Field(gt=0, description="每月发放额度(如 10000/20000)")
    enabled: bool = Field(default=True, description="是否启用")


class PayoutConfigUpdateSchema(BaseModel):
    """更新发放额度配置"""

    payout_limit: float | None = Field(default=None, gt=0, description="每月发放额度")
    enabled: bool | None = Field(default=None, description="是否启用")


class AllowanceDetailOutSchema(BaseSchema):
    """津贴明细响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    from_period: str = Field(description="来源周期(如 2026-10)")
    amount: float = Field(description="未发放金额")
    status: str = Field(description="状态(待发/已发)")


class PayoutQueryParam(BaseQueryParam):
    """发放额度查询参数"""

    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
