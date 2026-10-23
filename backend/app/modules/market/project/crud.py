"""项目（对外）与项目-任务归集的数据访问层。"""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import ProjectModel, ProjectTaskModel
from .schema import ProjectCreateSchema, ProjectTaskCreateSchema, ProjectUpdateSchema


class ProjectCRUD(MarketCRUDBase[ProjectModel, ProjectCreateSchema, ProjectUpdateSchema]):
    """项目数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ProjectModel, auth=auth, db=db)


class ProjectTaskCRUD(MarketCRUDBase[ProjectTaskModel, ProjectTaskCreateSchema, ProjectTaskCreateSchema]):
    """项目-任务归集数据层（创建/更新共用同一 schema）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ProjectTaskModel, auth=auth, db=db)

    async def delete(self, ids: list[int]) -> None:
        """归集关系物理删除。

        归集表带 ``unique(project_id, task_id)`` 约束，若走基类软删除，重建同一条归集关系会
        触发唯一约束冲突，故此处强制物理删除。
        """
        pk = self._get_pk_col()
        sql = delete(self.model).where(pk.in_(ids))
        await self.db.execute(sql)
        await self.db.flush()


__all__ = ["ProjectCRUD", "ProjectTaskCRUD"]
