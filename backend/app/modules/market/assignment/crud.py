from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import AssignmentModel
from .schema import AssignmentCreateSchema


class AssignmentCRUD(MarketCRUDBase[AssignmentModel, AssignmentCreateSchema, AssignmentCreateSchema]):
    """任务分派数据层（无独立更新模型，复用创建模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=AssignmentModel, auth=auth, db=db)
