"""产品库数据模型。

产品库维护 C 端成果提交时需要反复录入的产品三要素（产品名称 / 产品规格 / 生产企业）。
判重键就是这三列：三者全等视为同一个产品，同名不同厂商或不同规格是各自独立的记录，
C 端检索命中多条时由用户选择。

来源与审核：运营录入（``source=admin``）直接生效；C 端提交成果时自动入库
（``source=user``）先落 ``pending``，仅提交人自己可检索，运营审核通过（``approved``）
后对所有人可见，驳回（``rejected``）则不再参与检索。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin

from ..enums import ProductAuditStatus, ProductSource


class ProductModel(ModelMixin, UserMixin):
    """产品库（产品三要素字典 + 审核状态）。"""

    __tablename__: str = "market_product"
    __table_args__ = (
        UniqueConstraint("name", "spec", "manufacturer", name="uq_market_product_name_spec_manufacturer"),
        {"comment": "产品库表"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="产品名称")
    spec: Mapped[str] = mapped_column(String(128), nullable=False, default="", comment="产品规格(空串表示未填)")
    manufacturer: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="生产企业(空串表示未填)"
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ProductSource.ADMIN.value, index=True, comment="来源(admin 运营录入/user C端提交)"
    )
    audit_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ProductAuditStatus.APPROVED.value,
        index=True,
        comment="审核状态(pending 待审核/approved 已通过/rejected 已驳回)",
    )
    submitter_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="C端提交人ID(运营录入为空)",
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="审核人ID"
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审核时间")

    @property
    def display_name(self) -> str:
        """完整展示名（名称 + 规格 + 生产企业），用于 C 端候选列表与运营端核对。"""
        parts = [self.name]
        if self.spec:
            parts.append(self.spec)
        if self.manufacturer:
            parts.append(self.manufacturer)
        return " / ".join(parts)


__all__ = ["ProductModel"]
