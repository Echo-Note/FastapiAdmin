from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..assignment.crud import AssignmentCRUD
from ..enums import AssignmentStatus, SettlementStatus, SubmissionStatus, TaskStatus
from ..payout.service import PayoutService
from ..submission.crud import SubmissionCRUD
from ..task.crud import TaskCRUD
from .crud import SettlementCRUD, SettlementItemCRUD
from .schema import SettlementOutSchema, SettlementQueryParam


class SettlementService:
    """归集结算服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> SettlementOutSchema:
        """查询结算单详情。"""
        settlement = await SettlementCRUD(self.auth, self.db).get_or_404(id=id, preload=["items"])
        return SettlementOutSchema.model_validate(settlement)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: SettlementQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[SettlementOutSchema]:
        """分页查询结算单。"""
        offset = (page_no - 1) * page_size
        return await SettlementCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=SettlementOutSchema,
            preload=["items"],
        )

    async def settle(self, task_id: int) -> list[SettlementOutSchema]:
        """触发归集结算：汇总任务下所有审核通过的成果，按「用户 × 任务」生成结算单。

        规则（设计文档 §6）：
        - 仅「已完成」（运营判定）的任务可归集结算；
        - 应发金额 payable = 单价 × 通过成果数量（无上限）；
        - 发放封顶 + 津贴累计：调用发放服务计算实发与未发放（津贴）。
        """
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, preload=["task_type"])
        if task.status != TaskStatus.COMPLETED.value:
            raise CustomException(msg="仅「已完成」的任务可归集结算（请先判定任务完成）")

        assignments = await AssignmentCRUD(self.auth, self.db).get_list(search={"task_id": task_id})
        payout_service = PayoutService(self.auth, self.db)
        results: list[SettlementOutSchema] = []

        for assignment in assignments:
            approved_qty = await SubmissionCRUD(self.auth, self.db).count(
                assignment_id=assignment.id, status=SubmissionStatus.APPROVED.value
            )
            if approved_qty == 0:
                continue

            unit_price = Decimal(task.unit_price)
            payable = unit_price * approved_qty

            # 发放封顶 + 津贴累计
            paid, _carryover = await payout_service.settle_payable(
                user_id=assignment.user_id, period=task.period, payable=payable
            )

            # 结算单头
            settlement = await SettlementCRUD(self.auth, self.db).create(
                data={
                    "task_id": task_id,
                    "user_id": assignment.user_id,
                    "qty": approved_qty,
                    "payable_amount": payable,
                    "paid_amount": paid,
                    "status": SettlementStatus.CALCULATED.value,
                }
            )
            # 结算明细（对应附件结算单行）
            await SettlementItemCRUD(self.auth, self.db).create(
                data={
                    "settlement_id": settlement.id,
                    "service_type": task.task_type.service_type,
                    "service_item": task.task_type.service_item,
                    "service_task": task.task_type.service_task,
                    "unit": task.task_type.unit,
                    "price": unit_price,
                    "qty": approved_qty,
                    "amount": payable,
                }
            )
            # 分派流转为已结算
            await AssignmentCRUD(self.auth, self.db).update(id=assignment.id, data={"status": AssignmentStatus.SETTLED.value})

            detail = await self.detail(id=settlement.id)
            results.append(detail)

        await TaskCRUD(self.auth, self.db).update(id=task_id, data={"status": TaskStatus.SETTLED.value})
        return results
