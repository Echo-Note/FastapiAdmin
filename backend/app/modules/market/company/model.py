from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CompanyModel(ModelMixin, UserMixin):
    """医药公司主数据

    任务委托方。一期由运营端代发任务，医药公司不直接操作平台（二期开放自助发布）。
    """

    __tablename__: str = "market_company"
    __table_args__: dict[str, str] = {"comment": "医药公司主数据表"}

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True, comment="公司名称")
    code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, comment="公司编码")
    credit_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="统一社会信用代码")
    contact: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="公司地址")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启用 1:停用)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
