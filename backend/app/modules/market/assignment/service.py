from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.modules.system.user.crud import UserCRUD
from app.utils.common_util import search_to_dict

from ..enums import AssignmentStatus, TaskStatus
from ..quota.service import QuotaService
from ..task.crud import TaskCRUD
from .crud import AssignmentCRUD
from .schema import AssignmentCreateSchema, AssignmentOutSchema, AssignmentQueryParam

# task 为 TaskOutSchema（含 company/task_type 等 UserBySchema 嵌套），须完整预加载各层审计关系，
# 避免 detail()/page()/accept() 序列化时在异步环境下触发懒加载 MissingGreenlet
_ASSIGNMENT_PRELOAD = [
    "task",
    "task.created_by",
    "task.updated_by",
    "task.task_type",
    "task.task_type.created_by",
    "task.task_type.updated_by",
    "task.company",
    "task.company.created_by",
    "task.company.updated_by",
]


class AssignmentService:
    """任务分派/接收服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> AssignmentOutSchema:
        """查询分派详情。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(id=id, preload=_ASSIGNMENT_PRELOAD)
        return AssignmentOutSchema.model_validate(assignment)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: AssignmentQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[AssignmentOutSchema]:
        """分页查询分派。"""
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
        """分派任务：一个任务指派给多个 C 端用户（批量）。"""
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=data.task_id, msg="任务不存在")
        if task.status not in {TaskStatus.PUBLISHED.value, TaskStatus.IN_PROGRESS.value}:
            raise CustomException(msg="仅已发布/进行中的任务可分派")

        users = await UserCRUD(self.auth, self.db).get_list(search={"id": ("in", data.user_ids)})
        if len(users) != len(set(data.user_ids)):
            missing = sorted(set(data.user_ids) - {u.id for u in users})
            raise CustomException(msg=f"用户不存在: {missing}")

        assign_amount = Decimal(task.unit_price) * task.exec_qty
        assignment_ids: list[int] = []
        for user_id in data.user_ids:
            if await AssignmentCRUD(self.auth, self.db).get(task_id=data.task_id, user_id=user_id):
                continue  # 已分派，跳过（幂等）
            assignment = await AssignmentCRUD(self.auth, self.db).create(
                data={
                    "task_id": data.task_id,
                    "user_id": user_id,
                    "assign_amount": assign_amount,
                    "status": AssignmentStatus.PENDING.value,
                }
            )
            assignment_ids.append(assignment.id)
        # 重新加载预关联，避免 model_validate 触发 async 懒加载（MissingGreenlet）
        return [await self.detail(id=aid) for aid in assignment_ids]

    async def delete(self, ids: list[int]) -> None:
        """撤销分派（仅待接收状态可撤销）。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        assignments = await AssignmentCRUD(self.auth, self.db).get_list(search={"id": ("in", ids)})
        for assignment in assignments:
            if assignment.status != AssignmentStatus.PENDING.value:
                raise CustomException(msg=f"分派[{assignment.id}]已被接收，不能撤销")
        await AssignmentCRUD(self.auth, self.db).delete(ids=ids)

    async def accept(self, id: int) -> AssignmentOutSchema:
        """接收任务：PENDING → ACCEPTED，触发限额累计（接收时拦截）。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(id=id, preload=_ASSIGNMENT_PRELOAD)
        if assignment.status != AssignmentStatus.PENDING.value:
            raise CustomException(msg="该任务不可接收（已接收或已处理）")
        if assignment.user_id != self.auth.user.id:
            raise CustomException(msg="无权接收该任务")

        quota_service = QuotaService(self.auth, self.db)
        allowed = await quota_service.check_and_accumulate_receive(
            user_id=assignment.user_id,
            period=assignment.task.period,
            assign_amount=Decimal(assignment.assign_amount),
        )
        if not allowed:
            raise CustomException(msg="本月限额已满，无法继续接收任务")

        await AssignmentCRUD(self.auth, self.db).update(
            id=id,
            data={"status": AssignmentStatus.ACCEPTED.value, "accepted_at": datetime.now(UTC)},
        )
        # 任务首次被接收时流转为进行中
        if assignment.task.status == TaskStatus.PUBLISHED.value:
            await TaskCRUD(self.auth, self.db).update(id=assignment.task.id, data={"status": TaskStatus.IN_PROGRESS.value})
        return await self.detail(id=id)

    async def my_assignments(
        self,
        page_no: int,
        page_size: int,
        search: AssignmentQueryParam | None = None,
    ) -> PageResultSchema[AssignmentOutSchema]:
        """我的任务列表（小程序端）：仅查询当前用户的分派。"""
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        offset = (page_no - 1) * page_size
        return await AssignmentCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"id": "desc"}],
            search=cond,
            out_schema=AssignmentOutSchema,
            preload=_ASSIGNMENT_PRELOAD,
        )
