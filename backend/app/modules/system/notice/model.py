from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class NoticeModel(ModelMixin, UserMixin):
    """通知公告表"""

    __tablename__: str = "sys_notice"
    __table_args__: dict[str, str] = {"comment": "通知公告表"}

    notice_title: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="公告标题")
    notice_type: Mapped[str] = mapped_column(String(1), nullable=False, index=True, comment="公告类型(1通知 2公告)")
    notice_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="公告内容")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启用 1:停用 2:归档[预留])")
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class NoticeReadModel(ModelMixin):
    """公告已读记录（一个用户 × 一条公告 一条记录）

    公告本身是广播内容，没有“收件人”；已读是**按人**的事实，所以单独一张表。
    重复标记走「已存在则跳过」，不依赖前端去重。
    """

    __tablename__: str = "sys_notice_read"
    __table_args__ = (
        UniqueConstraint("user_id", "notice_id", name="uq_sys_notice_read_user_notice"),
        {"comment": "公告已读记录表"},
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID"
    )
    notice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_notice.id", ondelete="CASCADE"), nullable=False, index=True, comment="公告ID"
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="已读时间")
