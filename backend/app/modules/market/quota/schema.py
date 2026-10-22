from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserBySchema


class QuotaConfigOutSchema(BaseSchema, UserBySchema):
    """限额配置响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    period: str = Field(description="周期(如 2026-10)")
    quota_amount: float = Field(description="限额额度")
    enabled: bool = Field(default=True, description="是否启用")


class QuotaConfigCreateSchema(BaseModel):
    """创建限额配置"""

    user_id: int = Field(gt=0, description="C端用户ID")
    period: str = Field(min_length=1, max_length=16, description="周期(如 2026-10)")
    quota_amount: float = Field(gt=0, description="限额额度")
    enabled: bool = Field(default=True, description="是否启用")


class QuotaConfigUpdateSchema(BaseModel):
    """更新限额配置"""

    quota_amount: float | None = Field(default=None, gt=0, description="限额额度")
    enabled: bool | None = Field(default=None, description="是否启用")


class QuotaUsageOutSchema(BaseSchema):
    """限额使用响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    period: str = Field(description="周期(如 2026-10)")
    received_amount: float = Field(description="累计接收金额")
    payable_amount: float = Field(description="累计应发金额")
    over_amount: float = Field(description="累计超限金额")


class QuotaCarryoverOutSchema(BaseSchema):
    """顺延金额响应模型"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    from_period: str = Field(description="来源周期(如 2026-10)")
    to_period: str = Field(description="顺延至周期(如 2026-11)")
    amount: float = Field(description="顺延金额")
    status: str = Field(description="顺延状态")


class QuotaQueryParam(BaseQueryParam):
    """限额查询参数"""

    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
