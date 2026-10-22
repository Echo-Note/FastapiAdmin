from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import TaskModel, TaskTypeModel
from .schema import (
    TaskCreateSchema,
    TaskTypeCreateSchema,
    TaskTypeUpdateSchema,
    TaskUpdateSchema,
)


class TaskTypeCRUD(MarketCRUDBase[TaskTypeModel, TaskTypeCreateSchema, TaskTypeUpdateSchema]):
    """任务类型模板数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TaskTypeModel, auth=auth, db=db)


class TaskCRUD(MarketCRUDBase[TaskModel, TaskCreateSchema, TaskUpdateSchema]):
    """任务数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TaskModel, auth=auth, db=db)
