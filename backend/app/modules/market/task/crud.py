from datetime import UTC, datetime

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from ..enums import AssignMode, TaskStatus
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

    async def hall_page(self, offset: int, limit: int, preload: list[str] | None = None) -> tuple[list[TaskModel], int]:
        """公开大厅任务分页查询。

        条件：assign_mode=open + 状态 in (已发布, 进行中) + 未超出限定时间范围（exec_time_end 为空或未来）。
        返回 ``(任务列表, 总条数)``，由 Service 层组装 ``PageResultSchema``。
        """
        now = datetime.now(UTC)
        conditions = [
            TaskModel.assign_mode == AssignMode.OPEN.value,
            TaskModel.status.in_([TaskStatus.PUBLISHED.value, TaskStatus.IN_PROGRESS.value]),
            TaskModel.is_deleted == false(),
            or_(TaskModel.exec_time_end.is_(None), TaskModel.exec_time_end > now),
        ]
        data_sql = select(TaskModel).where(*conditions)
        for opt in self._loader_options(preload):
            data_sql = data_sql.options(opt)
        count_sql = select(func.count(TaskModel.id)).select_from(TaskModel).where(*conditions)
        total = (await self.db.execute(count_sql)).scalar() or 0
        result = await self.db.execute(data_sql.order_by(TaskModel.id.desc()).offset(offset).limit(limit))
        return list(result.scalars().all()), int(total)
