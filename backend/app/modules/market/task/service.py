"""任务管理域服务层。

任务两级层级（分类/模板）+ 任务实例 + 分派 + 成果提交的完整业务逻辑。
状态流转遵循 ``app.modules.market.enums`` 定义的状态机，单向流转由各 Service 显式约束。
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from redis.asyncio.client import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.redis_crud import RedisCURD
from app.utils.common_util import search_to_dict

from ..config import TaskConfig, TaskItemConfig
from ..enums import (
    AssignmentSource,
    AssignmentStatus,
    AssignMode,
    ProjectStatus,
    SubjectType,
    SubmissionStatus,
    SubmitCadence,
    TaskStatus,
)
from ..form_schema import FormSchemaSection
from ..institution.service import InstitutionService, extract_institution_info, map_institution_type
from ..numbering import NumberPrefix, next_code
from ..payout.crud import SettlementCRUD
from ..payout.service import PayoutService, SettlementService
from ..product.service import ProductService
from ..project.crud import ProjectCRUD
from ..project.model import ProjectItemModel, ProjectModel
from .crud import AssignmentCRUD, SubmissionCRUD, TaskCategoryCRUD, TaskCRUD, TaskItemCRUD, TaskTemplateCRUD
from .model import AssignmentModel, SubmissionModel, TaskItemModel, TaskModel, TaskTemplateModel
from .schema import (
    AssignmentCreateSchema,
    AssignmentOutSchema,
    AssignmentQueryParam,
    AssignmentUpdateSchema,
    CatalogUsageSchema,
    MiniAssignmentGroupSchema,
    MiniTaskGroupSchema,
    MyAssignmentStatsOutSchema,
    MyWeekProgressOutSchema,
    SubmissionCreateSchema,
    SubmissionOutSchema,
    SubmissionQueryParam,
    SubmissionReviewResultSchema,
    SubmissionReviewSchema,
    SubmissionSettlementNoticeSchema,
    SubmissionTaskContextSchema,
    SubmissionUpdateSchema,
    TaskCategoryCreateSchema,
    TaskCategoryOutSchema,
    TaskCategoryQueryParam,
    TaskCategoryTreeSchema,
    TaskCategoryUpdateSchema,
    TaskCreateSchema,
    TaskFacetSchema,
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

# 任务输出含 template（含 category + items）与 item（三级任务），需预加载自身审计关系、
# 各层关系及其审计关系
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
    "item",
    "item.created_by",
    "item.updated_by",
    "project",
]

# 分派输出含 task（复用任务预加载链，加 task. 前缀）
_ASSIGNMENT_PRELOAD = ["task", *[f"task.{p}" for p in _TASK_PRELOAD]]




def _resolve_form_schema(task: TaskModel) -> list[dict[str, Any]] | None:
    """取任务自带的采集表单结构：三级任务优先，叶子模板回退到模板配置。

    :param task: 任务实例（需已预加载 ``item`` 与 ``template``）
    :return: ``form_schema`` 分节列表；未配置时返回 None
    """
    if task.item is not None and isinstance(task.item.config, dict):
        schema = task.item.config.get("form_schema")
        if schema:
            return schema
    if isinstance(task.template.config, dict):
        return task.template.config.get("form_schema")
    return None


# 成果对象名称候选字段（机构：hospital_name/org_name；个人：受访对象 respondent；会议：会议名）
_SUBJECT_NAME_FIELDS: tuple[str, ...] = ("meeting_name", "subject_name", "respondent", "staff_name", "patient_name", "name")

# 成果列表/详情都要展示任务上下文（项目/分类/模板/任务）与机构摘要
_SUBMISSION_PRELOAD = [
    "institution",
    "assignment.task",
    "assignment.task.project",
    "assignment.task.item",
    "assignment.task.template",
    "assignment.task.template.category",
]


def _find_form_value(form_data: dict[str, Any] | None, keys: tuple[str, ...]) -> str:
    """跨分节按字段名取 ``form_data`` 里第一个非空标量值，未命中返回空串。

    :param form_data: 按分节 code 嵌套的采集表单数据
    :param keys: 候选字段名（按优先级）
    :return: 去空白后的文本值；无匹配返回 ``""``
    """
    for section in (form_data or {}).values():
        if not isinstance(section, dict):
            continue
        for key in keys:
            value = section.get(key)
            if isinstance(value, str | int | float) and str(value).strip():
                return str(value).strip()
    return ""


def _submission_display_fields(form_data: dict[str, Any] | None, subject_type: str) -> dict[str, str]:
    """从采集表单推导成果摘要字段（对象名称 / 区域）。

    C 端提交只传 ``form_data``，成果表的 ``subject_name`` / ``region`` 两列曾经无人赋值，
    导致审核页永远空白。提交时由本函数提取写入，存量数据在详情接口自愈回填。
    机构对象取机构名称（采集表里是 ``hospital_name`` / ``org_name``），其余对象类型取
    会议名/受访对象名等候选字段。

    :param form_data: 按分节 code 嵌套的采集表单数据
    :param subject_type: 采集对象类型（见 ``SubjectType``）
    :return: 含 ``subject_name`` / ``region`` 的字典（未命中为空串）
    """
    info = extract_institution_info(form_data or {}) if subject_type == SubjectType.INSTITUTION.value else None
    name = info["name"] if info else _find_form_value(form_data, _SUBJECT_NAME_FIELDS)
    region = (info["region"] if info else "") or _find_form_value(form_data, ("region",))
    return {"subject_name": name, "region": region}


def _resolve_form_schema_sections(task: TaskModel) -> list[FormSchemaSection] | None:
    """把任务自带的 ``form_schema`` 强类型化，供前端把 ``form_data`` 的字段名渲染成中文标签。

    历史库里可能存在不符合当前 Pydantic 定义的旧 schema（如缺 ``label``），此时降级返回
    None——前端会回退到英文 key，不能因为一个存量任务让整个成果详情 500。

    :param task: 任务实例（需已预加载 ``item`` 与 ``template``）
    :return: 分节列表；未配置或不合规时返回 None
    """
    raw = _resolve_form_schema(task)
    if not raw:
        return None
    try:
        return [FormSchemaSection.model_validate(section) for section in raw]
    except ValidationError:
        logger.warning(f"任务 {task.id} 的 form_schema 不合规，成果详情按字段名展示：{raw}")
        return None


def _task_context(task: TaskModel) -> SubmissionTaskContextSchema:
    """把 ``assignment.task`` 升维成审核列表需要的扁平层级上下文（项目/分类/模板/任务）。

    :param task: 任务实例（需已预加载 ``project`` / ``item`` / ``template.category``）
    :return: 扁平的任务上下文 Schema
    """
    template = task.template
    category = template.category
    return SubmissionTaskContextSchema(
        id=task.id,
        task_no=task.task_no,
        name=task.name,
        project_id=task.project_id,
        project_name=task.project.name,
        category_id=category.id,
        category_name=category.name,
        template_id=template.id,
        template_name=template.name,
        item_id=task.item_id,
        item_name=task.item.name if task.item else None,
    )


def _pop_task_filter(search: dict[str, Any], key: str) -> int | None:
    """从查询字典里摘出「任务层级」过滤值（它们不是成果表列，不能留给 ``_build_conditions``）。"""
    value = search.pop(key, None)
    return value[1] if isinstance(value, tuple) else value


def _apply_task_filter(search: dict[str, Any]) -> None:
    """把项目/模板/任务过滤改写为 ``assignment_id IN (子查询)``，现场修改 ``search``。

    成果表只存 ``assignment_id``，而项目/模板/任务是隔两层的外键，因此用一条子查询
    （``market_assignment JOIN market_task``）把层级条件下推给数据库，避免先取 id 再回传。
    """
    conditions = [
        (attr, _pop_task_filter(search, key))
        for key, attr in (
            ("project_id", TaskModel.project_id),
            ("template_id", TaskModel.template_id),
            ("item_id", TaskModel.item_id),
        )
    ]
    conditions = [(attr, value) for attr, value in conditions if value is not None]
    if not conditions:
        return
    stmt = select(AssignmentModel.id).join(TaskModel, AssignmentModel.task_id == TaskModel.id)
    for attr, value in conditions:
        stmt = stmt.where(attr == value)
    # 同时给了分配ID 时并进同一个子查询，否则子查询会盖掉分配ID 条件
    assignment_id = _pop_task_filter(search, "assignment_id")
    if assignment_id is not None:
        stmt = stmt.where(AssignmentModel.id == assignment_id)
    search["assignment_id"] = ("in", stmt)


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

    async def catalog_usage(self) -> CatalogUsageSchema:
        """统计目录里「已被项目引用」的三级任务与叶子模板 id。

        任务目录页默认只显示这些条目；未被引用的靠开关展示，避免刚建的库里
        目录树里一堆没有任何项目在用的条目。
        """
        stmt = (
            select(ProjectItemModel.item_id, ProjectItemModel.template_id)
            .join(ProjectModel, ProjectModel.id == ProjectItemModel.project_id)
            .where(ProjectModel.is_deleted.is_(False))
        )
        rows = (await self.db.execute(stmt)).all()
        item_ids = sorted({item_id for item_id, _ in rows if item_id is not None})
        template_ids = sorted({template_id for _, template_id in rows if template_id is not None})
        return CatalogUsageSchema(item_ids=item_ids, template_ids=template_ids)

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

    @staticmethod
    def _fill_task_exec_fields(out: TaskOutSchema) -> None:
        """回填最小单元任务的执行标准/执行要求。

        取值优先级：三级任务 ``item.config`` 覆盖模板 ``template.config``；
        三级任务未配置时回退模板配置。
        """
        item = out.item
        template = out.template
        item_standard = item.config.exec_standard if item and item.config else None
        item_requirement = item.config.executor_requirement if item and item.config else None
        template_standard = template.config.exec_standard if template and template.config else None
        template_requirement = template.config.executor_requirement if template and template.config else None
        out.exec_standard = item_standard if item_standard is not None else template_standard
        out.executor_requirement = item_requirement if item_requirement is not None else template_requirement

    @staticmethod
    def _task_out(task: TaskModel) -> TaskOutSchema:
        """序列化任务实例为出参并回填执行字段。"""
        out = TaskOutSchema.model_validate(task)
        TaskService._fill_task_exec_fields(out)
        return out

    @staticmethod
    def _task_orm_sort_key(task: TaskModel) -> tuple[int, ...]:
        """分组内最小单元任务排序键：分类 sort/id → 模板 id → 三级任务 sort/id。"""
        category = task.template.category if task.template else None
        item = task.item
        return (
            task.project_id,
            category.sort if category else 0,
            category.id if category else 0,
            task.template.id if task.template else 0,
            item.sort if item else 0,
            item.id if item else 0,
        )

    @staticmethod
    def _group_orm_tasks(tasks: Sequence[TaskModel]) -> list[MiniTaskGroupSchema]:
        """按项目分组最小单元任务。

        项目按 ``project_id`` 升序出现，组内任务按分类/模板/三级任务排序。
        """
        ordered = sorted(tasks, key=TaskService._task_orm_sort_key)
        groups: dict[int, MiniTaskGroupSchema] = {}
        for task in ordered:
            project = task.project
            group = groups.get(task.project_id)
            if group is None:
                group = MiniTaskGroupSchema(
                    project_id=task.project_id,
                    project_name=project.name if project else "",
                    period=project.period if project else None,
                )
                groups[task.project_id] = group
            group.tasks.append(TaskService._task_out(task))
        return list(groups.values())

    async def detail(self, id: int) -> TaskOutSchema:
        """查询任务详情。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id, preload=_TASK_PRELOAD)
        out = TaskOutSchema.model_validate(task)
        self._fill_task_exec_fields(out)
        return out

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TaskQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TaskOutSchema]:
        """分页查询任务，并聚合各任务的已分派/接收人数。

        任务实例无 ``category_id`` 字段，一级分类过滤需转为「该分类下模板 id 的 in 查询」。
        """
        offset = (page_no - 1) * page_size
        search_dict = search_to_dict(search) or {}
        if search is not None:
            search_dict.pop("include_closed_project", None)

        # category_id → template_id in
        if search is not None and search.category_id is not None:
            search_dict.pop("category_id", None)
            templates = await TaskTemplateCRUD(self.auth, self.db).get_list(search={"category_id": search.category_id})
            template_ids = [t.id for t in templates]
            if not template_ids:
                return PageResultSchema[TaskOutSchema](page_no=page_no, page_size=page_size, total=0, has_next=False, items=[])
            search_dict["template_id"] = ("in", template_ids)

        # exclude_status → status notin（未显式指定 status 时排除草稿；字符串须包成 list 供 SQLAlchemy notin 使用）
        if search is not None and search.exclude_status:
            exclude_val = search.exclude_status
            search_dict.pop("exclude_status", None)
            if "status" not in search_dict:
                search_dict["status"] = ("notin", [exclude_val])

        # 非活跃项目（已关闭 / 已删除）的任务默认不出现在任务列表：项目都结束了，任务还能被接单/分派是错的。
        # 注意不能直接覆写 search_dict["project_id"]——那是调用方显式指定的过滤条件，
        # 覆写会把「按项目查」变成「查所有活跃项目」，因此显式指定时改为判定该投影是否非活跃。
        if search is None or not search.include_closed_project:
            inactive = await self._inactive_project_ids()
            if "project_id" in search_dict:
                # 显式按项目过滤：值可能是 ("eq", 6) 形式的元组，取出其中的项目 id 判定是否非活跃
                cond = search_dict["project_id"]
                raw = cond[1] if isinstance(cond, tuple) else cond
                values = raw if isinstance(raw, list) else [raw]
                if any(isinstance(v, int) and v in inactive for v in values):
                    return PageResultSchema[TaskOutSchema](
                        page_no=page_no, page_size=page_size, total=0, has_next=False, items=[]
                    )
            elif inactive:
                search_dict["project_id"] = ("notin", inactive)

        result = await TaskCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_dict,
            out_schema=TaskOutSchema,
            preload=_TASK_PRELOAD,
        )
        for item in result.items:
            self._fill_task_exec_fields(item)
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

    async def _get_leaf_template(self, template_id: int) -> TaskTemplateModel:
        """查询并校验叶子模板：仅「无三级任务」的模板允许直接建任务。

        有三级任务的模板不承载 ``form_schema``（表单结构完全由三级任务自包含），
        若按模板级创建任务，C 端将无任何采集字段可填，故在此强校验拦截。
        """
        template = await TaskTemplateCRUD(self.auth, self.db).get_or_404(
            id=template_id, msg="叶子模板不存在", preload=["items"]
        )
        if template.items:
            raise CustomException(
                msg=f"模板[{template.name}]含 {len(template.items)} 个三级任务，请按三级任务创建任务"
            )
        return template

    async def facets(self) -> list[TaskFacetSchema]:
        """任务目录侧边栏的「已用目录」统计。

        只返回**确实有任务实例**的（分类, 模板）组合及其任务数，供前端构建侧边栏时
        隐藏「目录里有、但一个任务都没有」的模板——否则新建库/空库时侧边栏会显示
        一整棵没有任何任务对应的目录树。
        """
        conditions = [TaskModel.is_deleted.is_(False)]
        inactive = await self._inactive_project_ids()
        if inactive:
            conditions.append(TaskModel.project_id.notin_(inactive))
        stmt = (
            select(TaskTemplateModel.category_id, TaskModel.template_id, func.count(TaskModel.id))
            .join(TaskTemplateModel, TaskTemplateModel.id == TaskModel.template_id)
            .where(*conditions)
            .group_by(TaskTemplateModel.category_id, TaskModel.template_id)
            .order_by(TaskTemplateModel.category_id, TaskModel.template_id)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            TaskFacetSchema(category_id=category_id, template_id=template_id, task_count=count)
            for category_id, template_id, count in rows
        ]

    async def create(self, data: TaskCreateSchema) -> TaskOutSchema:
        """创建任务（草稿状态，编号自动生成，名称 = 项目-二级模板[-三级任务]）。"""
        project = await ProjectCRUD(self.auth, self.db).get_or_404(id=data.project_id, msg="项目不存在")
        task_no = await next_code(self.db, NumberPrefix.TASK)
        if data.item_id is not None:
            item = await TaskItemCRUD(self.auth, self.db).get_or_404(id=data.item_id, msg="三级任务不存在", preload=["template"])
            create_data = {
                "task_no": task_no,
                "project_id": data.project_id,
                "template_id": item.template_id,
                "item_id": item.id,
                "name": f"{project.name}-{item.template.name}-{item.name}",
                "period": data.period,
                "assign_mode": data.assign_mode,
            }
        else:
            template = await self._get_leaf_template(data.template_id)
            create_data = {
                "task_no": task_no,
                "project_id": data.project_id,
                "template_id": template.id,
                "item_id": None,
                "name": f"{project.name}-{template.name}",
                "period": data.period,
                "assign_mode": data.assign_mode,
            }
        task = await TaskCRUD(self.auth, self.db).create(data=create_data)
        return await self.detail(id=task.id)

    async def update(self, id: int, data: TaskUpdateSchema) -> TaskOutSchema:
        """更新任务（仅草稿状态可改，编号不可修改；项目/任务单元变更时同步模板与名称）。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=id)
        if task.status != TaskStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的任务可修改")

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        # 项目或任务单元（三级任务/叶子模板）变更时，同步派生的二级模板与显示名
        if data.item_id is not None or data.template_id is not None or data.project_id is not None:
            project_id = data.project_id if data.project_id is not None else task.project_id
            project = await ProjectCRUD(self.auth, self.db).get_or_404(id=project_id, msg="项目不存在")
            if data.item_id is not None:
                item = await TaskItemCRUD(self.auth, self.db).get_or_404(id=data.item_id, msg="三级任务不存在", preload=["template"])
                update_data["template_id"] = item.template_id
                update_data["item_id"] = item.id
                update_data["name"] = f"{project.name}-{item.template.name}-{item.name}"
            elif data.template_id is not None:
                template = await self._get_leaf_template(data.template_id)
                update_data["template_id"] = template.id
                update_data["item_id"] = None
                update_data["name"] = f"{project.name}-{template.name}"

        await TaskCRUD(self.auth, self.db).update(id=id, data=update_data)
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
        search = await self._hall_visibility_search()
        result = await TaskCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"published_at": "desc"}, {"id": "desc"}],
            search=search,
            out_schema=TaskOutSchema,
            preload=_TASK_PRELOAD,
        )
        for item in result.items:
            self._fill_task_exec_fields(item)
        return result

    async def _hall_visibility_search(self) -> dict[str, Any]:
        """任务大厅可见性过滤条件：PUBLISHED + open + 排除已领取 + 排除已关闭/已删除项目的任务。"""
        claimed = await AssignmentCRUD(self.auth, self.db).get_list(
            search={"user_id": self.auth.user.id, "source": AssignmentSource.CLAIMED.value}
        )
        claimed_ids = [a.task_id for a in claimed]
        search: dict[str, Any] = {
            "status": TaskStatus.PUBLISHED.value,
            "assign_mode": AssignMode.OPEN.value,
            "id": ("notin", claimed_ids),
        }
        inactive = await self._inactive_project_ids()
        if inactive:
            search["project_id"] = ("notin", inactive)
        return search

    async def _inactive_project_ids(self) -> list[int]:
        """取「非活跃项目」id：已关闭（CLOSED）或已软删除。

        项目的生命周期结束后，其下任务不应再出现在任务列表/大厅/目录统计里；
        数据保留在库里以便追溯。
        """
        rows = await self.db.execute(
            select(ProjectModel.id).where(
                or_(ProjectModel.status == ProjectStatus.CLOSED.value, ProjectModel.is_deleted.is_(True))
            )
        )
        return list(rows.scalars().all())

    async def grouped_hall_tasks(self) -> list[MiniTaskGroupSchema]:
        """任务大厅分组：复用大厅可见性，一次性查出全部可见任务并按项目分组。"""
        search = await self._hall_visibility_search()
        tasks = await TaskCRUD(self.auth, self.db).get_list(search=search, preload=_TASK_PRELOAD)
        return self._group_orm_tasks(tasks)


class AssignmentService:
    """任务分配/接收服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> AssignmentOutSchema:
        """查询分派详情（预加载任务链，避免异步懒加载）。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(id=id, preload=_ASSIGNMENT_PRELOAD)
        out = AssignmentOutSchema.model_validate(assignment)
        if out.task is not None:
            TaskService._fill_task_exec_fields(out.task)
        return out

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: AssignmentQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[AssignmentOutSchema]:
        """分页查询分派（预加载任务链）。"""
        offset = (page_no - 1) * page_size
        result = await AssignmentCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=AssignmentOutSchema,
            preload=_ASSIGNMENT_PRELOAD,
        )
        for item in result.items:
            if item.task is not None:
                TaskService._fill_task_exec_fields(item.task)
        return result

    async def create(self, data: AssignmentCreateSchema) -> list[AssignmentOutSchema]:
        """批量创建分派（运营定向分派，一个任务指派给多个用户，跳过已分派）。"""
        await TaskCRUD(self.auth, self.db).get_or_404(id=data.task_id, msg="任务不存在")
        return await self.batch_assign(task_id=data.task_id, user_ids=data.user_ids, source=data.source)

    async def batch_assign(self, task_id: int, user_ids: list[int], source: str) -> list[AssignmentOutSchema]:
        """批量创建分派记录：用户去重、跳过已分派，返回本次新建的分派列表。

        运营定向分派（``source=assigned``）时：

        - 任务的分配方式改为 ``direct``，避免「已指定执行人但任务仍为公开大厅」的矛盾状态；
        - 草稿任务一并置为 ``PUBLISHED``（写发布人与时间）——「指定了执行人」本身就是上线信号，
          否则被指派人能看到的却是一个未发布的任务，任务状态与实际执行脱节。

        大厅接单（``claim``）不走本方法。不需要定向分派的任务仍由运营显式「发布」进大厅。
        """
        created: list[AssignmentOutSchema] = []
        if source == AssignmentSource.ASSIGNED.value:
            update_data: dict[str, Any] = {"assign_mode": AssignMode.DIRECT.value}
            task = await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, msg="任务不存在")
            if task.status == TaskStatus.DRAFT.value:
                update_data.update(
                    {
                        "status": TaskStatus.PUBLISHED.value,
                        "publisher_id": self.auth.user.id,
                        "published_at": datetime.now(UTC),
                    }
                )
            await TaskCRUD(self.auth, self.db).update(id=task_id, data=update_data)
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

    async def my_stats(self) -> MyAssignmentStatsOutSchema:
        """我的待办计数（C 端角标）：分派状态分组 + 被驳回成果数。

        角标只需数字，所以不拉列表：一次 group by 拿各状态计数，再单独数一次被驳回成果。
        """
        status_stmt = (
            select(AssignmentModel.status, func.count(AssignmentModel.id))
            .where(AssignmentModel.user_id == self.auth.user.id, AssignmentModel.is_deleted.is_(False))
            .group_by(AssignmentModel.status)
        )
        counts: dict[str, int] = {}
        for status, count in (await self.db.execute(status_stmt)).all():
            counts[status] = int(count)

        rejected = await self.db.scalar(
            select(func.count(SubmissionModel.id)).where(
                SubmissionModel.user_id == self.auth.user.id,
                SubmissionModel.status == SubmissionStatus.REJECTED.value,
                SubmissionModel.is_deleted.is_(False),
            )
        )
        return MyAssignmentStatsOutSchema(
            pending=counts.get(AssignmentStatus.PENDING.value, 0),
            accepted=counts.get(AssignmentStatus.ACCEPTED.value, 0),
            submitted=counts.get(AssignmentStatus.SUBMITTED.value, 0),
            reviewed=counts.get(AssignmentStatus.REVIEWED.value, 0),
            settled=counts.get(AssignmentStatus.SETTLED.value, 0),
            rejected_submissions=int(rejected or 0),
        )

    async def my_week_progress(self) -> MyWeekProgressOutSchema:
        """本周进度（工作台顶部进度带）：截止日在本周的分派中，交付了多少。

        以「任务截止日期」而不是「成果提交时间」为准：C 端关心的是「这周该交的活交了没」，
        迟交的成果仍属于本周应完成的事，否则逾期会被悄悄算成「本周无任务」。
        """
        today = datetime.now(UTC).date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        async def count(statuses: tuple[str, ...] | None = None) -> int:
            stmt = (
                select(func.count(AssignmentModel.id))
                .select_from(AssignmentModel)
                .join(TaskModel, TaskModel.id == AssignmentModel.task_id)
                .where(
                    AssignmentModel.user_id == self.auth.user.id,
                    AssignmentModel.is_deleted.is_(False),
                    TaskModel.period >= week_start,
                    TaskModel.period <= week_end,
                )
            )
            if statuses:
                stmt = stmt.where(AssignmentModel.status.in_(statuses))
            return int((await self.db.scalar(stmt)) or 0)

        return MyWeekProgressOutSchema(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            due=await count(),
            done=await count(
                (AssignmentStatus.SUBMITTED.value, AssignmentStatus.REVIEWED.value, AssignmentStatus.SETTLED.value)
            ),
            approved=await count((AssignmentStatus.REVIEWED.value, AssignmentStatus.SETTLED.value)),
        )

    async def my_assignments(
        self, page_no: int, page_size: int, search: AssignmentQueryParam | None = None
    ) -> PageResultSchema[AssignmentOutSchema]:
        """我的任务：按当前登录用户过滤的分派列表。"""
        offset = (page_no - 1) * page_size
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        result = await AssignmentCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"id": "desc"}],
            search=cond,
            out_schema=AssignmentOutSchema,
            preload=_ASSIGNMENT_PRELOAD,
        )
        for item in result.items:
            if item.task is not None:
                TaskService._fill_task_exec_fields(item.task)
        return result

    async def grouped_my_assignments(self, search: AssignmentQueryParam | None = None) -> list[MiniAssignmentGroupSchema]:
        """我的任务分组：复用我的任务语义，一次性查出全部分派并按任务项目分组。"""
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        assignments = await AssignmentCRUD(self.auth, self.db).get_list(
            search=cond,
            order_by=[{"id": "desc"}],
            preload=_ASSIGNMENT_PRELOAD,
        )
        return self._group_orm_assignments(assignments)

    @staticmethod
    def _group_orm_assignments(assignments: Sequence[AssignmentModel]) -> list[MiniAssignmentGroupSchema]:
        """按分派单所属任务的项目分组，组内按任务分类/模板/三级任务排序。

        保留分派单自身 id/status（而非仅任务），供「我的任务」状态筛选、进度轨道、
        成果角标与卡片跳转使用。
        """
        def sort_key(a: AssignmentModel) -> tuple[int, ...]:
            task = a.task
            if task is None:
                return (0, 0, 0, 0, 0, 0, a.id or 0)
            return (*TaskService._task_orm_sort_key(task), a.id or 0)

        ordered = sorted(assignments, key=sort_key)
        groups: dict[int, MiniAssignmentGroupSchema] = {}
        for a in ordered:
            task = a.task
            project = task.project if task else None
            project_id = task.project_id if task else 0
            group = groups.get(project_id)
            if group is None:
                group = MiniAssignmentGroupSchema(
                    project_id=project_id,
                    project_name=project.name if project else "",
                    period=project.period if project else None,
                )
                groups[project_id] = group
            out = AssignmentOutSchema.model_validate(a)
            if out.task is not None:
                TaskService._fill_task_exec_fields(out.task)
            group.assignments.append(out)
        return list(groups.values())

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
        """查询成果详情。

        除基础字段外回填四样只读信息（都是审核员看页面时必须有的）：

        1. ``task``：项目/分类/模板/任务的扁平上下文（成果表只有 ``assignment_id``）；
        2. ``institution``：只有 ``institution_id`` 时前端无法反查机构名称；
        3. ``form_schema``：该任务的采集表单结构，是 ``form_data`` 英文字段名 → 中文标签的
           唯一映射源（前端不重复维护字段名）；
        4. ``region`` / ``subject_name`` / ``archive_no``：早期提交只落 ``form_data``，这三列
           从未赋值，这里按 ``form_data`` 推导并**顺手补写回表**（只补空值，一次性自愈，
           让列表页也能看到）；档案号按 ``ARC-`` 序列生成。
        """
        crud = SubmissionCRUD(self.auth, self.db)
        submission = await crud.get_or_404(id=id, preload=_SUBMISSION_PRELOAD)
        out = self._to_out(submission)
        out.form_schema = _resolve_form_schema_sections(submission.assignment.task)

        # 存量行：把出参层算出的摘要值真正落库（只补空值），档案号同理
        patch: dict[str, Any] = {
            field: getattr(out, field) for field in ("subject_name", "region") if getattr(out, field) and not getattr(submission, field)
        }
        if not out.archive_no:
            out.archive_no = await next_code(self.db, NumberPrefix.ARCHIVE)
            patch["archive_no"] = out.archive_no
        if patch:
            await crud.update(id=id, data=patch)
        return out

    def _to_out(self, submission: Any) -> SubmissionOutSchema:
        """ORM 成果行 → 出参：补任务上下文，并按需算出摘要字段（只影响出参，不落库）。"""
        out = SubmissionOutSchema.model_validate(submission)
        out.task = _task_context(submission.assignment.task)
        self._fill_summary_fields(out)
        return out

    @staticmethod
    def _fill_summary_fields(out: SubmissionOutSchema) -> None:
        """按机构 / ``form_data`` 回填空的摘要字段（对象名称、区域），已有值不覆盖。

        存量行的这两列从未写入，如果只在详情里补，列表仍是一片空白；因此出参层统一补齐，
        详情再把差异落库（见 ``detail``）。
        """
        derived = _submission_display_fields(out.form_data, out.subject_type)
        if not out.subject_name:
            out.subject_name = (out.institution.name if out.institution else "") or derived["subject_name"] or None
        if not out.region:
            out.region = (out.institution.region if out.institution else "") or derived["region"] or None

    async def _page_out(
        self,
        page_no: int,
        page_size: int,
        search: dict[str, Any],
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[SubmissionOutSchema]:
        """分页取成果并逐行补任务上下文（列表与「我的成果」共用）。"""
        offset = (page_no - 1) * page_size
        result = await SubmissionCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search,
            preload=_SUBMISSION_PRELOAD,
        )
        return PageResultSchema[SubmissionOutSchema](
            page_no=result.page_no,
            page_size=result.page_size,
            total=result.total,
            has_next=result.has_next,
            items=[self._to_out(submission) for submission in result.items],
        )

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: SubmissionQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[SubmissionOutSchema]:
        """分页查询成果（可按项目/模板/任务层级过滤，见 ``_apply_task_filter``）。"""
        cond = search_to_dict(search) or {}
        _apply_task_filter(cond)
        return await self._page_out(page_no=page_no, page_size=page_size, search=cond, order_by=order_by)

    async def create(self, data: SubmissionCreateSchema) -> SubmissionOutSchema:
        """提交成果（落库即 ``PENDING`` 待审核），并按模板采集对象类型归集机构。

        采集对象类型以任务模板 ``TaskConfig.subject_type`` 为准（前端传值仅作兜底）；
        当对象为机构时，从 ``form_data`` 提取机构名称/区域/等级，按模板名映射机构类型后
        归集机构（同名复用、否则创建），回填 ``institution_id``。运营端不再手动预置机构。

        并发与去重：先对分派行加 ``FOR UPDATE`` 锁，再按模板 ``submit_rule.cadence`` 判断本月是否
        已提交——``monthly`` / ``once`` 只允许一份，``unlimited``（如会议服务）不限。行锁保证两个
        并发请求不会同时通过查重；``market_submission`` 上没有唯一约束（定额任务需要单月多份）。
        """
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(
            id=data.assignment_id, msg="分配记录不存在", preload=["task", "task.template", "task.item"]
        )
        # 先锁分派行：同一分派的并发提交在此串行化
        await self.db.execute(
            select(AssignmentModel.id).where(AssignmentModel.id == data.assignment_id).with_for_update()
        )
        template = assignment.task.template
        template_config = TaskConfig.model_validate(template.config)
        await self._ensure_period_not_submitted(
            assignment_id=data.assignment_id,
            period=data.period,
            cadence=template_config.submit_rule.cadence,
        )
        subject_type = (template.config or {}).get("subject_type", data.subject_type)

        create_data = data.model_dump()
        create_data["user_id"] = self.auth.user.id
        create_data["subject_type"] = subject_type
        create_data["status"] = SubmissionStatus.PENDING.value

        # 摘要字段由后端从 form_data 推导（C 端只传 form_data）：对象名称 / 区域
        display_fields = _submission_display_fields(data.form_data, subject_type)
        create_data["subject_name"] = data.subject_name or display_fields["subject_name"] or None
        create_data["region"] = data.region or display_fields["region"] or None
        # 档案号：成果的开发档案编号，C 端不填写，由运营端开后即时分配（唯一、可搜索）
        create_data["archive_no"] = data.archive_no or await next_code(self.db, NumberPrefix.ARCHIVE)

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
        # 提交动作回写分派状态：首次提交 → SUBMITTED（审核通过后才会推进到 REVIEWED）
        if assignment.status in {AssignmentStatus.ACCEPTED.value, AssignmentStatus.PENDING.value}:
            await AssignmentCRUD(self.auth, self.db).update(
                id=assignment.id,
                data={"status": AssignmentStatus.SUBMITTED.value, "submitted_at": datetime.now(UTC)},
            )
        # 产品库自动入库：成果里出现库里没有的产品时写待审记录（失败不阻断提交，见 ProductService）
        await ProductService(self.auth, self.db).ingest_from_form_data(
            data.form_data, _resolve_form_schema(assignment.task)
        )
        return await self.detail(id=submission.id)

    async def _ensure_period_not_submitted(self, assignment_id: int, period: str, cadence: str) -> None:
        """按提交节奏校验同一分派在同一月份是否已提交过成果。

        ``monthly`` / ``once`` 只允许一份（驳回的那份不算占用，允许改后重提）；
        ``unlimited`` 不限（如会议服务）。调用方需先对分派行加锁，否则并发下会双通过。
        """
        if cadence == SubmitCadence.UNLIMITED.value:
            return
        existing = await SubmissionCRUD(self.auth, self.db).get_list(
            search={"assignment_id": assignment_id, "period": period, "status": ("notin", [SubmissionStatus.REJECTED.value])}
        )
        if existing:
            raise CustomException(msg=f"本月已提交过该任务的成果（{period}），请勿重复提交")

    async def update(self, id: int, data: SubmissionUpdateSchema) -> SubmissionOutSchema:
        """更新成果（草稿/驳回状态可改，驳回重提版本 +1）。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(
            id=id, preload=["assignment", "assignment.task", "assignment.task.template", "assignment.task.item"]
        )
        if submission.status not in {SubmissionStatus.DRAFT.value, SubmissionStatus.REJECTED.value}:
            raise CustomException(msg="仅草稿/驳回状态的成果可修改")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if submission.status == SubmissionStatus.REJECTED.value:
            update_data["version"] = submission.version + 1
            update_data["status"] = SubmissionStatus.DRAFT.value
        await SubmissionCRUD(self.auth, self.db).update(id=id, data=update_data)
        if data.form_data is not None:
            # 驳回重提同样要把新增产品入库（同一判重键已存在则跳过）
            await ProductService(self.auth, self.db).ingest_from_form_data(
                data.form_data, _resolve_form_schema(submission.assignment.task)
            )
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除成果。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await SubmissionCRUD(self.auth, self.db).delete(ids=ids)

    async def my_detail(self, id: int) -> SubmissionOutSchema:
        """我的成果详情（C 端）：驳回后修改重提要回填原表单。

        越权按「不存在」处理，不向调用方泄露他人成果是否存在。
        """
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(
            id=id, msg="成果不存在", preload=_SUBMISSION_PRELOAD
        )
        if submission.user_id != self.auth.user.id:
            raise CustomException(msg="成果不存在")
        return await self.detail(id=id)

    async def my_submissions(
        self, page_no: int, page_size: int, search: SubmissionQueryParam | None = None
    ) -> PageResultSchema[SubmissionOutSchema]:
        """我的成果：按当前登录用户过滤的成果列表。"""
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        _apply_task_filter(cond)
        return await self._page_out(page_no=page_no, page_size=page_size, search=cond)

    async def review(self, id: int, data: SubmissionReviewSchema) -> SubmissionReviewResultSchema:
        """审核成果：approved→APPROVED，否则 REJECTED+review_comment，回写 assignment.status。

        审核通过后**立即自动归集结算**（不再要求运营另点「归集结算」），归集为 best-effort：
        审核已经生效是事实，归集失败不回滚审核，只把原因带回出参供前端提示。
        """
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id, preload=["assignment"])
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
        # 回写分派状态：通过 → REVIEWED（本项目所有成果审完即视为审核完成）；驳回 → SUBMITTED（等重提）
        target_status = AssignmentStatus.REVIEWED.value if data.approved else AssignmentStatus.SUBMITTED.value
        await AssignmentCRUD(self.auth, self.db).update(
            id=submission.assignment_id,
            data={"status": target_status, "submitted_at": datetime.now(UTC)},
        )
        settlement, warning = await self._auto_settle(submission) if data.approved else (None, None)
        return SubmissionReviewResultSchema(
            submission=await self.detail(id=id), settlement=settlement, warning=warning
        )

    async def _auto_settle(
        self, submission: SubmissionModel
    ) -> tuple[SubmissionSettlementNoticeSchema | None, str | None]:
        """审核通过后自动归集：按 (任务, 成果月份) 调 ``SettlementService.settle``。

        归集**不看任务状态**（``require_completed=False``）——审核是业务真实终点，卡「任务已完成」
        只会让结算与发放数据一直空着；运营手动点「归集结算」仍保留该前置。

        :return: (归集结果, 失败原因)；失败时归集结果为 None，原因用于提示运营手动补跑。
        """
        assignment = submission.assignment
        try:
            await SettlementService(self.auth, self.db).settle(
                task_id=assignment.task_id, period=submission.period, require_completed=False
            )
            row = await SettlementCRUD(self.auth, self.db).get(
                task_id=assignment.task_id, user_id=assignment.user_id, period=submission.period
            )
            result = await PayoutService(self.auth, self.db).summary(
                user_id=assignment.user_id, period=submission.period
            )
        except Exception as exc:  # 归集失败不得让已生效的审核回滚
            logger.exception(f"成果 {submission.id} 审核通过后自动归集失败")
            return None, f"审核已生效，但自动归集失败：{getattr(exc, 'msg', None) or exc}"
        if row is None:
            return None, "审核已生效，但本次未生成结算单（请确认任务模板单价已配置）"
        return (
            SubmissionSettlementNoticeSchema(
                task_id=assignment.task_id,
                period=submission.period,
                payable=row.payable_amount,
                paid=result.paid,
                rollover=result.rollover,
                limit=result.limit,
            ),
            None,
        )
