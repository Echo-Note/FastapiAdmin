"""任务管理域 CRUD 层。

各实体继承 ``MarketCRUDBase``（跳过 created_id 数据范围过滤，数据权限由 Service 层显式控制）。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import AssignmentModel, SubmissionModel, TaskCategoryModel, TaskItemModel, TaskModel, TaskTemplateModel
from .schema import (
    AssignmentCreateSchema,
    AssignmentUpdateSchema,
    SubmissionCreateSchema,
    SubmissionUpdateSchema,
    TaskCategoryCreateSchema,
    TaskCategoryUpdateSchema,
    TaskCreateSchema,
    TaskItemCreateSchema,
    TaskItemUpdateSchema,
    TaskTemplateCreateSchema,
    TaskTemplateUpdateSchema,
    TaskUpdateSchema,
)


class TaskCategoryCRUD(MarketCRUDBase[TaskCategoryModel, TaskCategoryCreateSchema, TaskCategoryUpdateSchema]):
    """一级任务分类数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TaskCategoryModel, auth=auth, db=db)


class TaskTemplateCRUD(MarketCRUDBase[TaskTemplateModel, TaskTemplateCreateSchema, TaskTemplateUpdateSchema]):
    """二级任务模板数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TaskTemplateModel, auth=auth, db=db)


class TaskItemCRUD(MarketCRUDBase[TaskItemModel, TaskItemCreateSchema, TaskItemUpdateSchema]):
    """三级任务数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TaskItemModel, auth=auth, db=db)


class TaskCRUD(MarketCRUDBase[TaskModel, TaskCreateSchema, TaskUpdateSchema]):
    """任务实例数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TaskModel, auth=auth, db=db)


class AssignmentCRUD(MarketCRUDBase[AssignmentModel, AssignmentCreateSchema, AssignmentUpdateSchema]):
    """任务分配/接收数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=AssignmentModel, auth=auth, db=db)


class SubmissionCRUD(MarketCRUDBase[SubmissionModel, SubmissionCreateSchema, SubmissionUpdateSchema]):
    """成果提交数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SubmissionModel, auth=auth, db=db)
