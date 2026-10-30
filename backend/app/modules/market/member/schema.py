"""C 端成员档案的 Schema。"""

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema

from ..enums import MemberStatus
from .brief import MarketUserBriefSchema


class MemberOutSchema(BaseSchema):
    """成员档案响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(description="C端用户ID")
    user: MarketUserBriefSchema | None = Field(default=None, description="用户摘要(昵称/账号/手机号)")
    member_no: str = Field(description="成员编号(如 U-0001)")
    status: str = Field(description="成员状态(ACTIVE/DISABLED)")


class MemberQueryParam(BaseQueryParam):
    """成员档案查询参数。"""

    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    member_no: str | None = Field(default=None, description="成员编号", json_schema_extra={"q": "like"})
    status: str | None = Field(default=None, description="成员状态", json_schema_extra={"q": "eq"})


class MemberCreateSchema(BaseModel):
    """把已有 sys_user 纳入为 C 端成员（运营手动建档）。"""

    user_id: int = Field(gt=0, description="C端用户ID")
    status: MemberStatus = Field(default=MemberStatus.ACTIVE, description="成员状态")


class MemberUpdateSchema(BaseModel):
    """调整成员状态。"""

    status: MemberStatus = Field(description="成员状态(ACTIVE/DISABLED)")
