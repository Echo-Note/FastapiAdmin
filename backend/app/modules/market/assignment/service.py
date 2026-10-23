from datetime import UTC, datetime

from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.redis_crud import RedisCURD
from app.modules.system.user.crud import UserCRUD
from app.utils.common_util import search_to_dict

from ..enums import AssignmentSource, AssignmentStatus, AssignMode, TaskKind, TaskStatus
from ..task.crud import TaskCRUD
from .crud import AssignmentCRUD
from .schema import AssignmentCreateSchema, AssignmentOutSchema, AssignmentQueryParam

# task 为 TaskOutSchema（含 task_type 等 UserBySchema 嵌套），须完整预加载各层审计关系，
# 避免 detail()/page()/accept() 序列化时在异步环境下触发懒加载 MissingGreenlet
_ASSIGNMENT_PRELOAD = [
    "task",
    "task.created_by",
    "task.updated_by",
    "task.task_type",
    "task.task_type.created_by",
    "task.task_type.updated_by",
    "task.project_links",
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
        if task.assign_mode != AssignMode.DIRECT.value:
            raise CustomException(msg="该任务为公开大厅任务，请在任务大厅自行接单，不支持定向分派")

        users = await UserCRUD(self.auth, self.db).get_list(search={"id": ("in", data.user_ids)})
        if len(users) != len(set(data.user_ids)):
            missing = sorted(set(data.user_ids) - {u.id for u in users})
            raise CustomException(msg=f"用户不存在: {missing}")

        assignment_ids: list[int] = []
        for user_id in data.user_ids:
            if await AssignmentCRUD(self.auth, self.db).get(task_id=data.task_id, user_id=user_id):
                continue  # 已分派，跳过（幂等）
            assignment = await AssignmentCRUD(self.auth, self.db).create(
                data={
                    "task_id": data.task_id,
                    "user_id": user_id,
                    "source": AssignmentSource.ASSIGNED.value,
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
        """接收任务：PENDING → ACCEPTED。不限额、不限单量。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(id=id, preload=_ASSIGNMENT_PRELOAD)
        if assignment.status != AssignmentStatus.PENDING.value:
            raise CustomException(msg="该任务不可接收（已接收或已处理）")
        if assignment.user_id != self.auth.user.id:
            raise CustomException(msg="无权接收该任务")

        await AssignmentCRUD(self.auth, self.db).update(
            id=id,
            data={"status": AssignmentStatus.ACCEPTED.value, "accepted_at": datetime.now(UTC)},
        )
        # 任务首次被接收时流转为进行中
        if assignment.task.status == TaskStatus.PUBLISHED.value:
            await TaskCRUD(self.auth, self.db).update(id=assignment.task.id, data={"status": TaskStatus.IN_PROGRESS.value})
        return await self.detail(id=id)

    async def claim(self, task_id: int, redis: Redis) -> AssignmentOutSchema:
        """大厅接单：公开任务由当前用户自行接单，直接形成「已接收」的任务实例。

        不限制接单数量与金额；定额任务受执行数量限量约束（接单即占名额，先到先得），
        名额接满后拒绝接单，任务随之从大厅消失。同一用户同一任务仅可接单一次。
        """
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, msg="任务不存在")
        if task.assign_mode != AssignMode.OPEN.value:
            raise CustomException(msg="该任务为定向分派任务，不支持大厅接单")
        if task.status not in {TaskStatus.PUBLISHED.value, TaskStatus.IN_PROGRESS.value}:
            raise CustomException(msg="该任务暂不可接单")
        if task.exec_time_end is not None and task.exec_time_end <= datetime.now(UTC):
            raise CustomException(msg="该任务已超出限定时间范围，不可接单")

        # 同一用户对同一任务仅可接单一次（幂等防重）
        if await AssignmentCRUD(self.auth, self.db).get(task_id=task_id, user_id=self.auth.user.id):
            raise CustomException(msg="您已接取该任务，请勿重复接单")

        # 定额任务：接单占用一个名额（Redis 原子计数防超卖），名额接满即拒绝
        if task.task_kind == TaskKind.QUOTA.value:
            claim_key = f"{RedisInitKeyConfig.MARKET_TASK_CLAIM.key}:{task_id}"
            new_count = await RedisCURD(redis).incr_with_limit(key=claim_key, limit=task.exec_qty)
            if new_count < 0:
                raise CustomException(msg="该任务名额已满，无法接单")

        try:
            assignment = await AssignmentCRUD(self.auth, self.db).create(
                data={
                    "task_id": task_id,
                    "user_id": self.auth.user.id,
                    "source": AssignmentSource.CLAIMED.value,
                    "status": AssignmentStatus.ACCEPTED.value,
                    "accepted_at": datetime.now(UTC),
                }
            )
        except Exception:
            # 定额任务名额已占用但落库失败，回滚计数
            if task.task_kind == TaskKind.QUOTA.value:
                claim_key = f"{RedisInitKeyConfig.MARKET_TASK_CLAIM.key}:{task_id}"
                await RedisCURD(redis).decr(key=claim_key)
            raise

        if task.status == TaskStatus.PUBLISHED.value:
            await TaskCRUD(self.auth, self.db).update(id=task_id, data={"status": TaskStatus.IN_PROGRESS.value})
        return await self.detail(id=assignment.id)

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
