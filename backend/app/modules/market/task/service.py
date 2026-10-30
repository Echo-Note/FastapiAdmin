"""任务管理域服务层。

任务两级层级（分类/模板）+ 任务实例 + 分派 + 成果提交的完整业务逻辑。
状态流转遵循 ``app.modules.market.enums`` 定义的状态机，单向流转由各 Service 显式约束。
"""

from datetime import UTC, datetime
from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.redis_crud import RedisCURD
from app.utils.common_util import search_to_dict

from ..config import TaskConfig, TaskItemConfig
from ..enums import AssignmentSource, AssignmentStatus, AssignMode, SubjectType, SubmissionStatus, TaskStatus
from ..institution.service import InstitutionService, extract_institution_info, map_institution_type
from ..numbering import NumberPrefix, next_code
from ..project.crud import ProjectCRUD
from .crud import AssignmentCRUD, SubmissionCRUD, TaskCategoryCRUD, TaskCRUD, TaskItemCRUD, TaskTemplateCRUD
from .model import AssignmentModel, TaskItemModel, TaskTemplateModel
from .schema import (
    AssignmentCreateSchema,
    AssignmentOutSchema,
    AssignmentQueryParam,
    AssignmentUpdateSchema,
    SubmissionCreateSchema,
    SubmissionOutSchema,
    SubmissionQueryParam,
    SubmissionReviewSchema,
    SubmissionUpdateSchema,
    TaskCategoryCreateSchema,
    TaskCategoryOutSchema,
    TaskCategoryQueryParam,
    TaskCategoryTreeSchema,
    TaskCategoryUpdateSchema,
    TaskCreateSchema,
    TaskItemCreateSchema,
    TaskItemOutSchema,
    TaskItemQueryParam,
    TaskItemTreeOutSchema,
    TaskItemUpdateSchema,
    TaskOutSchema,
    TaskQueryParam,
    TaskStatusUpdateSchema,
    TaskTemplateCreateSchema,
    TaskTemplateOutSchema,
    TaskTemplateQueryParam,
    TaskTemplateTreeOutSchema,
    TaskTemplateUpdateSchema,
    TaskUpdateSchema,
)

# 模板输出含 category + items（三级任务），需预加载其审计关系与子任务的审计关系
_TEMPLATE_PRELOAD = [
    "category",
    "category.created_by",
    "category.updated_by",
    "items",
    "items.created_by",
    "items.updated_by",
]

# 任务输出含 template（含 category + items），需预加载自身审计关系、两层关系及其审计关系
_TASK_PRELOAD = [
    "created_by",
    "updated_by",
    "template",
    "template.created_by",
    "template.updated_by",
    "template.category",
    "template.category.created_by",
    "template.category.updated_by",
    "template.items",
    "template.items.created_by",
    "template.items.updated_by",
]

# 分派输出含 task（复用任务预加载链，加 task. 前缀）
_ASSIGNMENT_PRELOAD = ["task", *[f"task.{p}" for p in _TASK_PRELOAD]]




class TaskCategoryService:
    """一级任务分类服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> TaskCategoryOutSchema:
        """查询一级分类详情。"""
        category = await TaskCategoryCRUD(self.auth, self.db).get_or_404(id=id)
        return TaskCategoryOutSchema.model_validate(category)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TaskCategoryQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TaskCategoryOutSchema]:
        """分页查询一级分类。"""
        offset = (page_no - 1) * page_size
        return await TaskCategoryCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"sort": "asc"}, {"id": "asc"}],
            search=search_to_dict(search),
            out_schema=TaskCategoryOutSchema,
        )

    async def create(self, data: TaskCategoryCreateSchema) -> TaskCategoryOutSchema:
        """创建一级分类（编号自动生成）。"""
        code = await next_code(self.db, NumberPrefix.CATEGORY)
        category = await TaskCategoryCRUD(self.auth, self.db).create(data={**data.model_dump(), "code": code})
        return await self.detail(id=category.id)

    async def update(self, id: int, data: TaskCategoryUpdateSchema) -> TaskCategoryOutSchema:
        """更新一级分类（编号不可修改）。"""
        await TaskCategoryCRUD(self.auth, self.db).get_or_404(id=id)
        await TaskCategoryCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除一级分类。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await TaskCategoryCRUD(self.auth, self.db).delete(ids=ids)

    async def tree(self) -> list[TaskCategoryTreeSchema]:
        """任务目录树：一级分类 + 其下二级模板（含三级任务）。"""
        categories = await TaskCategoryCRUD(self.auth, self.db).get_list(
            order_by=[{"sort": "asc"}, {"id": "asc"}]
        )
        result: list[TaskCategoryTreeSchema] = []
        for category in categories:
            templates = await TaskTemplateCRUD(self.auth, self.db).get_list(
                search={"category_id": category.id}, order_by=[{"id": "asc"}], preload=["items"]
            )
            node = TaskCategoryTreeSchema.model_validate(category)
            node.children = [self._template_tree_out(t, category.name) for t in templates]
            result.append(node)
        return result

    @staticmethod
    def _template_tree_out(template: TaskTemplateModel, category_name: str | None = None) -> TaskTemplateTreeOutSchema:
        """树形模板子节点序列化（config 用 ``TaskConfig`` 解析，items 用 ``TaskItemConfig`` 解析）。"""
        out = TaskTemplateTreeOutSchema.model_validate(template)
        out.config = TaskConfig.model_validate(template.config)
        out.category_name = category_name
        out.items = [TaskCategoryService._item_tree_out(i) for i in template.items]
        return out

    @staticmethod
    def _item_tree_out(item: TaskItemModel) -> TaskItemTreeOutSchema:
        """树形任务三级节点序列化（config 用 ``TaskItemConfig`` 解析）。"""
        out = TaskItemTreeOutSchema.model_validate(item)
        out.config = TaskItemConfig.model_validate(item.config)
        return out


class TaskTemplateService:
    """二级任务模板服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> TaskTemplateOutSchema:
        """查询二级模板详情，config 用 ``TaskConfig`` 解析，含其下三级任务。"""
        template = await TaskTemplateCRUD(self.auth, self.db).get_or_404(id=id, preload=_TEMPLATE_PRELOAD)
        out = TaskTemplateOutSchema.model_validate(template)
        out.config = TaskConfig.model_validate(template.config)
        out.items = [self._item_out(i) for i in template.items]
        return out

    @staticmethod
    def _item_out(item: TaskItemModel) -> TaskItemOutSchema:
        """三级任务序列化（config 用 ``TaskItemConfig`` 解析）。"""
        out = TaskItemOutSchema.model_validate(item)
        out.config = TaskItemConfig.model_validate(item.config)
        return out

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TaskTemplateQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TaskTemplateOutSchema]:
        """分页查询二级模板。"""
        offset = (page_no - 1) * page_size
        return await TaskTemplateCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=TaskTemplateOutSchema,
            preload=_TEMPLATE_PRELOAD,
        )

    async def create(self, data: TaskTemplateCreateSchema) -> TaskTemplateOutSchema:
        """创建二级模板（编号自动生成）。"""
        await TaskCategoryCRUD(self.auth, self.db).get_or_404(id=data.category_id, msg="一级分类不存在")
        create_data = data.model_dump()
        create_data["code"] = await next_code(self.db, NumberPrefix.TEMPLATE)
        create_data["config"] = data.config.model_dump(mode="json")
        template = await TaskTemplateCRUD(self.auth, self.db).create(data=create_data)
        return await self.detail(id=template.id)

    async def update(self, id: int, data: TaskTemplateUpdateSchema) -> TaskTemplateOutSchema:
        """更新二级模板（编号不可修改）。"""
        await TaskTemplateCRUD(self.auth, self.db).get_or_404(id=id)
        if data.category_id is not None:
            await TaskCategoryCRUD(self.auth, self.db).get_or_404(id=data.category_id, msg="一级分类不存在")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if data.config is not None:
            update_data["config"] = data.config.model_dump(mode="json")
        await TaskTemplateCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除二级模板。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await TaskTemplateCRUD(self.auth, self.db).delete(ids=ids)


class TaskItemService:
    """三级任务服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> TaskItemOutSchema:
        """查询三级任务详情，config 用 ``TaskItemConfig`` 解析。"""
        item = await TaskItemCRUD(self.auth, self.db).get_or_404(id=id)
        out = TaskItemOutSchema.model_validate(item)
        out.config = TaskItemConfig.model_validate(item.config)
        return out

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TaskItemQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TaskItemOutSchema]:
        """分页查询三级任务。"""
        offset = (page_no - 1) * page_size
        return await TaskItemCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"sort": "asc"}, {"id": "asc"}],
            search=search_to_dict(search),
            out_schema=TaskItemOutSchema,
        )

    async def create(self, data: TaskItemCreateSchema) -> TaskItemOutSchema:
        """创建三级任务（任务自包含完整采集分节，编号自动生成）。"""
        await TaskTemplateCRUD(self.auth, self.db).get_or_404(id=data.template_id, msg="二级模板不存在")
        create_data = data.model_dump()
        create_data["code"] = await next_code(self.db, NumberPrefix.ITEM)
        create_data["config"] = data.config.model_dump(mode="json")
        item = await TaskItemCRUD(self.auth, self.db).create(data=create_data)
        return await self.detail(id=item.id)

    async def update(self, id: int, data: TaskItemUpdateSchema) -> TaskItemOutSchema:
        """更新三级任务（任务自包含完整采集分节，不从模板继承）。"""
        await TaskItemCRUD(self.auth, self.db).get_or_404(id=id)
        if data.template_id is not None:
            await TaskTemplateCRUD(self.auth, self.db).get_or_404(id=data.template_id, msg="二级模板不存在")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if data.config is not None:
            update_data["config"] = data.config.model_dump(mode="json")
        await TaskItemCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除三级任务。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await TaskItemCRUD(self.auth, self.db).delete(ids=ids)


class TaskService:
    """任务实例服务"""

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
        """分页查询任务，并聚合各任务的已分派/接收人数。"""
        offset = (page_no - 1) * page_size
        result = await TaskCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=TaskOutSchema,
            preload=_TASK_PRELOAD,
        )
        await self._attach_assignment_counts(result)
        return result

    async def _attach_assignment_counts(self, result: PageResultSchema[TaskOutSchema]) -> None:
        """为任务分页结果回填 assignment_count（按 task_id 分组统计分派/接收记录数）。"""
        if not result.items:
            return
        task_ids = [item.id for item in result.items if item.id is not None]
        if not task_ids:
            return
        rows = await self.db.execute(
            select(AssignmentModel.task_id, func.count(AssignmentModel.id))
            .where(AssignmentModel.task_id.in_(task_ids))
            .group_by(AssignmentModel.task_id)
        )
        count_map: dict[int, int] = {int(task_id): int(cnt) for task_id, cnt in rows.all()}
        for item in result.items:
            if item.id is not None:
                item.assignment_count = count_map.get(item.id, 0)

    async def create(self, data: TaskCreateSchema) -> TaskOutSchema:
        """创建任务（草稿状态，编号自动生成）。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=data.project_id, msg="项目不存在")
        await TaskTemplateCRUD(self.auth, self.db).get_or_404(id=data.template_id, msg="任务模板不存在")
        task_no = await next_code(self.db, NumberPrefix.TASK)
        task = await TaskCRUD(self.auth, self.db).create(data={**data.model_dump(), "task_no": task_no})
        return await self.detail(id=task.id)

    async def update(self, id: int, data: TaskUpdateSchema) -> TaskOutSchema:
        """更新任务（仅草稿状态可改，编号不可修改）。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可修改")
        if data.project_id is not None:
            await ProjectCRUD(self.auth, self.db).get_or_404(id=data.project_id, msg="项目不存在")
        if data.template_id is not None:
            await TaskTemplateCRUD(self.auth, self.db).get_or_404(id=data.template_id, msg="任务模板不存在")
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

    async def publish(self, id: int) -> TaskOutSchema:
        """发布任务：DRAFT → PUBLISHED，写入发布人与发布时间。

        发布与分派解耦：发布仅做状态流转，不处理分派；定向分派由独立的分配动作
        （单个「添加分派」/ 列表「批量分配」）完成，分派时自动将任务改为 direct。
        """
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可发布")

        update_data: dict[str, Any] = {
            "status": TaskStatus.PUBLISHED.value,
            "publisher_id": self.auth.user.id,
            "published_at": datetime.now(UTC),
        }
        await TaskCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def batch_publish(self, ids: list[int]) -> dict[str, Any]:
        """批量发布任务：逐个发布（仅状态流转），单任务失败不影响其余，返回成功数与失败明细。"""
        published = 0
        failed: list[dict[str, Any]] = []
        for task_id in dict.fromkeys(ids):
            try:
                await self.publish(id=task_id)
                published += 1
            except CustomException as exc:
                failed.append({"id": task_id, "msg": exc.msg})
        return {"published": published, "failed": failed}

    async def change_status(self, id: int, data: TaskStatusUpdateSchema) -> TaskOutSchema:
        """任务状态单向流转：PUBLISHED → IN_PROGRESS → COMPLETED → SETTLED → ARCHIVED。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        order = [
            TaskStatus.PUBLISHED.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.COMPLETED.value,
            TaskStatus.SETTLED.value,
            TaskStatus.ARCHIVED.value,
        ]
        if task.status not in order:
            raise CustomException(msg="当前任务状态异常")
        if data.status not in order or order.index(data.status) <= order.index(task.status):
            raise CustomException(msg="任务状态只能单向流转(发布→进行中→已完成→已结算→归档)")
        await TaskCRUD(self.auth, self.db).update(id=id, data={"status": data.status})
        return await self.detail(id=id)

    async def hall_tasks(self, redis: Redis, page_no: int, page_size: int) -> PageResultSchema[TaskOutSchema]:
        """任务大厅：status=PUBLISHED 且 assign_mode=open、且当前用户未领取的任务列表。

        按用户隔离：某用户领取（claimed）后，仅该用户的大厅不再展示此任务，
        其他用户的大厅仍正常展示（任务本身仍为 open，可被其他人领取）。

        参数 ``redis`` 为接口预留（C 端大厅调用方统一传入），当前大厅过滤为纯数据库查询，
        接单计数走 ``AssignmentService.claim`` 的 Redis 计数器。
        """
        del redis  # 预留参数，当前未使用
        offset = (page_no - 1) * page_size
        # 当前用户已领取的任务 id 列表，大厅需排除这些任务
        claimed = await AssignmentCRUD(self.auth, self.db).get_list(
            search={"user_id": self.auth.user.id, "source": AssignmentSource.CLAIMED.value}
        )
        claimed_ids = [a.task_id for a in claimed]
        search = {
            "status": TaskStatus.PUBLISHED.value,
            "assign_mode": AssignMode.OPEN.value,
            "id": ("notin", claimed_ids),
        }
        return await TaskCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"published_at": "desc"}, {"id": "desc"}],
            search=search,
            out_schema=TaskOutSchema,
            preload=_TASK_PRELOAD,
        )


class AssignmentService:
    """任务分配/接收服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> AssignmentOutSchema:
        """查询分派详情（预加载任务链，避免异步懒加载）。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(id=id, preload=_ASSIGNMENT_PRELOAD)
        return AssignmentOutSchema.model_validate(assignment)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: AssignmentQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[AssignmentOutSchema]:
        """分页查询分派（预加载任务链）。"""
        offset = (page_no - 1) * page_size
        return await AssignmentCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=AssignmentOutSchema,
            preload=_ASSIGNMENT_PRELOAD,
        )

    async def create(self, data: AssignmentCreateSchema) -> list[AssignmentOutSchema]:
        """批量创建分派（运营定向分派，一个任务指派给多个用户，跳过已分派）。"""
        await TaskCRUD(self.auth, self.db).get_or_404(id=data.task_id, msg="任务不存在")
        return await self.batch_assign(task_id=data.task_id, user_ids=data.user_ids, source=data.source)

    async def batch_assign(self, task_id: int, user_ids: list[int], source: str) -> list[AssignmentOutSchema]:
        """批量创建分派记录：用户去重、跳过已分派，返回本次新建的分派列表。

        运营定向分派（``source=assigned``）时，自动将任务的分配方式改为 ``direct``，
        避免「已指定执行人但任务仍为公开大厅」的矛盾状态（大厅接单 ``claim`` 不走此方法）。
        """
        created: list[AssignmentOutSchema] = []
        if source == AssignmentSource.ASSIGNED.value:
            await TaskCRUD(self.auth, self.db).update(id=task_id, data={"assign_mode": AssignMode.DIRECT.value})
        for user_id in dict.fromkeys(user_ids):
            existing = await AssignmentCRUD(self.auth, self.db).get_list(
                search={"task_id": task_id, "user_id": user_id}
            )
            if existing:
                continue
            assignment = await AssignmentCRUD(self.auth, self.db).create(
                data={"task_id": task_id, "user_id": user_id, "source": source}
            )
            created.append(await self.detail(id=assignment.id))
        return created

    async def batch_assign_multi(self, task_ids: list[int], user_ids: list[int]) -> int:
        """批量分配：多任务 × 多用户交叉创建分派（跳过已存在），返回本次新建数量。"""
        created_count = 0
        for task_id in dict.fromkeys(task_ids):
            await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, msg="任务不存在")
            created = await self.batch_assign(
                task_id=task_id, user_ids=user_ids, source=AssignmentSource.ASSIGNED.value
            )
            created_count += len(created)
        return created_count

    async def update(self, id: int, data: AssignmentUpdateSchema) -> AssignmentOutSchema:
        """更新分派。"""
        await AssignmentCRUD(self.auth, self.db).get_or_404(id=id)
        await AssignmentCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除分派。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await AssignmentCRUD(self.auth, self.db).delete(ids=ids)

    async def my_assignments(
        self, page_no: int, page_size: int, search: AssignmentQueryParam | None = None
    ) -> PageResultSchema[AssignmentOutSchema]:
        """我的任务：按当前登录用户过滤的分派列表。"""
        offset = (page_no - 1) * page_size
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        return await AssignmentCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"id": "desc"}],
            search=cond,
            out_schema=AssignmentOutSchema,
            preload=_ASSIGNMENT_PRELOAD,
        )

    async def accept(self, id: int) -> AssignmentOutSchema:
        """接收任务：PENDING → ACCEPTED，写入接收时间。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(id=id)
        if assignment.status != "PENDING":
            raise CustomException(msg="仅待接收状态的任务可接收")
        await AssignmentCRUD(self.auth, self.db).update(id=id, data={"status": "ACCEPTED", "accepted_at": datetime.now(UTC)})
        return await self.detail(id=id)

    async def claim(self, task_id: int, redis: Redis) -> AssignmentOutSchema:
        """大厅接单：为当前用户生成 claimed 分派，幂等防重。

        用户主动接单即视为「已接收」，分派直接置为 ``ACCEPTED`` 并写入接收时间
        （区别于运营定向分派 assigned 的 ``PENDING`` 待接收，需用户再确认接收）。

        接单不改动任务的分配方式（任务仍为公开大厅，其他用户仍可在大厅看到并接单），
        仅对当前用户隐藏该任务——大厅查询按「当前用户是否已领取」过滤。
        """
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, msg="任务不存在")
        if task.assign_mode != AssignMode.OPEN.value:
            raise CustomException(msg="该任务不是公开大厅任务，不可接单")
        if task.status != TaskStatus.PUBLISHED.value:
            raise CustomException(msg="仅已发布的任务可接单")
        existing = await AssignmentCRUD(self.auth, self.db).get_list(
            search={"task_id": task_id, "user_id": self.auth.user.id, "source": AssignmentSource.CLAIMED.value}
        )
        if existing:
            return await self.detail(id=existing[0].id)
        assignment = await AssignmentCRUD(self.auth, self.db).create(
            data={
                "task_id": task_id,
                "user_id": self.auth.user.id,
                "source": AssignmentSource.CLAIMED.value,
                "status": AssignmentStatus.ACCEPTED.value,
                "accepted_at": datetime.now(UTC),
            }
        )
        claim_key = f"{RedisInitKeyConfig.MARKET_TASK_CLAIM.key}:{task_id}"
        await RedisCURD(redis).incr(claim_key)
        return await self.detail(id=assignment.id)


class SubmissionService:
    """成果提交服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> SubmissionOutSchema:
        """查询成果详情。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id)
        return SubmissionOutSchema.model_validate(submission)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: SubmissionQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[SubmissionOutSchema]:
        """分页查询成果。"""
        offset = (page_no - 1) * page_size
        return await SubmissionCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=SubmissionOutSchema,
        )

    async def create(self, data: SubmissionCreateSchema) -> SubmissionOutSchema:
        """创建成果（草稿状态），并按模板采集对象类型归集机构。

        采集对象类型以任务模板 ``TaskConfig.subject_type`` 为准（前端传值仅作兜底）；
        当对象为机构时，从 ``form_data`` 提取机构名称/区域/等级，按模板名映射机构类型后
        归集机构（同名复用、否则创建），回填 ``institution_id``。运营端不再手动预置机构。
        """
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(
            id=data.assignment_id, msg="分配记录不存在", preload=["task", "task.template"]
        )
        template = assignment.task.template
        subject_type = (template.config or {}).get("subject_type", data.subject_type)

        create_data = data.model_dump()
        create_data["user_id"] = self.auth.user.id
        create_data["subject_type"] = subject_type

        if subject_type == SubjectType.INSTITUTION.value:
            info = extract_institution_info(data.form_data)
            institution_type = map_institution_type(template.name) if info else None
            if info and institution_type:
                create_data["institution_id"] = await InstitutionService(self.auth, self.db).collect(
                    name=info["name"],
                    institution_type=institution_type,
                    level=info.get("level") or None,
                    region=info.get("region") or None,
                )

        submission = await SubmissionCRUD(self.auth, self.db).create(data=create_data)
        return await self.detail(id=submission.id)

    async def update(self, id: int, data: SubmissionUpdateSchema) -> SubmissionOutSchema:
        """更新成果（草稿/驳回状态可改，驳回重提版本 +1）。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id)
        if submission.status not in {SubmissionStatus.DRAFT.value, SubmissionStatus.REJECTED.value}:
            raise CustomException(msg="仅草稿/驳回状态的成果可修改")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if submission.status == SubmissionStatus.REJECTED.value:
            update_data["version"] = submission.version + 1
            update_data["status"] = SubmissionStatus.DRAFT.value
        await SubmissionCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除成果。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await SubmissionCRUD(self.auth, self.db).delete(ids=ids)

    async def my_submissions(
        self, page_no: int, page_size: int, search: SubmissionQueryParam | None = None
    ) -> PageResultSchema[SubmissionOutSchema]:
        """我的成果：按当前登录用户过滤的成果列表。"""
        offset = (page_no - 1) * page_size
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        return await SubmissionCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"id": "desc"}],
            search=cond,
            out_schema=SubmissionOutSchema,
        )

    async def review(self, id: int, data: SubmissionReviewSchema) -> SubmissionOutSchema:
        """审核成果：approved→APPROVED，否则 REJECTED+review_comment，回写 assignment.status。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id)
        if submission.status not in {SubmissionStatus.DRAFT.value, SubmissionStatus.PENDING.value}:
            raise CustomException(msg="仅待审核状态的成果可审核")
        if data.approved:
            update_data: dict[str, Any] = {"status": SubmissionStatus.APPROVED.value}
        else:
            update_data = {
                "status": SubmissionStatus.REJECTED.value,
                "review_comment": data.review_comment,
            }
        update_data.update(
            {
                "reviewer_id": self.auth.user.id,
                "reviewed_at": datetime.now(UTC),
            }
        )
        await SubmissionCRUD(self.auth, self.db).update(id=id, data=update_data)
        # 回写分派状态：通过→SUBMITTED，驳回→SUBMITTED（保留已提交，允许重提）
        if data.approved:
            await AssignmentCRUD(self.auth, self.db).update(
                id=submission.assignment_id,
                data={"status": "SUBMITTED", "submitted_at": datetime.now(UTC)},
            )
        return await self.detail(id=id)
