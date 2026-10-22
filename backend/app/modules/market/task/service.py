from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..company.crud import CompanyCRUD
from ..enums import TaskStatus
from .crud import TaskCRUD, TaskTypeCRUD
from .schema import (
    TaskCreateSchema,
    TaskOutSchema,
    TaskPublishSchema,
    TaskQueryParam,
    TaskTypeCreateSchema,
    TaskTypeOutSchema,
    TaskTypeQueryParam,
    TaskTypeUpdateSchema,
    TaskUpdateSchema,
)

# task_type / company 均为 UserBySchema（含 created_by/updated_by），必须嵌套预加载其审计关系，
# 避免 detail()/page() 序列化时在异步环境下触发懒加载 MissingGreenlet
_TASK_PRELOAD = [
    "task_type",
    "task_type.created_by",
    "task_type.updated_by",
    "company",
    "company.created_by",
    "company.updated_by",
]


class TaskTypeService:
    """任务类型模板服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> TaskTypeOutSchema:
        """查询任务类型模板详情。"""
        task_type = await TaskTypeCRUD(self.auth, self.db).get_or_404(id=id)
        return TaskTypeOutSchema.model_validate(task_type)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TaskTypeQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TaskTypeOutSchema]:
        """分页查询任务类型模板。"""
        offset = (page_no - 1) * page_size
        return await TaskTypeCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search),
            out_schema=TaskTypeOutSchema,
        )

    async def create(self, data: TaskTypeCreateSchema) -> TaskTypeOutSchema:
        """创建任务类型模板。"""
        if await TaskTypeCRUD(self.auth, self.db).get(code=data.code):
            raise CustomException(msg="已存在相同编码的任务类型")
        task_type = await TaskTypeCRUD(self.auth, self.db).create(data=data)
        return TaskTypeOutSchema.model_validate(task_type)

    async def update(self, id: int, data: TaskTypeUpdateSchema) -> TaskTypeOutSchema:
        """更新任务类型模板。"""
        await TaskTypeCRUD(self.auth, self.db).get_or_404(id=id)
        if data.code and (exist := await TaskTypeCRUD(self.auth, self.db).get(code=data.code)) and exist.id != id:
            raise CustomException(msg="已存在相同编码的任务类型")
        await TaskTypeCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除任务类型模板。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await TaskTypeCRUD(self.auth, self.db).delete(ids=ids)


class TaskService:
    """任务服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> TaskOutSchema:
        """查询任务详情。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id, preload=_TASK_PRELOAD)
        return TaskOutSchema.model_validate(task)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TaskQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TaskOutSchema]:
        """分页查询任务。"""
        offset = (page_no - 1) * page_size
        return await TaskCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=TaskOutSchema,
            preload=_TASK_PRELOAD,
        )

    async def create(self, data: TaskCreateSchema) -> TaskOutSchema:
        """创建任务（草稿状态）。"""
        if await TaskCRUD(self.auth, self.db).get(task_no=data.task_no):
            raise CustomException(msg="已存在相同任务号的任务")
        task_type = await TaskTypeCRUD(self.auth, self.db).get_or_404(id=data.task_type_id, msg="任务类型模板不存在")
        await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        if data.unit_price is None:
            data.unit_price = float(task_type.default_price)
        task = await TaskCRUD(self.auth, self.db).create(data=data)
        return await self.detail(id=task.id)

    async def update(self, id: int, data: TaskUpdateSchema) -> TaskOutSchema:
        """更新任务（仅草稿状态可改）。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可修改")
        if data.task_no and (exist := await TaskCRUD(self.auth, self.db).get(task_no=data.task_no)) and exist.id != id:
            raise CustomException(msg="已存在相同任务号的任务")
        await TaskCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除任务（仅草稿状态可删）。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        tasks = await TaskCRUD(self.auth, self.db).get_list(search={"id": ("in", ids)})
        for task in tasks:
            if task.status != TaskStatus.DRAFT.value:
                raise CustomException(msg=f"任务[{task.task_no}]非草稿状态，不能删除")
        await TaskCRUD(self.auth, self.db).delete(ids=ids)

    async def publish(self, id: int, data: TaskPublishSchema | None = None) -> TaskOutSchema:
        """发布任务：DRAFT → PUBLISHED。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可发布")
        update_data: dict[str, Any] = {"status": TaskStatus.PUBLISHED.value, "published_at": datetime.now(UTC)}
        if data and data.deadline_at:
            update_data["deadline_at"] = data.deadline_at
        await TaskCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)
