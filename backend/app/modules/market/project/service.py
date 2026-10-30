"""项目管理（对外）、医药公司主数据、月度报告的业务逻辑。

- ``CompanyService``：医药公司主数据 CRUD
- ``ProjectService``：项目 CRUD + 关联任务单元（三级任务/叶子模板）+ 状态流转 + 发布（按任务单元批量生成任务）
- ``ReportService``：月度报告 CRUD + 按项目×模板×月份聚合生成报告

跨模块依赖（三级任务 ``TaskItemModel``、任务实例 ``TaskModel``、成果 ``SubmissionModel``）
定义于任务管理模块（``..task``），此处以延迟 import 引入，
避免本模块加载时因依赖尚未就绪而整体失败。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..enums import ProjectStatus, SubmissionStatus
from ..numbering import NumberPrefix, next_code
from .crud import CompanyCRUD, ProjectCRUD, ProjectItemCRUD, ReportCRUD
from .schema import (
    CompanyCreateSchema,
    CompanyOutSchema,
    CompanyQueryParam,
    CompanyUpdateSchema,
    ProjectCreateSchema,
    ProjectOutSchema,
    ProjectQueryParam,
    ProjectStatusUpdateSchema,
    ProjectUpdateSchema,
    ReportCreateSchema,
    ReportOutSchema,
    ReportQueryParam,
    ReportUpdateSchema,
)

# company 为 UserBySchema（含 created_by/updated_by），需嵌套预加载审计关系；
# item_links 为项目-三级任务关联，序列化 item_ids 时依赖它，需 selectinload 预加载
_PROJECT_PRELOAD = [
    "company",
    "company.created_by",
    "company.updated_by",
    "item_links",
]

# 报告需预加载其所属项目与二级模板（用于详情展示）
_REPORT_PRELOAD = ["project", "template"]


class CompanyService:
    """医药公司主数据服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> CompanyOutSchema:
        """查询医药公司详情。"""
        company = await CompanyCRUD(self.auth, self.db).get_or_404(id=id)
        return CompanyOutSchema.model_validate(company)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: CompanyQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[CompanyOutSchema]:
        """分页查询医药公司。"""
        offset = (page_no - 1) * page_size
        return await CompanyCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=CompanyOutSchema,
        )

    async def create(self, data: CompanyCreateSchema) -> CompanyOutSchema:
        """创建医药公司（编号自动生成）。"""
        if await CompanyCRUD(self.auth, self.db).get(name=data.name):
            raise CustomException(msg="已存在相同名称的医药公司")
        code = await next_code(self.db, NumberPrefix.COMPANY)
        company = await CompanyCRUD(self.auth, self.db).create(data={**data.model_dump(), "code": code})
        return CompanyOutSchema.model_validate(company)

    async def update(self, id: int, data: CompanyUpdateSchema) -> CompanyOutSchema:
        """更新医药公司（编号不可修改）。"""
        await CompanyCRUD(self.auth, self.db).get_or_404(id=id)
        if data.name and (exist := await CompanyCRUD(self.auth, self.db).get(name=data.name)) and exist.id != id:
            raise CustomException(msg="已存在相同名称的医药公司")
        await CompanyCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除医药公司。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await CompanyCRUD(self.auth, self.db).delete(ids=ids)


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
        """创建项目（草稿状态，编号自动生成），并关联任务单元（三级任务/叶子模板）。"""
        await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        create_data = data.model_dump(exclude={"item_ids", "template_ids"})
        create_data["code"] = await next_code(self.db, NumberPrefix.PROJECT)
        project = await ProjectCRUD(self.auth, self.db).create(data=create_data)
        await self._sync_task_unit_links(project.id, data.item_ids, data.template_ids)
        return await self.detail(id=project.id)

    async def update(self, id: int, data: ProjectUpdateSchema) -> ProjectOutSchema:
        """更新项目（编号不可修改）。"""
        project = await ProjectCRUD(self.auth, self.db).get_or_404(id=id, preload=_PROJECT_PRELOAD)
        if data.company_id is not None:
            await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"item_ids", "template_ids"})
        await ProjectCRUD(self.auth, self.db).update(id=id, data=update_data)
        if data.item_ids is not None or data.template_ids is not None:
            # 缺省不修改：仅传入一侧时，另一侧保持现状
            item_ids = data.item_ids if data.item_ids is not None else project.item_ids
            template_ids = data.template_ids if data.template_ids is not None else project.template_ids
            await self._sync_task_unit_links(id, item_ids, template_ids)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除项目。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await ProjectCRUD(self.auth, self.db).delete(ids=ids)

    async def add_item(self, id: int, item_id: int) -> ProjectOutSchema:
        """把三级任务关联到项目（增量，幂等）。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id, preload=_PROJECT_PRELOAD)
        await self._ensure_item_exists(item_id)
        existing = await ProjectItemCRUD(self.auth, self.db).get_list(search={"project_id": id, "item_id": item_id})
        if not existing:
            await ProjectItemCRUD(self.auth, self.db).create(data={"project_id": id, "item_id": item_id})
        return await self.detail(id=id)

    async def remove_item(self, id: int, item_id: int) -> ProjectOutSchema:
        """从项目移除三级任务关联。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id)
        existing = await ProjectItemCRUD(self.auth, self.db).get_list(search={"project_id": id, "item_id": item_id})
        if existing:
            await ProjectItemCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
        return await self.detail(id=id)

    async def add_template(self, id: int, template_id: int) -> ProjectOutSchema:
        """把叶子模板关联到项目（增量，幂等）。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id, preload=_PROJECT_PRELOAD)
        await self._ensure_template_exists(template_id)
        existing = await ProjectItemCRUD(self.auth, self.db).get_list(search={"project_id": id, "template_id": template_id})
        if not existing:
            await ProjectItemCRUD(self.auth, self.db).create(data={"project_id": id, "template_id": template_id})
        return await self.detail(id=id)

    async def remove_template(self, id: int, template_id: int) -> ProjectOutSchema:
        """从项目移除叶子模板关联。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=id)
        existing = await ProjectItemCRUD(self.auth, self.db).get_list(search={"project_id": id, "template_id": template_id})
        if existing:
            await ProjectItemCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
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

    async def publish(self, id: int) -> ProjectOutSchema:
        """发布项目：状态置为进行中，并按关联的任务单元批量创建任务实例。

        三级任务生成 ``name=f"{project}-{template}-{item}"``；叶子模板（无三级任务）生成
        ``name=f"{project}-{template}"`` 且 ``item_id`` 为空。已存在同 project+item（或
        project+叶子模板）的任务则跳过（幂等）。
        """
        from ..task.crud import TaskCRUD

        project = await ProjectCRUD(self.auth, self.db).get_or_404(
            id=id, preload=[*_PROJECT_PRELOAD, "item_links.item", "item_links.item.template", "item_links.template"]
        )
        if project.status != ProjectStatus.DRAFT.value:
            raise CustomException(msg="仅草稿状态的项目可发布")

        for link in project.item_links:
            if link.item is not None:
                item = link.item
                existing = await TaskCRUD(self.auth, self.db).get(project_id=id, item_id=item.id)
                if existing:
                    continue  # 同项目同三级任务已生成任务，幂等跳过
                task_no = await next_code(self.db, NumberPrefix.TASK)
                await TaskCRUD(self.auth, self.db).create(
                    data={
                        "task_no": task_no,
                        "project_id": id,
                        "template_id": item.template_id,
                        "item_id": item.id,
                        "name": f"{project.name}-{item.template.name}-{item.name}",
                        "period": project.period,
                        "assign_mode": "open",
                        "status": "DRAFT",
                    }
                )
            elif link.template is not None:
                # 防御历史脏关联：非叶子模板（含三级任务）不生成模板级任务，其表单结构由三级任务自包含
                await self._ensure_template_exists(link.template.id)
                template = link.template
                existing = await TaskCRUD(self.auth, self.db).get(
                    project_id=id, template_id=template.id, item_id=("None", None)
                )
                if existing:
                    continue  # 同项目同叶子模板已生成任务，幂等跳过
                task_no = await next_code(self.db, NumberPrefix.TASK)
                await TaskCRUD(self.auth, self.db).create(
                    data={
                        "task_no": task_no,
                        "project_id": id,
                        "template_id": template.id,
                        "item_id": None,
                        "name": f"{project.name}-{template.name}",
                        "period": project.period,
                        "assign_mode": "open",
                        "status": "DRAFT",
                    }
                )

        await ProjectCRUD(self.auth, self.db).update(id=id, data={"status": ProjectStatus.IN_PROGRESS.value})
        return await self.detail(id=id)

    async def _sync_task_unit_links(self, project_id: int, item_ids: list[int], template_ids: list[int]) -> None:
        """同步项目-任务单元关联关系（全量替换为传入的三级任务 + 叶子模板列表）。"""
        unique_items = list(dict.fromkeys(item_ids))  # 去重并保持顺序
        unique_templates = list(dict.fromkeys(template_ids))
        for iid in unique_items:
            await self._ensure_item_exists(iid)
        for tid in unique_templates:
            await self._ensure_template_exists(tid)
        existing = await ProjectItemCRUD(self.auth, self.db).get_list(search={"project_id": project_id})
        if existing:
            await ProjectItemCRUD(self.auth, self.db).delete(ids=[link.id for link in existing])
        for iid in unique_items:
            await ProjectItemCRUD(self.auth, self.db).create(data={"project_id": project_id, "item_id": iid})
        for tid in unique_templates:
            await ProjectItemCRUD(self.auth, self.db).create(data={"project_id": project_id, "template_id": tid})

    async def _ensure_item_exists(self, item_id: int) -> None:
        """校验三级任务存在（依赖任务管理模块的 TaskItemModel）。"""
        from ..task.crud import TaskItemCRUD

        await TaskItemCRUD(self.auth, self.db).get_or_404(id=item_id, msg=f"三级任务[{item_id}]不存在")

    async def _ensure_template_exists(self, template_id: int) -> None:
        """校验叶子模板存在且确为「叶子」（无三级任务，依赖任务管理模块的 TaskTemplateModel）。

        有三级任务的模板不承载 ``form_schema``（表单由三级任务自包含），按模板级
        关联/建任务会导致 C 端无采集字段可填，故关联入口强校验拦截。
        """
        from ..task.crud import TaskTemplateCRUD

        template = await TaskTemplateCRUD(self.auth, self.db).get_or_404(
            id=template_id, msg=f"叶子模板[{template_id}]不存在", preload=["items"]
        )
        if template.items:
            raise CustomException(
                msg=f"模板[{template.name}]含 {len(template.items)} 个三级任务，请关联其三级任务而非模板"
            )


class ReportService:
    """月度报告服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> ReportOutSchema:
        """查询月度报告详情。"""
        report = await ReportCRUD(self.auth, self.db).get_or_404(id=id, preload=_REPORT_PRELOAD)
        return ReportOutSchema.model_validate(report)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: ReportQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ReportOutSchema]:
        """分页查询月度报告。"""
        offset = (page_no - 1) * page_size
        return await ReportCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=ReportOutSchema,
            preload=_REPORT_PRELOAD,
        )

    async def create(self, data: ReportCreateSchema) -> ReportOutSchema:
        """创建月度报告。"""
        await ProjectCRUD(self.auth, self.db).get_or_404(id=data.project_id, msg="项目不存在")
        report = await ReportCRUD(self.auth, self.db).create(data=data)
        return await self.detail(id=report.id)

    async def update(self, id: int, data: ReportUpdateSchema) -> ReportOutSchema:
        """更新月度报告。"""
        await ReportCRUD(self.auth, self.db).get_or_404(id=id)
        await ReportCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除月度报告。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await ReportCRUD(self.auth, self.db).delete(ids=ids)

    async def generate(self, project_id: int, template_id: int | None, period: str) -> ReportOutSchema:
        """生成月度报告：汇总该 project(+template)+period 下审核通过成果的数量与金额写入 summary。

        ``template_id`` 为空则汇总整个项目。成果通过「成果 → 分配 → 任务」链路归属到项目与模板，
        数量为当月审核通过（``APPROVED``）成果数，金额按各模板固定单价（``config.price``）乘以数量累加。
        """
        from ..task.model import AssignmentModel, SubmissionModel, TaskModel

        await ProjectCRUD(self.auth, self.db).get_or_404(id=project_id, msg="项目不存在")

        # 项目下（可指定模板）的任务实例，预加载模板以读取单价
        task_conditions = [TaskModel.project_id == project_id, TaskModel.is_deleted.is_(False)]
        if template_id is not None:
            task_conditions.append(TaskModel.template_id == template_id)
        task_ids = list((await self.db.execute(select(TaskModel.id).where(*task_conditions))).scalars().all())

        approved_count = 0
        total_amount = 0.0
        if task_ids:
            # 当月审核通过的成果，按任务分组统计数量
            rows = (
                await self.db.execute(
                    select(AssignmentModel.task_id, func.count(SubmissionModel.id))
                    .join(SubmissionModel, SubmissionModel.assignment_id == AssignmentModel.id)
                    .where(
                        AssignmentModel.task_id.in_(task_ids),
                        AssignmentModel.is_deleted.is_(False),
                        SubmissionModel.period == period,
                        SubmissionModel.status == SubmissionStatus.APPROVED.value,
                        SubmissionModel.is_deleted.is_(False),
                    )
                    .group_by(AssignmentModel.task_id)
                )
            ).all()

            # 任务 → 模板 → 单价映射（读取模板配置的固定单价）
            task_id_to_template = {
                task.id: task.template_id
                for task in (
                    await self.db.execute(select(TaskModel).where(TaskModel.id.in_(task_ids)))
                ).scalars().all()
            }
            template_ids = set(task_id_to_template.values())
            from ..task.model import TaskTemplateModel

            template_price: dict[int, float] = {}
            if template_ids:
                templates = (
                    await self.db.execute(select(TaskTemplateModel).where(TaskTemplateModel.id.in_(template_ids)))
                ).scalars().all()
                for tmpl in templates:
                    price = (tmpl.config or {}).get("price")
                    template_price[tmpl.id] = float(price) if price is not None else 0.0

            for task_id, cnt in rows:
                count = int(cnt or 0)
                approved_count += count
                tid = task_id_to_template.get(task_id)
                if tid is not None:
                    total_amount += count * template_price.get(tid, 0.0)

        summary = {"count": approved_count, "amount": round(total_amount, 2)}
        report = await ReportCRUD(self.auth, self.db).create(
            data={
                "project_id": project_id,
                "template_id": template_id,
                "period": period,
                "summary": summary,
                "status": "DRAFT",
            }
        )
        return await self.detail(id=report.id)
