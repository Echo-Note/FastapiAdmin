"""给「历史上已经在用 C 端功能」的用户补建成员档案。

**为什么需要**：``market_member`` 上线后，C 端接口首访会自动建档，但存量用户只有在**下一次
访问**时才会有档案——运营打开成员管理页会看到一张空表，误以为没数据。

本脚本按**行为证据**回填：凡是曾经接过单、提交过成果或产生过津贴/结算记录的用户，
都视为 C 端成员并建档（这是能拿到的唯一可靠证据；系统没有保存过「谁是 C 端」的字段）。

幂等：已建档用户跳过，重复执行结果一致。

用法（backend 目录下）：

    PYTHONPATH=. uv run python -m app.scripts.backfill_member            # dry-run
    PYTHONPATH=. uv run python -m app.scripts.backfill_member --apply    # 落库
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.base_model import MappedBase
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.database import async_db_session
from app.modules.market.member.model import MemberModel
from app.modules.market.member.service import MemberService
from app.modules.market.payout.model import AllowanceDetailModel, AllowanceModel, SettlementModel
from app.modules.market.task.model import AssignmentModel, SubmissionModel
from app.utils.import_util import ImportUtil

_ = ImportUtil.find_models(MappedBase)

# 能证明「这个用户是 C 端」的行为来源（取 user_id 并集）
_EVIDENCE = (
    select(AssignmentModel.user_id).where(AssignmentModel.is_deleted.is_(False)),
    select(SubmissionModel.user_id).where(SubmissionModel.is_deleted.is_(False)),
    select(SettlementModel.user_id).where(SettlementModel.is_deleted.is_(False)),
    select(AllowanceModel.user_id).where(AllowanceModel.is_deleted.is_(False)),
    select(AllowanceDetailModel.user_id).where(AllowanceDetailModel.is_deleted.is_(False)),
)


async def backfill(*, apply: bool) -> int:
    """给行为证据命中的用户补建档，返回本次（将）新建的档案数。"""
    created = 0
    async with async_db_session() as db, db.begin():
        user_ids = sorted({row for stmt in _EVIDENCE for row in (await db.execute(stmt)).scalars()})
        if not user_ids:
            print("✅ 没有任何 C 端行为记录，无需回填")
            return 0

        existing = set((await db.execute(select(MemberModel.user_id))).scalars())
        pending = [uid for uid in user_ids if uid not in existing]
        if not pending:
            print(f"✅ 命中的 {len(user_ids)} 个用户都已有成员档案，无需回填")
            return 0

        auth = AuthSchema(user=CoreUserSchema(id=1, username="system", name="系统回填"))
        service = MemberService(auth, db)
        for user_id in pending:
            if not apply:
                print(f"[dry-run] 将为用户#{user_id} 建档")
                created += 1
                continue
            member = await service.ensure_for_user(user_id)
            print(f"✅ 用户#{user_id} → 成员 {member.member_no}")
            created += 1

    print(f"{'' if apply else '[dry-run] '}✅ 共处理 {created} 个用户")
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="给历史 C 端用户补建 market_member 档案")
    parser.add_argument("--apply", action="store_true", help="真正写库；缺省只打印将建档的用户")
    args = parser.parse_args()
    asyncio.run(backfill(apply=args.apply))


if __name__ == "__main__":
    main()
