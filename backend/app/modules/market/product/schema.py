"""产品库 Schema 定义。

输出 Schema 继承 ``BaseSchema`` 与 ``UserBySchema``（审计人）；
输入 Schema 用 Pydantic ``Field`` 做校验；查询参数继承 ``BaseQueryParam`` 与
``UserByQueryParam``，配合 ``json_schema_extra={"q": ...}`` 控制操作符。
"""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class ProductOutSchema(BaseSchema, UserBySchema):
    """产品库响应模型"""

    name: str = Field(description="产品名称")
    spec: str = Field(default="", description="产品规格")
    manufacturer: str = Field(default="", description="生产企业")
    source: str = Field(description="来源(admin 运营录入/user C端提交)")
    audit_status: str = Field(description="审核状态(pending/approved/rejected)")
    submitter_id: int | None = Field(default=None, description="C端提交人ID")
    reviewer_id: int | None = Field(default=None, description="审核人ID")
    review_comment: str | None = Field(default=None, description="审核意见")
    reviewed_at: datetime | None = Field(default=None, description="审核时间")
    display_name: str = Field(default="", description="完整展示名(名称/规格/生产企业)")


class ProductCreateSchema(BaseModel):
    """运营录入产品（录入即生效，不需要二次审核）"""

    name: str = Field(min_length=1, max_length=128, description="产品名称")
    spec: str = Field(default="", max_length=128, description="产品规格")
    manufacturer: str = Field(default="", max_length=255, description="生产企业")

    @model_validator(mode="after")
    def _normalize(self) -> "ProductCreateSchema":
        """名称/规格/企业去首尾空白，避免同一产品因空格被当成不同记录。"""
        self.name = self.name.strip()
        self.spec = self.spec.strip()
        self.manufacturer = self.manufacturer.strip()
        if not self.name:
            raise ValueError("产品名称不能为空")
        return self


class ProductUpdateSchema(BaseModel):
    """修改产品（改名/规格/企业等于改动判重键，由唯一约束兜底）"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="产品名称")
    spec: str | None = Field(default=None, max_length=128, description="产品规格")
    manufacturer: str | None = Field(default=None, max_length=255, description="生产企业")


class ProductQueryParam(BaseQueryParam, UserByQueryParam):
    """产品库查询参数"""

    name: str | None = Field(default=None, description="产品名称", json_schema_extra={"q": "like"})
    manufacturer: str | None = Field(default=None, description="生产企业", json_schema_extra={"q": "like"})
    audit_status: str | None = Field(default=None, description="审核状态", json_schema_extra={"q": "eq"})
    source: str | None = Field(default=None, description="来源", json_schema_extra={"q": "eq"})


class ProductAuditSchema(BaseModel):
    """产品审核（支持批量）"""

    ids: list[int] = Field(min_length=1, description="待审核产品ID列表")
    approved: bool = Field(description="True 通过 / False 驳回")
    review_comment: str | None = Field(default=None, max_length=500, description="审核意见(驳回时建议填写)")

    @model_validator(mode="after")
    def _require_comment_on_reject(self) -> "ProductAuditSchema":
        """驳回必须给意见，避免运营与提交人对不上为什么被拒。"""
        if not self.approved and not (self.review_comment or "").strip():
            raise ValueError("驳回必须填写审核意见")
        return self


class ProductSearchItemSchema(BaseModel):
    """C 端产品检索候选（只暴露填充所需的三要素）"""

    id: int = Field(description="产品ID")
    name: str = Field(description="产品名称")
    spec: str = Field(default="", description="产品规格")
    manufacturer: str = Field(default="", description="生产企业")
    display_name: str = Field(default="", description="完整展示名(名称/规格/生产企业)")


class ProductSearchQueryParam(BaseModel):
    """C 端产品检索参数"""

    keyword: str = Field(default="", max_length=128, description="按产品名称模糊匹配")
    limit: int = Field(default=20, ge=1, le=50, description="返回条数上限")


__all__ = [
    "ProductAuditSchema",
    "ProductCreateSchema",
    "ProductOutSchema",
    "ProductQueryParam",
    "ProductSearchItemSchema",
    "ProductSearchQueryParam",
    "ProductUpdateSchema",
]
