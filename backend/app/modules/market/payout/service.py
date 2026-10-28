"""发放管理域服务层：归集结算 + 发放额度 + 个人任务津贴。"""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..config import TaskConfig
from ..enums import SettlementStatus, SubmissionStatus, TaskStatus
from ..task.crud import AssignmentCRUD, SubmissionCRUD, TaskCRUD
from .crud import AllowanceCRUD, AllowanceDetailCRUD, PayoutConfigCRUD, SettlementCRUD, SettlementItemCRUD
from .schema import (
    AllowanceDetailOutSchema,
    AllowanceOutSchema,
    PayoutConfigCreateSchema,
    PayoutConfigOutSchema,
    PayoutConfigQueryParam,
    PayoutConfigUpdateSchema,
    SettlementOutSchema,
    SettlementQueryParam,
)

# 每月发放额度默认值（运营可调为 10000/20000）
DEFAULT_PAYOUT_LIMIT = Decimal("20000")


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

    async def settle(self, task_id: int, period: str) -> list[SettlementOutSchema]:
        """归集结算：汇总「任务 × 用户」下审核通过的成果，生成结算单 + 明细。

        规则：
        - 仅「已完成」（运营判定）的任务可归集结算；
        - 应发金额 payable = 单价 × 通过成果数量（无上限）；
        - 幂等：同一 task + user + period 已存在结算单则跳过。
        """
        task = await TaskCRUD(self.auth, self.db).get_or_404(id=task_id, preload=["template", "template.category"])
        if task.status != TaskStatus.COMPLETED.value:
            raise CustomException(msg="仅「已完成」的任务可归集结算（请先判定任务完成）")

        # 解析模板配置（unit/price），供结算明细使用
        config = TaskConfig.model_validate(task.template.config)
        unit = config.unit
        price = config.price if config.price is not None else Decimal("0")

        assignments = await AssignmentCRUD(self.auth, self.db).get_list(search={"task_id": task_id})
        results: list[SettlementOutSchema] = []

        for assignment in assignments:
            # 幂等：已存在同 task + user + period 的结算单则跳过
            if await SettlementCRUD(self.auth, self.db).get(task_id=task_id, user_id=assignment.user_id, period=period):
                continue

            approved_qty = await SubmissionCRUD(self.auth, self.db).count(
                assignment_id=assignment.id, status=SubmissionStatus.APPROVED.value, period=period
            )
            if approved_qty == 0:
                continue

            payable = price * approved_qty

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
            await SettlementItemCRUD(self.auth, self.db).create(
                data={
                    "settlement_id": settlement.id,
                    "category_name": task.template.category.name,
                    "template_name": task.template.name,
                    "unit": unit,
                    "price": price,
                    "qty": approved_qty,
                    "amount": payable,
                }
            )
            results.append(await self.detail(id=settlement.id))

        return results

    async def confirm(self, id: int) -> SettlementOutSchema:
        """确认结算单：PENDING / CALCULATED → CONFIRMED。"""
        settlement = await SettlementCRUD(self.auth, self.db).get_or_404(id=id)
        if settlement.status not in {SettlementStatus.PENDING.value, SettlementStatus.CALCULATED.value}:
            raise CustomException(msg="仅待结算/已计算的结算单可确认")
        await SettlementCRUD(self.auth, self.db).update(id=id, data={"status": SettlementStatus.CONFIRMED.value})
        return await self.detail(id=id)


class PayoutService:
    """发放服务：发放额度配置 CRUD + 津贴账户 / 明细查询。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

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
        """查询我的发放情况：发放额度、津贴余额、津贴明细。"""
        allowance = await AllowanceCRUD(self.auth, self.db).get(user_id=user_id)
        config = await PayoutConfigCRUD(self.auth, self.db).get(user_id=user_id, period=period)
        details = await AllowanceDetailCRUD(self.auth, self.db).get_list(
            search={"user_id": user_id}, order_by=[{"id": "asc"}]
        )
        return {
            "user_id": user_id,
            "period": period,
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
