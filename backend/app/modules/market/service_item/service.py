from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..company.crud import CompanyCRUD
from ..task.crud import TaskTypeCRUD
from .crud import ServiceItemCRUD, ServiceItemTaskCRUD
from .schema import ServiceItemCreateSchema, ServiceItemOutSchema, ServiceItemQueryParam, ServiceItemUpdateSchema

# 映射 task_type_links 需预加载（detail/page 序列化 task_type_ids 时避免异步懒加载 MissingGreenlet）；
# company 为 UserBySchema，须嵌套预加载其审计关系
_SERVICE_ITEM_PRELOAD = ["task_type_links", "company", "company.created_by", "company.updated_by"]


class ServiceItemService:
    """对外服务项目价目服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> ServiceItemOutSchema:
        """查询对外服务项目价目详情。"""
        item = await ServiceItemCRUD(self.auth, self.db).get_or_404(id=id, preload=_SERVICE_ITEM_PRELOAD)
        return ServiceItemOutSchema.model_validate(item)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: ServiceItemQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ServiceItemOutSchema]:
        """分页查询对外服务项目价目。"""
        offset = (page_no - 1) * page_size
        return await ServiceItemCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"service_no": "asc"}],
            search=search_to_dict(search),
            out_schema=ServiceItemOutSchema,
            preload=_SERVICE_ITEM_PRELOAD,
        )

    async def create(self, data: ServiceItemCreateSchema) -> ServiceItemOutSchema:
        """创建对外服务项目价目，并建立对内任务映射。"""
        if await ServiceItemCRUD(self.auth, self.db).get(code=data.code):
            raise CustomException(msg="已存在相同编码的服务项目")
        if await ServiceItemCRUD(self.auth, self.db).get(service_no=data.service_no):
            raise CustomException(msg="已存在相同服务项目号的服务项目")
        if data.company_id:
            await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        item = await ServiceItemCRUD(self.auth, self.db).create(data=data.model_dump(exclude={"task_type_ids"}))
        await self._sync_task_type_links(item.id, data.task_type_ids)
        return await self.detail(id=item.id)

    async def update(self, id: int, data: ServiceItemUpdateSchema) -> ServiceItemOutSchema:
        """更新对外服务项目价目。"""
        await ServiceItemCRUD(self.auth, self.db).get_or_404(id=id)
        if data.code and (exist := await ServiceItemCRUD(self.auth, self.db).get(code=data.code)) and exist.id != id:
            raise CustomException(msg="已存在相同编码的服务项目")
        if data.service_no and (exist := await ServiceItemCRUD(self.auth, self.db).get(service_no=data.service_no)) and exist.id != id:
            raise CustomException(msg="已存在相同服务项目号的服务项目")
        if data.company_id:
            await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"task_type_ids"})
        await ServiceItemCRUD(self.auth, self.db).update(id=id, data=update_data)
        if data.task_type_ids is not None:
            await self._sync_task_type_links(id, data.task_type_ids)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除对外服务项目价目。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await ServiceItemCRUD(self.auth, self.db).delete(ids=ids)

    async def _sync_task_type_links(self, service_item_id: int, task_type_ids: list[int]) -> None:
        """同步服务项目-任务类型映射（全量替换为传入的任务类型列表）。"""
        unique_ids = list(dict.fromkeys(task_type_ids))
        for tt_id in unique_ids:
            await TaskTypeCRUD(self.auth, self.db).get_or_404(id=tt_id, msg=f"任务类型[{tt_id}]不存在")
        existing = await ServiceItemTaskCRUD(self.auth, self.db).get_list(search={"service_item_id": service_item_id})
        if existing:
            await ServiceItemTaskCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
        for tt_id in unique_ids:
            await ServiceItemTaskCRUD(self.auth, self.db).create(data={"service_item_id": service_item_id, "task_type_id": tt_id})
