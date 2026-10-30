"""项目管理（对外）、医药公司主数据、项目-三级任务关联、月度报告的数据访问层。"""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import CompanyModel, ProjectItemModel, ProjectModel, ReportModel
from .schema import (
    CompanyCreateSchema,
    CompanyUpdateSchema,
    ProjectCreateSchema,
    ProjectItemCreateSchema,
    ProjectUpdateSchema,
    ReportCreateSchema,
    ReportUpdateSchema,
)


class CompanyCRUD(MarketCRUDBase[CompanyModel, CompanyCreateSchema, CompanyUpdateSchema]):
    """医药公司数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=CompanyModel, auth=auth, db=db)


class ProjectCRUD(MarketCRUDBase[ProjectModel, ProjectCreateSchema, ProjectUpdateSchema]):
    """项目数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ProjectModel, auth=auth, db=db)


class ProjectItemCRUD(MarketCRUDBase[ProjectItemModel, ProjectItemCreateSchema, ProjectItemCreateSchema]):
    """项目-三级任务关联数据层（创建/更新共用同一 schema）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ProjectItemModel, auth=auth, db=db)

    async def delete(self, ids: list[int]) -> None:
        """关联关系物理删除。

        关联表带 ``unique(project_id, item_id)`` 约束，若走基类软删除，重建同一条关联会
        触发唯一约束冲突，故此处强制物理删除。
        """
        pk = self._get_pk_col()
        sql = delete(self.model).where(pk.in_(ids))
        await self.db.execute(sql)
        await self.db.flush()


class ReportCRUD(MarketCRUDBase[ReportModel, ReportCreateSchema, ReportUpdateSchema]):
    """月度报告数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ReportModel, auth=auth, db=db)


__all__ = ["CompanyCRUD", "ProjectCRUD", "ProjectItemCRUD", "ReportCRUD"]
