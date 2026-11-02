from datetime import UTC, datetime
from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.redis_crud import RedisCURD
from app.utils.common_util import search_to_dict

from ..enums import AssignMode, TaskKind, TaskStatus
from ..project.crud import ProjectCRUD, ProjectTaskCRUD
from .crud import TaskCRUD, TaskTypeCRUD
from .schema import (
    TaskCreateSchema,
    TaskOutSchema,
    TaskQueryParam,
    TaskTypeCreateSchema,
    TaskTypeOutSchema,
    TaskTypeQueryParam,
    TaskTypeUpdateSchema,
    TaskUpdateSchema,
)

# task_type 为 UserBySchema（含 created_by/updated_by），必须嵌套预加载其审计关系，
# 避免 detail()/page() 序列化时在异步环境下触发懒加载 MissingGreenlet
_TASK_PRELOAD = [
    "task_type",
    "task_type.created_by",
    "task_type.updated_by",
    "project_links",
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
        """创建任务（草稿状态），并归集到指定项目。"""
        if await TaskCRUD(self.auth, self.db).get(task_no=data.task_no):
            raise CustomException(msg="已存在相同任务号的任务")
        task_type = await TaskTypeCRUD(self.auth, self.db).get_or_404(id=data.task_type_id, msg="任务类型模板不存在")

        # 任务分类缺省取模板默认；定额任务必须限定时间范围
        task_kind = data.task_kind or task_type.default_kind
        if task_kind == TaskKind.QUOTA.value and (data.exec_time_start is None or data.exec_time_end is None):
            raise CustomException(msg="定额任务必须设置限定时间范围")

        create_data = data.model_dump(exclude={"project_ids"})
        create_data["task_kind"] = task_kind
        if create_data.get("unit_price") is None:
            create_data["unit_price"] = float(task_type.default_price)
        task = await TaskCRUD(self.auth, self.db).create(data=create_data)

        # 任务归集到多个项目
        await self._sync_project_links(task.id, data.project_ids)
        return await self.detail(id=task.id)

    async def update(self, id: int, data: TaskUpdateSchema) -> TaskOutSchema:
        """更新任务（仅草稿状态可改）。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可修改")
        if data.task_no and (exist := await TaskCRUD(self.auth, self.db).get(task_no=data.task_no)) and exist.id != id:
            raise CustomException(msg="已存在相同任务号的任务")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"project_ids"})
        await TaskCRUD(self.auth, self.db).update(id=id, data=update_data)
        # 若提供了 project_ids，则全量替换归集关系
        if data.project_ids is not None:
            await self._sync_project_links(id, data.project_ids)
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

    async def publish(self, redis: Redis, id: int) -> TaskOutSchema:
        """发布任务：DRAFT → PUBLISHED。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可发布")
        # 定额任务发布时初始化 Redis 已接单数计数（防超卖）
        if task.task_kind == TaskKind.QUOTA.value:
            claim_key = f"{RedisInitKeyConfig.MARKET_TASK_CLAIM.key}:{id}"
            await RedisCURD(redis).set(key=claim_key, value="0", expire=None)
        update_data: dict[str, Any] = {"status": TaskStatus.PUBLISHED.value, "published_at": datetime.now(UTC)}
        await TaskCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def complete(self, id: int) -> TaskOutSchema:
        """判定任务完成（运营手动）：PUBLISHED / IN_PROGRESS → COMPLETED。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status not in {TaskStatus.PUBLISHED.value, TaskStatus.IN_PROGRESS.value}:
            raise CustomException(msg="仅已发布/进行中的任务可判定完成")
        await TaskCRUD(self.auth, self.db).update(
            id=id,
            data={"status": TaskStatus.COMPLETED.value, "completed_by": self.auth.user.id, "completed_at": datetime.now(UTC)},
        )
        return await self.detail(id=id)

    async def _sync_project_links(self, task_id: int, project_ids: list[int]) -> None:
        """同步任务-项目归集关系（全量替换为传入的项目列表）。"""
        unique_ids = list(dict.fromkeys(project_ids))  # 去重并保持顺序
        for pid in unique_ids:
            await ProjectCRUD(self.auth, self.db).get_or_404(id=pid, msg=f"项目[{pid}]不存在")
        existing = await ProjectTaskCRUD(self.auth, self.db).get_list(search={"task_id": task_id})
        if existing:
            await ProjectTaskCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
        for pid in unique_ids:
            await ProjectTaskCRUD(self.auth, self.db).create(data={"project_id": pid, "task_id": task_id})

    async def hall_task_detail(self, task_id: int, redis: Redis) -> TaskOutSchema:
        """任务大厅任务详情（C 端）。

        C 端不能走 `/market/tasks/detail`（要求 `module_market:task:query` 权限码），
        所以单独提供一个只读入口；可见范围与大厅列表严格一致：
        公开接单 + 已发布/进行中 + 未超出限定时间 + （定额任务）名额未满。
        """
        obj = await TaskCRUD(self.auth, self.db).get(id=task_id, preload=_TASK_PRELOAD)
        if (
            obj is None
            or obj.assign_mode != AssignMode.OPEN.value
            or obj.status not in {TaskStatus.PUBLISHED.value, TaskStatus.IN_PROGRESS.value}
            or (obj.exec_time_end is not None and obj.exec_time_end <= datetime.now(UTC))
        ):
            raise CustomException(msg="任务不存在或已下架")

        claim_key = f"{RedisInitKeyConfig.MARKET_TASK_CLAIM.key}:{obj.id}"
        raw = await RedisCURD(redis).get(claim_key)
        claimed = int(raw) if raw else 0
        if obj.task_kind == TaskKind.QUOTA.value and claimed >= obj.exec_qty:
            raise CustomException(msg="该任务名额已满")
        return TaskOutSchema.model_validate(obj).model_copy(update={"claimed_count": claimed})

    async def hall_tasks(self, redis: Redis, page_no: int, page_size: int) -> PageResultSchema[TaskOutSchema]:
        """任务大厅：公开接单任务列表（定额任务过滤已满份数，返回剩余份数）。"""
        # 公开任务量通常不大，一次取全量后按 Redis 计数过滤已满任务，再内存分页
        objs, _ = await TaskCRUD(self.auth, self.db).hall_page(offset=0, limit=10000, preload=_TASK_PRELOAD)
        claim_keys = [f"{RedisInitKeyConfig.MARKET_TASK_CLAIM.key}:{obj.id}" for obj in objs]
        raw_counts = await RedisCURD(redis).mget(claim_keys)
        avail: list[TaskOutSchema] = []
        for obj, raw in zip(objs, raw_counts, strict=False):
            claimed = int(raw) if raw else 0
            if obj.task_kind == TaskKind.QUOTA.value and claimed >= obj.exec_qty:
                continue  # 定额任务名额已接满，从大厅剔除
            out = TaskOutSchema.model_validate(obj).model_copy(update={"claimed_count": claimed})
            avail.append(out)
        total = len(avail)
        start = (page_no - 1) * page_size
        items = avail[start : start + page_size]
        return PageResultSchema(
            page_no=page_no,
            page_size=page_size,
            total=total,
            has_next=start + page_size < total,
            items=items,
        )
