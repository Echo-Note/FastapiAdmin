from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin

if TYPE_CHECKING:
    from app.modules.market.task.model import SubmissionModel


class InstitutionModel(ModelMixin, UserMixin):
    """机构主数据（医院 / 药店 / 商业公司）

    成果提交针对的对象实体。一次提交 = 一个机构 × 一份采集表。
    同时作为 C 端提交图片的归集主体，一对多关联 ``InstitutionImageModel``。
    """

    __tablename__: str = "market_institution"
    __table_args__: dict[str, str] = {"comment": "机构主数据表"}

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="机构名称")
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="机构类型(等级医院/基层医疗/民营医疗/零售药店/商业公司)")
    level: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="等级(如三甲/二级，可选)")
    region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="所在区域")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="详细地址")
    contact: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启用 1:停用)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    images: Mapped[list["InstitutionImageModel"]] = relationship(
        back_populates="institution", cascade="all, delete-orphan"
    )


class InstitutionImageModel(ModelMixin, UserMixin):
    """机构图片归集表

    归集 C 端提交成果时上传的机构图片（门头照/内景照/打卡照等），
    通过 ``institution_id`` 归属到具体机构，``submission_id`` 记录图片来源成果（可空）。
    """

    __tablename__: str = "market_institution_image"
    __table_args__: dict[str, str] = {"comment": "机构图片归集表"}

    institution_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("market_institution.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属机构ID"
    )
    submission_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("market_submission.id", ondelete="SET NULL"), nullable=True, index=True, comment="来源成果ID(可空)"
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="图片地址")
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="图片分类(门头照/内景照/打卡照等)")
    uploaded_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="上传人ID"
    )
    period: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True, comment="提交月份(如 2026-03)")

    institution: Mapped["InstitutionModel"] = relationship(back_populates="images")
    submission: Mapped["SubmissionModel"] = relationship()


__all__ = [
    "InstitutionModel",
    "InstitutionImageModel",
]
