from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.utils.common_util import search_to_dict

from ..enums import CarryoverStatus
from .crud import QuotaCarryoverCRUD, QuotaConfigCRUD, QuotaUsageCRUD
from .model import QuotaUsageModel
from .schema import (
    QuotaCarryoverOutSchema,
    QuotaConfigCreateSchema,
    QuotaConfigOutSchema,
    QuotaConfigUpdateSchema,
    QuotaQueryParam,
)


def _next_period(period: str) -> str:
    """计算下一周期（自然月 +1）。

    参数:
    - period (str): 周期字符串，如 ``2026-10``。

    返回:
    - str: 下一周期，如 ``2026-11``（12 月跨年为次年 1 月）。
    """
    year, month = period.split("-")
    y, m = int(year), int(month)
    if m == 12:
        return f"{y + 1:04d}-01"
    return f"{y:04d}-{m + 1:02d}"


class QuotaService:
    """限额服务：配置 CRUD + 接收累计 / 结算封顶 / 顺延算法。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 配置 CRUD ──────────────────────────────────────────────────────

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: QuotaQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[QuotaConfigOutSchema]:
        """分页查询限额配置。"""
        offset = (page_no - 1) * page_size
        return await QuotaConfigCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=QuotaConfigOutSchema,
        )

    async def save_config(self, data: QuotaConfigCreateSchema) -> QuotaConfigOutSchema:
        """创建或更新限额配置（按 user_id + period upsert）。"""
        exist = await QuotaConfigCRUD(self.auth, self.db).get(user_id=data.user_id, period=data.period)
        if exist:
            await QuotaConfigCRUD(self.auth, self.db).update(
                id=exist.id,
                data=QuotaConfigUpdateSchema(quota_amount=data.quota_amount, enabled=data.enabled),
            )
            config = exist
        else:
            config = await QuotaConfigCRUD(self.auth, self.db).create(data=data)
        return QuotaConfigOutSchema.model_validate(config)

    # ── 算法辅助 ───────────────────────────────────────────────────────

    async def get_effective_quota(self, user_id: int, period: str) -> Decimal | None:
        """获取用户某周期生效的限额额度；无配置或已停用返回 None（视为不限）。"""
        config = await QuotaConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        if config is None or not config.enabled:
            return None
        return config.quota_amount

    async def get_or_create_usage(self, user_id: int, period: str) -> QuotaUsageModel:
        """获取或创建「用户 × 周期」的限额使用记录。"""
        usage = await QuotaUsageCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        if usage is None:
            usage = await QuotaUsageCRUD(self.auth, self.db).create(
                data={"user_id": user_id, "period": period, "received_amount": 0, "payable_amount": 0, "over_amount": 0}
            )
        return usage

    async def check_and_accumulate_receive(self, user_id: int, period: str, assign_amount: Decimal) -> bool:
        """接收任务时的限额检查与累计（接收时拦截）。

        规则（设计文档 §6.2）：
        - 累计接收金额已达限额 → 拒绝接收（返回 False）。
        - 未达限额 → 累计接收金额 += assign_amount，临界超额仅标记 over_amount，允许接收。

        返回:
        - bool: True 表示允许接收，False 表示已达限额拒绝接收。
        """
        usage = await self.get_or_create_usage(user_id=user_id, period=period)
        quota = await self.get_effective_quota(user_id=user_id, period=period)

        if quota is not None and usage.received_amount >= quota:
            return False

        usage.received_amount = Decimal(usage.received_amount) + assign_amount
        if quota is not None:
            usage.over_amount = max(Decimal(0), usage.received_amount - quota)
        await self.db.flush()
        return True

    async def settle_payable(self, user_id: int, period: str, payable: Decimal) -> tuple[Decimal, Decimal]:
        """归集结算时的发放封顶与顺延（设计文档 §6.2）。

        规则：
        - 可发额度 remaining = max(0, Q - 累计应发)。
        - 实际可发 actual = min(payable, remaining)。
        - 顺延 carryover = payable - actual（滚入下一周期）。

        返回:
        - tuple[Decimal, Decimal]: (实际可发金额, 顺延金额)。
        """
        usage = await self.get_or_create_usage(user_id=user_id, period=period)
        quota = await self.get_effective_quota(user_id=user_id, period=period)

        actual = payable
        carryover = Decimal(0)
        if quota is not None:
            remaining = max(Decimal(0), quota - Decimal(usage.payable_amount))
            actual = min(payable, remaining)
            carryover = payable - actual

        usage.payable_amount = Decimal(usage.payable_amount) + actual
        await self.db.flush()

        if carryover > 0:
            await QuotaCarryoverCRUD(self.auth, self.db).create(
                data={
                    "user_id": user_id,
                    "from_period": period,
                    "to_period": _next_period(period),
                    "amount": carryover,
                    "status": CarryoverStatus.PENDING.value,
                }
            )

        return actual, carryover

    # ── 查询 ───────────────────────────────────────────────────────────

    async def my_quota(self, user_id: int, period: str) -> dict:
        """查询我的额度/收益：限额额度、累计接收、累计应发、超限、顺延明细。"""
        usage = await QuotaUsageCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        quota = await self.get_effective_quota(user_id=user_id, period=period)
        carryovers = await QuotaCarryoverCRUD(self.auth, self.db).get_list(
            search={"user_id": user_id, "to_period": period, "status": CarryoverStatus.PENDING.value},
            order_by=[{"id": "asc"}],
        )
        return {
            "user_id": user_id,
            "period": period,
            "quota_amount": float(quota) if quota is not None else None,
            "received_amount": float(usage.received_amount) if usage else 0.0,
            "payable_amount": float(usage.payable_amount) if usage else 0.0,
            "over_amount": float(usage.over_amount) if usage else 0.0,
            "carryover_items": [QuotaCarryoverOutSchema.model_validate(c).model_dump() for c in carryovers],
        }
