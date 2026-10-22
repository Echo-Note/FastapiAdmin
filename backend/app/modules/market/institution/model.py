from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class InstitutionModel(ModelMixin, UserMixin):
    """机构主数据（医院 / 药店 / 商业公司）

    成果提交针对的对象实体。一次提交 = 一个机构 × 一份采集表。
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
