"""一次性脚本：为「历史已通过成果」补做归集结算 + 发放核算。

背景：2026-11 起 `SubmissionService.review` 在审核通过时自动归集；这个能力只对**之后**的
审核生效——在此之前已审通过的成果不会自动补结算单，于是「结算管理」「发放管理」看起来是空的。
本脚本把库里所有 `status=APPROVED` 的成果按 `(任务, 月份)` 重放一次归集，等价于运营逐条点
「归集结算」，只是**跳过任务必须 COMPLETED 的前置**（历史任务可能还停在 PUBLISHED）。

幂等：`settle` 本身是重算语义，重复执行结果一致（金额不叠加、不新增重复结算单）。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.backfill_settlement            # 只打印将处理的分组
    PYTHONPATH=. uv run python -m app.scripts.backfill_settlement --apply    # 真正落库
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.base_model import MappedBase
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.database import async_db_session
from app.modules.market.payout.service import SettlementService
from app.modules.market.task.model import AssignmentModel, SubmissionModel
from app.utils.import_util import ImportUtil

# 全量注册模型：确保 relationship 字符串引用可解析
_ = ImportUtil.find_models(MappedBase)


async def _pending_groups(db) -> list[tuple[int, str]]:
    """返回库中所有「有已通过成果」的 ``(task_id, period)`` 分组（去重、稳定排序）。"""
    stmt = (
        select(AssignmentModel.task_id, SubmissionModel.period)
        .join(AssignmentModel, AssignmentModel.id == SubmissionModel.assignment_id)
        .where(
            SubmissionModel.is_deleted.is_(False),
            SubmissionModel.status == "APPROVED",
        )
        .group_by(AssignmentModel.task_id, SubmissionModel.period)
        .order_by(AssignmentModel.task_id, SubmissionModel.period)
    )
    return [(row[0], row[1]) for row in (await db.execute(stmt)).all()]


async def backfill(*, apply: bool) -> int:
    """按 ``(task_id, period)`` 逐组归集；返回成功处理的组数。"""
    handled = 0
    async with async_db_session() as db, db.begin():
        groups = await _pending_groups(db)
        if not groups:
            print("✅ 没有「已通过成果」需要补归集")
            return 0

        # 以超管身份执行：CRUD 只把 auth.user.id 记为 created_id/updated_id
        auth = AuthSchema(user=CoreUserSchema(id=1, username="system", name="系统补算"))
        service = SettlementService(auth, db)
        for task_id, period in groups:
            if not apply:
                print(f"[dry-run] 将补归集 任务#{task_id} 月份={period}")
                handled += 1
                continue
            results = await service.settle(task_id=task_id, period=period, require_completed=False)
            for item in results:
                print(
                    f"✅ 任务#{task_id} 月份={period} 用户#{item.user_id} "
                    f"数量={item.qty} 应发={item.payable_amount} 实发={item.paid_amount}"
                )
            handled += 1
    print(f"{'' if apply else '[dry-run] '}✅ 共处理 {handled} 个「任务 × 月份」分组")
    return handled


def main() -> None:
    parser = argparse.ArgumentParser(description="为历史已通过成果补做归集结算与发放核算")
    parser.add_argument("--apply", action="store_true", help="真正写库；缺省只打印将处理的分组")
    args = parser.parse_args()
    asyncio.run(backfill(apply=args.apply))


if __name__ == "__main__":
    main()
