"""发放额度与个人任务津贴的业务逻辑。"""

from decimal import Decimal

from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.utils.common_util import search_to_dict

from ..enums import AllowanceStatus
from ..settlement.model import SettlementModel
from ..task.model import TaskModel
from .crud import AllowanceCRUD, AllowanceDetailCRUD, PayoutConfigCRUD
from .model import AllowanceModel
from .schema import (
    AllowanceDetailOutSchema,
    MyEarningsSummaryOutSchema,
    PayoutConfigCreateSchema,
    PayoutConfigOutSchema,
    PayoutConfigUpdateSchema,
    PayoutQueryParam,
)

# 每月发放额度默认值（运营可调为 10000/20000）
DEFAULT_PAYOUT_LIMIT = Decimal("20000")


class PayoutService:
    """发放服务：配置 CRUD + 发放封顶 / 津贴累计算法。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 配置 CRUD ──────────────────────────────────────────────────────

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: PayoutQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[PayoutConfigOutSchema]:
        """分页查询发放额度配置。"""
        offset = (page_no - 1) * page_size
        return await PayoutConfigCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=PayoutConfigOutSchema,
        )

    async def save_config(self, data: PayoutConfigCreateSchema) -> PayoutConfigOutSchema:
        """创建或更新发放额度配置（按 user_id + period upsert）。"""
        exist = await PayoutConfigCRUD(self.auth, self.db).get(user_id=data.user_id, period=data.period)
        if exist:
            await PayoutConfigCRUD(self.auth, self.db).update(
                id=exist.id,
                data=PayoutConfigUpdateSchema(payout_limit=data.payout_limit, enabled=data.enabled),
            )
            config = exist
        else:
            config = await PayoutConfigCRUD(self.auth, self.db).create(data=data)
        return PayoutConfigOutSchema.model_validate(config)

    # ── 算法辅助 ───────────────────────────────────────────────────────

    async def get_effective_payout_limit(self, user_id: int, period: str) -> Decimal:
        """获取用户某周期生效的每月发放额度；无配置或已停用返回默认 2 万。"""
        config = await PayoutConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        if config is None or not config.enabled:
            return DEFAULT_PAYOUT_LIMIT
        return Decimal(config.payout_limit)

    async def get_or_create_allowance(self, user_id: int) -> AllowanceModel:
        """获取或创建用户津贴账户。"""
        allowance = await AllowanceCRUD(self.auth, self.db).get(user_id=user_id)
        if allowance is None:
            allowance = await AllowanceCRUD(self.auth, self.db).create(data={"user_id": user_id, "balance": 0})
        return allowance

    async def settle_payable(self, user_id: int, period: str, payable: Decimal) -> tuple[Decimal, Decimal]:
        """发放封顶 + 津贴累计（设计文档 §6.2）。

        规则：
        - 津贴（上期未发放）优先发放；
        - 剩余额度再发放本月应发；
        - 本月未发放部分累计入津贴账户，顺延下月发放。

        返回:
        - tuple[Decimal, Decimal]: (本月实发总额, 本月新增未发放金额)。
        """
        allowance = await self.get_or_create_allowance(user_id=user_id)
        limit = await self.get_effective_payout_limit(user_id=user_id, period=period)

        balance = Decimal(allowance.balance)
        paid_balance = min(balance, limit)
        remaining = limit - paid_balance
        paid_payable = min(payable, remaining)

        paid = paid_balance + paid_payable
        carryover_new = payable - paid_payable
        new_balance = balance - paid_balance + carryover_new

        allowance.balance = new_balance
        await self.db.flush()

        if carryover_new > 0:
            await AllowanceDetailCRUD(self.auth, self.db).create(
                data={"user_id": user_id, "from_period": period, "amount": carryover_new, "status": AllowanceStatus.PENDING.value}
            )

        return paid, carryover_new

    # ── 查询 ───────────────────────────────────────────────────────────

    async def my_summary(self, user_id: int, period: str) -> MyEarningsSummaryOutSchema:
        """我的收益汇总（C 端「我的」页收益卡）：本月应发 + 津贴余额 + 本月发放额度。

        `market_settlement` 自身没有 period 字段，周期在 `market_task.period` 上，
        因此「本月应发」= join task 后按周期过滤的结算单 `payable_amount` 合计。
        一期的应发即应得（没有支付环节），所以这里不区分结算单状态。
        """
        summary_stmt = (
            select(
                func.coalesce(func.sum(SettlementModel.payable_amount), 0),
                func.count(SettlementModel.id),
            )
            .join(TaskModel, TaskModel.id == SettlementModel.task_id)
            .where(
                SettlementModel.user_id == user_id,
                TaskModel.period == period,
                SettlementModel.is_deleted == false(),
            )
        )
        payable_sum, settlement_count = (await self.db.execute(summary_stmt)).one()

        allowance = await AllowanceCRUD(self.auth, self.db).get(user_id=user_id)
        config = await PayoutConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        return MyEarningsSummaryOutSchema(
            period=period,
            month_payable=float(payable_sum or 0),
            settlement_count=int(settlement_count or 0),
            allowance_balance=float(allowance.balance) if allowance else 0.0,
            payout_limit=float(config.payout_limit) if config and config.enabled else float(DEFAULT_PAYOUT_LIMIT),
        )

    async def my_payout(self, user_id: int, period: str) -> dict:
        """查询我的发放情况：发放额度、津贴余额、津贴明细。"""
        allowance = await AllowanceCRUD(self.auth, self.db).get(user_id=user_id)
        config = await PayoutConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        details = await AllowanceDetailCRUD(self.auth, self.db).get_list(
            search={"user_id": user_id, "status": AllowanceStatus.PENDING.value}, order_by=[{"id": "asc"}]
        )
        return {
            "user_id": user_id,
            "period": period,
            "payout_limit": float(config.payout_limit) if config and config.enabled else float(DEFAULT_PAYOUT_LIMIT),
            "allowance_balance": float(allowance.balance) if allowance else 0.0,
            "allowance_items": [AllowanceDetailOutSchema.model_validate(d).model_dump() for d in details],
        }
