"""C 端成员档案数据访问层。"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import MemberModel
from .schema import MemberCreateSchema, MemberUpdateSchema


class MemberCRUD(MarketCRUDBase[MemberModel, MemberCreateSchema, MemberUpdateSchema]):
    """成员档案数据层。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=MemberModel, auth=auth, db=db)


__all__: list[Any] = ["MemberCRUD"]
