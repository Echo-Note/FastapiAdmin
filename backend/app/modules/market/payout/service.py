"""发放管理域服务层：归集结算 + 发放封顶 / 津贴滚存 + 发放额度配置。

## 金额口径（唯一真相源，改动前先读）

按「用户 × 周期」整体计算，而不是按单条结算单：

```
当月应发 period_payable = Σ 该用户该 period 所有结算单 payable_amount
期初津贴 prev_balance   = allowance_detail 中 from_period < period 的最近一行的 amount
当月额度 limit          = payout_config(user, period).payout_limit，缺行/停用时 20000
待发   pending          = period_payable + prev_balance
实发   paid             = min(pending, limit)
期末津贴 balance_after  = pending - paid          （= max(0, pending - limit)）
```

`paid` 按结算单 id 顺序**贪心分摊**回每行的 `paid_amount`，保证 `Σ paid_amount == paid`。
分摊必然让额度耗尽后创建的单显示 0——这是封顶的真实反映，不是缺数据。
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.common_util import search_to_dict

from ..config import TaskConfig
from ..enums import (
    AllowanceStatus,
    AssignmentStatus,
    PayStatus,
    SettlementStatus,
    SubmissionStatus,
    TaskStatus,
)
from ..member import load_user_briefs
from ..task.crud import AssignmentCRUD, SubmissionCRUD, TaskCRUD
from ..task.model import TaskModel
from .crud import AllowanceCRUD, AllowanceDetailCRUD, PayoutConfigCRUD, SettlementCRUD, SettlementItemCRUD
from .model import AllowanceDetailModel, SettlementModel
from .schema import (
    AllowanceDetailOutSchema,
    AllowanceOutSchema,
    PayoutConfigCreateSchema,
    PayoutConfigOutSchema,
    PayoutConfigQueryParam,
    PayoutConfigUpdateSchema,
    PayoutResultOutSchema,
    SettlementOutSchema,
    SettlementQueryParam,
)

# 每月发放额度默认值（运营可调为 10000/20000）
DEFAULT_PAYOUT_LIMIT = Decimal("20000")

_ZERO = Decimal("0")


def _money(value: Decimal | int | float | None) -> Decimal:
    """把求和/ORM 返回的数值统一成两位小数 Decimal，避免 float 误差带进金额。"""
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


class SettlementService:
    """归集结算服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> SettlementOutSchema:
        """查询结算单详情。"""
        settlement = await SettlementCRUD(self.auth, self.db).get_or_404(id=id, preload=["items"])
        return await self._attach_user(SettlementOutSchema.model_validate(settlement))

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: SettlementQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[SettlementOutSchema]:
        """分页查询结算单（带 C 端用户摘要，前端不用自己反查 sys_user）。"""
        offset = (page_no - 1) * page_size
        result = await SettlementCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=SettlementOutSchema,
            preload=["items"],
        )
        briefs = await load_user_briefs(self.db, [item.user_id for item in result.items])
        for item in result.items:
            item.user = briefs.get(item.user_id)
        return result

    async def _attach_user(self, settlement: SettlementOutSchema) -> SettlementOutSchema:
        """给单条结算单补上用户摘要。"""
        briefs = await load_user_briefs(self.db, [settlement.user_id])
        settlement.user = briefs.get(settlement.user_id)
        return settlement

    async def settle(self, task_id: int, period: str, *, require_completed: bool = True) -> list[SettlementOutSchema]:
        """归集结算：汇总「任务 × 用户」下审核通过的成果，生成/重算结算单 + 明细，并应用发放封顶。

        规则：
        - ``require_completed`` 为真时（运营手动归集）要求任务已 COMPLETED；为假时（审核通过
          触发的自动归集）不看任务状态——审核是业务真实终点，卡状态只会让数据一直空着。
        - 应发金额 payable = 单价 × 该周期内通过成果数（无上限）。
        - **幂等靠重算实现**：已存在同 task + user + period 的结算单时更新数量与金额，而不是
          跳过。跳过会让「同月同任务的第二份通过成果」永远不计入，也会让审核结果变更后
          的金额永久停在旧值。
        - 归集完按「用户 × 周期」调 :meth:`PayoutService.apply` 应用封顶与津贴滚存。
        """
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, preload=["template", "template.category"])
        if require_completed and task.status != TaskStatus.COMPLETED.value:
            raise CustomException(msg="仅「已完成」的任务可归集结算（请先判定任务完成）")

        # 解析模板配置（unit/price），供结算明细使用
        config = TaskConfig.model_validate(task.template.config)
        unit = config.unit
        price = config.price if config.price is not None else _ZERO

        assignments = await AssignmentCRUD(self.auth, self.db).get_list(search={"task_id": task_id})
        settled_users: list[int] = []

        for assignment in assignments:
            approved_qty = await SubmissionCRUD(self.auth, self.db).count(
                assignment_id=assignment.id, status=SubmissionStatus.APPROVED.value, period=period
            )
            existing = await SettlementCRUD(self.auth, self.db).get(
                task_id=task_id, user_id=assignment.user_id, period=period
            )
            if approved_qty == 0 and not existing:
                continue

            payable = _money(price * approved_qty)
            if existing:
                await SettlementCRUD(self.auth, self.db).update(
                    id=existing.id, data={"qty": approved_qty, "payable_amount": payable}
                )
                await self._sync_item(settlement_id=existing.id, task=task, unit=unit, price=price, qty=approved_qty, amount=payable)
            else:
                settlement = await SettlementCRUD(self.auth, self.db).create(
                    data={
                        "task_id": task_id,
                        "user_id": assignment.user_id,
                        "period": period,
                        "qty": approved_qty,
                        "payable_amount": payable,
                        "status": SettlementStatus.CALCULATED.value,
                    }
                )
                await self._sync_item(settlement_id=settlement.id, task=task, unit=unit, price=price, qty=approved_qty, amount=payable)
            # 归集结算完成 → 该分派推进到 SETTLED（分派状态机的最后一个节点）
            await AssignmentCRUD(self.auth, self.db).update(
                id=assignment.id, data={"status": AssignmentStatus.SETTLED.value}
            )
            settled_users.append(assignment.user_id)

        payout = PayoutService(self.auth, self.db)
        for user_id in dict.fromkeys(settled_users):
            await payout.apply(user_id=user_id, period=period)

        results: list[SettlementOutSchema] = []
        for user_id in dict.fromkeys(settled_users):
            row = await SettlementCRUD(self.auth, self.db).get(task_id=task_id, user_id=user_id, period=period)
            if row:
                results.append(await self.detail(id=row.id))
        return results

    async def _sync_item(
        self,
        settlement_id: int,
        task: TaskModel,
        unit: str,
        price: Decimal,
        qty: int,
        amount: Decimal,
    ) -> None:
        """同步结算明细行：有则更新、无则创建、多余的删掉（一条结算单只保留一行明细）。

        明细存的是**名称快照**（分类名/模板名），不是外键——模板改名不回溯历史结算单。
        """
        crud = SettlementItemCRUD(self.auth, self.db)
        data = {
            "category_name": task.template.category.name,
            "template_name": task.template.name,
            "unit": unit,
            "price": price,
            "qty": qty,
            "amount": amount,
        }
        items = await crud.get_list(search={"settlement_id": settlement_id})
        if items:
            await crud.update(id=items[0].id, data=data)
            if len(items) > 1:
                await crud.delete(ids=[item.id for item in items[1:]])
            return
        await crud.create(data={"settlement_id": settlement_id, **data})

    async def confirm(self, id: int) -> SettlementOutSchema:
        """确认结算单：PENDING / CALCULATED → CONFIRMED。"""
        settlement = await SettlementCRUD(self.auth, self.db).get_or_404(id=id)
        if settlement.status not in {SettlementStatus.PENDING.value, SettlementStatus.CALCULATED.value}:
            raise CustomException(msg="仅待结算/已计算的结算单可确认")
        await SettlementCRUD(self.auth, self.db).update(id=id, data={"status": SettlementStatus.CONFIRMED.value})
        return await self.detail(id=id)


class PayoutService:
    """发放服务：封顶 / 津贴滚存计算 + 发放结果查询 + 发放额度配置 CRUD。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 发放算法 ──────────────────────────────────────────────────────

    async def limit_of(self, user_id: int, period: str) -> Decimal:
        """取该用户该周期的发放额度；无配置或已停用则用默认额度。"""
        config = await PayoutConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        return _money(config.payout_limit) if config and config.enabled else DEFAULT_PAYOUT_LIMIT

    async def prior_balance(self, user_id: int, period: str) -> Decimal:
        """期初津贴余额 = 该用户最近一条「早于本周期」的津贴明细 ``amount``。

        明细行的 ``amount`` 存的是**该期期末累计未发放余额**（已把期初算进待发额），所以
        连续两期叠加时只读最近一行即可，不能求和多行——那会把滚存重复计一次。
        **不看 ``status``**：重算某期时 status 可能已被改写，依赖它会让期初余额丢失。
        """
        rows = await AllowanceDetailCRUD(self.auth, self.db).get_list(
            search={"user_id": user_id, "from_period": ("lt", period)},
            order_by=[{"from_period": "desc"}],
        )
        return _money(rows[0].amount) if rows else _ZERO

    async def period_payable(self, user_id: int, period: str) -> Decimal:
        """该用户该周期所有结算单的应发合计（跨任务）。"""
        total = await self.db.scalar(
            select(func.coalesce(func.sum(SettlementModel.payable_amount), 0)).where(
                SettlementModel.user_id == user_id,
                SettlementModel.period == period,
                SettlementModel.is_deleted.is_(False),
            )
        )
        return _money(total)

    async def apply(self, user_id: int, period: str) -> PayoutResultOutSchema:
        """发放封顶 + 津贴滚存：按「用户 × 周期」整体重算并落库，返回该期发放结果。

        幂等：同一 user + period 反复调用结果相同（每次都从结算单与上期账本重算，不累加）。
        """
        payable = await self.period_payable(user_id, period)
        prev_balance = await self.prior_balance(user_id, period)
        limit = await self.limit_of(user_id, period)

        pending = payable + prev_balance
        paid = min(pending, limit)
        rollover = pending - paid

        allowance_crud = AllowanceCRUD(self.auth, self.db)
        allowance = await allowance_crud.get(user_id=user_id)
        if allowance:
            await allowance_crud.update(id=allowance.id, data={"balance": rollover})
        else:
            await allowance_crud.create(data={"user_id": user_id, "balance": rollover})

        detail_crud = AllowanceDetailCRUD(self.auth, self.db)
        detail = await detail_crud.get(user_id=user_id, from_period=period)
        if detail:
            await detail_crud.update(id=detail.id, data={"amount": rollover})
        else:
            await detail_crud.create(
                data={
                    "user_id": user_id,
                    "from_period": period,
                    "amount": rollover,
                    "status": AllowanceStatus.PENDING.value,
                }
            )

        settlements = await SettlementCRUD(self.auth, self.db).get_list(
            search={"user_id": user_id, "period": period}, order_by=[{"id": "asc"}]
        )
        remaining = paid
        for settlement in settlements:
            row_paid = min(remaining, _money(settlement.payable_amount))
            remaining -= row_paid
            await SettlementCRUD(self.auth, self.db).update(
                id=settlement.id,
                data={"paid_amount": row_paid, "pay_status": PayStatus.SCHEDULED.value},
            )

        logger.info(
            f"发放核算完成 user={user_id} period={period} "
            f"应发={payable} 期初={prev_balance} 额度={limit} 实发={paid} 滚存={rollover}"
        )
        return PayoutResultOutSchema(
            user_id=user_id,
            period=period,
            payable=payable,
            prev_balance=prev_balance,
            limit=limit,
            paid=paid,
            rollover=rollover,
        )

    async def summary(self, user_id: int, period: str) -> PayoutResultOutSchema:
        """读出发放结果（不落库）：账本里有快照就用快照，没有则按算法推导。"""
        details = await AllowanceDetailCRUD(self.auth, self.db).get_list(search={"user_id": user_id})
        return await self._derive_result(user_id=user_id, period=period, details=details)

    async def results(
        self,
        page_no: int,
        page_size: int,
        user_id: int | None = None,
        period: str | None = None,
    ) -> PageResultSchema[PayoutResultOutSchema]:
        """发放结果列表：按 用户 × 周期 聚合结算单应发，再补齐期初/额度/实发/滚存。

        分组与分页都在 SQL 侧完成（不先取全量再算）；本次页内的津贴明细与额度配置一次性
        批量查出，避免逐行 N+1。
        """
        offset = (page_no - 1) * page_size
        conditions = [SettlementModel.is_deleted.is_(False)]
        if user_id:
            conditions.append(SettlementModel.user_id == user_id)
        if period:
            conditions.append(SettlementModel.period == period)

        grouped = (
            select(
                SettlementModel.user_id.label("user_id"),
                SettlementModel.period.label("period"),
                func.sum(SettlementModel.payable_amount).label("payable"),
            )
            .where(*conditions)
            .group_by(SettlementModel.user_id, SettlementModel.period)
            .subquery()
        )

        total = await self.db.scalar(select(func.count()).select_from(grouped)) or 0
        rows = (
            await self.db.execute(
                select(grouped)
                .order_by(grouped.c.period.desc(), grouped.c.user_id.asc())
                .offset(offset)
                .limit(page_size)
            )
        ).all()

        details: list[AllowanceDetailModel] = []
        limit_map: dict[tuple[int, str], Decimal] = {}
        if rows:
            user_ids = list({row.user_id for row in rows})
            periods = list({row.period for row in rows})
            details = await AllowanceDetailCRUD(self.auth, self.db).get_list(search={"user_id": ("in", user_ids)})
            configs = await PayoutConfigCRUD(self.auth, self.db).get_list(
                search={"user_id": ("in", user_ids), "period": ("in", periods)}
            )
            limit_map = {
                (config.user_id, config.period): _money(config.payout_limit) if config.enabled else DEFAULT_PAYOUT_LIMIT
                for config in configs
            }
        items = [
            await self._derive_result(
                user_id=row.user_id,
                period=row.period,
                payable=_money(row.payable),
                details=details,
                limit=limit_map.get((row.user_id, row.period), DEFAULT_PAYOUT_LIMIT),
            )
            for row in rows
        ]
        briefs = await load_user_briefs(self.db, [item.user_id for item in items])
        for item in items:
            item.user = briefs.get(item.user_id)
        return PageResultSchema[PayoutResultOutSchema](
            page_no=page_no,
            page_size=page_size,
            total=total,
            has_next=offset + page_size < total,
            items=items,
        )

    async def _derive_result(
        self,
        user_id: int,
        period: str,
        payable: Decimal | None = None,
        details: list[AllowanceDetailModel] | None = None,
        limit: Decimal | None = None,
    ) -> PayoutResultOutSchema:
        """由结算单 + 津贴账本推出某用户某期的发放结果。

        期末津贴优先取账本快照（``allowance_detail`` 里该期那行），没有快照时才按
        ``max(0, 待发 - 额度)`` 现算——快照是当时的结论，额度后来被改动不该让历史实发跟着变。

        ``details`` / ``limit`` 可由调用方批量预取传入，避免列表页逐行 N+1。
        """
        if payable is None:
            payable = await self.period_payable(user_id, period)
        rows = details if details is not None else await AllowanceDetailCRUD(self.auth, self.db).get_list(search={"user_id": user_id})
        earlier = sorted((row for row in rows if row.from_period < period), key=lambda row: row.from_period)
        prev_balance = _money(earlier[-1].amount) if earlier else _ZERO
        snapshot = next((row for row in rows if row.from_period == period), None)
        if limit is None:
            limit = await self.limit_of(user_id=user_id, period=period)
        if snapshot:
            rollover = _money(snapshot.amount)
            paid = payable + prev_balance - rollover
        else:
            pending = payable + prev_balance
            paid = min(pending, limit)
            rollover = pending - paid
        return PayoutResultOutSchema(
            user_id=user_id,
            period=period,
            payable=payable,
            prev_balance=prev_balance,
            limit=limit,
            paid=paid,
            rollover=rollover,
        )

    # ── 发放额度配置 ──────────────────────────────────────────────────

    async def detail(self, id: int) -> PayoutConfigOutSchema:
        """查询发放额度配置详情。"""
        config = await PayoutConfigCRUD(self.auth, self.db).get_or_404(id=id)
        return PayoutConfigOutSchema.model_validate(config)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: PayoutConfigQueryParam | None = None,
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

    async def create(self, data: PayoutConfigCreateSchema) -> PayoutConfigOutSchema:
        """创建发放额度配置。"""
        if await PayoutConfigCRUD(self.auth, self.db).get(user_id=data.user_id, period=data.period):
            raise CustomException(msg="该用户该周期已存在发放额度配置")
        config = await PayoutConfigCRUD(self.auth, self.db).create(data=data)
        return PayoutConfigOutSchema.model_validate(config)

    async def update(self, id: int, data: PayoutConfigUpdateSchema) -> PayoutConfigOutSchema:
        """更新发放额度配置。"""
        await PayoutConfigCRUD(self.auth, self.db).get_or_404(id=id)
        await PayoutConfigCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除发放额度配置。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await PayoutConfigCRUD(self.auth, self.db).delete(ids=ids)

    async def my_payout(self, user_id: int, period: str) -> dict:
        """查询我的发放情况：本月应发、发放额度、津贴余额、津贴明细。

        `payable` 是 C 端「我的」页收益卡的主数字（这个月能拿多少）；它由结算单按周期
        汇总而来（`period_payable`），不是把明细行加起来——明细存的是期末余额，求和会重复计滚存。
        """
        allowance = await AllowanceCRUD(self.auth, self.db).get(user_id=user_id)
        config = await PayoutConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        details = await AllowanceDetailCRUD(self.auth, self.db).get_list(
            search={"user_id": user_id}, order_by=[{"id": "asc"}]
        )
        payable = await self.period_payable(user_id, period)
        return {
            "user_id": user_id,
            "period": period,
            "payable": float(payable),
            "payout_limit": float(config.payout_limit) if config and config.enabled else float(DEFAULT_PAYOUT_LIMIT),
            "allowance_balance": float(allowance.balance) if allowance else 0.0,
            "allowance_items": [AllowanceDetailOutSchema.model_validate(d).model_dump(mode="json") for d in details],
        }


class AllowanceService:
    """个人任务津贴服务：账户 / 明细查询。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> AllowanceOutSchema:
        """查询津贴账户详情。"""
        allowance = await AllowanceCRUD(self.auth, self.db).get_or_404(id=id)
        return AllowanceOutSchema.model_validate(allowance)

    async def page(
        self,
        page_no: int,
        page_size: int,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[AllowanceOutSchema]:
        """分页查询津贴账户。"""
        offset = (page_no - 1) * page_size
        return await AllowanceCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            out_schema=AllowanceOutSchema,
        )

    async def detail_page(
        self,
        page_no: int,
        page_size: int,
        user_id: int | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[AllowanceDetailOutSchema]:
        """分页查询津贴明细。"""
        offset = (page_no - 1) * page_size
        search: dict[str, object] = {}
        if user_id is not None:
            search["user_id"] = user_id
        return await AllowanceDetailCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search,
            out_schema=AllowanceDetailOutSchema,
        )
