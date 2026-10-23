"""项目（对外）与项目-任务归集的业务逻辑。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..company.crud import CompanyCRUD
from ..enums import ProjectStatus
from ..task.crud import TaskCRUD
from .crud import ProjectCRUD, ProjectTaskCRUD
from .schema import (
    ProjectAddTaskSchema,
    ProjectCreateSchema,
    ProjectOutSchema,
    ProjectQueryParam,
    ProjectStatusUpdateSchema,
    ProjectUpdateSchema,
)

# company 为 UserBySchema（含 created_by/updated_by），需嵌套预加载审计关系；
# task_links 为归集关系，序列化 task_ids 时依赖它，需 selectinload 预加载
_PROJECT_PRELOAD = [
    "company",
    "company.created_by",
    "company.updated_by",
    "task_links",
]


class ProjectService:
    """项目服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> ProjectOutSchema:
        """查询项目详情。"""
        project = await ProjectCRUD(self.auth, self.db).get_or_404(id=id, preload=_PROJECT_PRELOAD)
        return ProjectOutSchema.model_validate(project)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: ProjectQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ProjectOutSchema]:
        """分页查询项目。"""
        offset = (page_no - 1) * page_size
        return await ProjectCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=ProjectOutSchema,
            preload=_PROJECT_PRELOAD,
        )

    async def create(self, data: ProjectCreateSchema) -> ProjectOutSchema:
        """创建项目（草稿状态），并归集指定任务。"""
        if await ProjectCRUD(self.auth, self.db).get(code=data.code):
            raise CustomException(msg="已存在相同编码的项目")
        await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        create_data = data.model_dump(exclude={"task_ids"})
        project = await ProjectCRUD(self.auth, self.db).create(data=create_data)
        await self._sync_task_links(project.id, data.task_ids)
        return await self.detail(id=project.id)

    async def update(self, id: int, data: ProjectUpdateSchema) -> ProjectOutSchema:
        """更新项目。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id)
        if data.code and (exist := await ProjectCRUD(self.auth, self.db).get(code=data.code)) and exist.id != id:
            raise CustomException(msg="已存在相同编码的项目")
        if data.company_id is not None:
            await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"task_ids"})
        await ProjectCRUD(self.auth, self.db).update(id=id, data=update_data)
        if data.task_ids is not None:
            await self._sync_task_links(id, data.task_ids)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除项目。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await ProjectCRUD(self.auth, self.db).delete(ids=ids)

    async def add_task(self, id: int, data: ProjectAddTaskSchema) -> ProjectOutSchema:
        """把任务归集到项目（增量，幂等）。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id, preload=_PROJECT_PRELOAD)
        await TaskCRUD(self.auth, self.db).get_or_404(id=data.task_id, msg="任务不存在")
        existing = await ProjectTaskCRUD(self.auth, self.db).get_list(search={"project_id": id, "task_id": data.task_id})
        if not existing:
            await ProjectTaskCRUD(self.auth, self.db).create(data={"project_id": id, "task_id": data.task_id})
        return ProjectOutSchema.model_validate(await ProjectCRUD(self.auth, self.db).get_or_404(id=id, preload=_PROJECT_PRELOAD))

    async def remove_task(self, id: int, task_id: int) -> ProjectOutSchema:
        """从项目移除任务归集。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id)
        existing = await ProjectTaskCRUD(self.auth, self.db).get_list(search={"project_id": id, "task_id": task_id})
        if existing:
            await ProjectTaskCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
        return await self.detail(id=id)

    async def change_status(self, id: int, data: ProjectStatusUpdateSchema) -> ProjectOutSchema:
        """项目状态单向流转：草稿 → 进行中 → 已完成 → 已关闭。"""
        project = await ProjectCRUD(self.auth, self.db).get_or_404(id=id)
        order = [
            ProjectStatus.DRAFT.value,
            ProjectStatus.IN_PROGRESS.value,
            ProjectStatus.COMPLETED.value,
            ProjectStatus.CLOSED.value,
        ]
        if project.status not in order:
            raise CustomException(msg="当前项目状态异常")
        if data.status not in order or order.index(data.status) <= order.index(project.status):
            raise CustomException(msg="项目状态只能单向流转(草稿→进行中→已完成→已关闭)")
        await ProjectCRUD(self.auth, self.db).update(id=id, data={"status": data.status})
        return await self.detail(id=id)

    async def _sync_task_links(self, project_id: int, task_ids: list[int]) -> None:
        """同步项目-任务归集关系（全量替换为传入的任务列表）。"""
        unique_ids = list(dict.fromkeys(task_ids))  # 去重并保持顺序
        for tid in unique_ids:
            await TaskCRUD(self.auth, self.db).get_or_404(id=tid, msg=f"任务[{tid}]不存在")
        existing = await ProjectTaskCRUD(self.auth, self.db).get_list(search={"project_id": project_id})
        if existing:
            await ProjectTaskCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
        for tid in unique_ids:
            await ProjectTaskCRUD(self.auth, self.db).create(data={"project_id": project_id, "task_id": tid})
