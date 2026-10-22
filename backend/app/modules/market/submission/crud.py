from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import SubmissionModel
from .schema import SubmissionCreateSchema, SubmissionUpdateSchema


class SubmissionCRUD(MarketCRUDBase[SubmissionModel, SubmissionCreateSchema, SubmissionUpdateSchema]):
    """成果提交数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SubmissionModel, auth=auth, db=db)
