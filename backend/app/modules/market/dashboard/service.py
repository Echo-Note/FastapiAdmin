"""运营工作台（市场数据概览）统计服务。

统计口径：所有指标均排除软删除记录（``is_deleted == False``），
统计对象基于重写后的新模型（项目/公司/机构/一级分类/二级模板/任务/成果/结算）。
"""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.modules.market.enums import SubmissionStatus, TaskStatus
from app.modules.market.models import (
    AssignmentModel,
    CompanyModel,
    InstitutionModel,
    ProjectModel,
    SettlementModel,
    SubmissionModel,
    TaskCategoryModel,
    TaskModel,
    TaskTemplateModel,
)

from .schema import (
    DashboardInsightsSchema,
    DashboardOverviewSchema,
    PendingSubmissionRowSchema,
    SettlementStatSchema,
    SubmissionStatSchema,
    SubmissionTrendPointSchema,
    TaskStatSchema,
)

# 运营端统计的「一天」以北京时间切分（与 ap_scheduler 的时区一致）；库里的时间戳存 UTC
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

TREND_DAYS = 14
QUEUE_LIMIT = 8
SUBJECT_FALLBACK = "未填写对象"

# 成果状态 → 趋势图三分类（草稿不计入趋势，与「待审/通过/驳回」口径一致）
_TREND_BUCKET: dict[str, str] = {
    SubmissionStatus.PENDING.value: "pending",
    SubmissionStatus.APPROVED.value: "approved",
    SubmissionStatus.REJECTED.value: "rejected",
}


def _as_local_day(moment: datetime) -> date:
    """把库里的时间转成北京时间日历日。

    SQLite（测试库）返回的是 naive datetime，按 UTC 解释后再转本地；
    直接 ``astimezone()`` 会误以为是服务器本地时区。
    """
    aware = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return aware.astimezone(LOCAL_TZ).date()


def build_trend(
    rows: Iterable[tuple[datetime, str]], days: list[date]
) -> list[SubmissionTrendPointSchema]:
    """按本地日期把成果提交分桶，缺失日补 0。

    聚合放在 Python 而不是 SQL：``date_trunc`` / ``AT TIME ZONE`` 是 PG 专有
    （测试库是 SQLite），且「一天从哪儿切」显式写在代码里比埋在 SQL 里可读。
    窗口已由调用方用 ``created_time >= start`` 限好，行数很小。
    """
    buckets: dict[date, dict[str, int]] = {
        day: {"pending": 0, "approved": 0, "rejected": 0} for day in days
    }
    for created_time, status in rows:
        bucket = buckets.get(_as_local_day(created_time))
        key = _TREND_BUCKET.get(status)
        if bucket is None or key is None:
            continue
        bucket[key] += 1

    return [
        SubmissionTrendPointSchema(date=day.isoformat(), **buckets[day]) for day in days
    ]


class DashboardService:
    """运营工作台统计"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def overview(self) -> DashboardOverviewSchema:
        """汇总市场域核心统计指标（均排除软删除记录）。"""
        db = self.db

        # 任务：总数 + 按状态分组（进行中/已完成/已结算）
        task_total = await db.scalar(
            select(func.count()).select_from(TaskModel).where(TaskModel.is_deleted.is_(False))
        )
        task_rows = dict(
            (
                await db.execute(
                    select(TaskModel.status, func.count())
                    .where(TaskModel.is_deleted.is_(False))
                    .group_by(TaskModel.status)
                )
            ).all()
        )

        # 成果：总数 + 按状态分组（待审核/通过/驳回）
        submission_total = await db.scalar(
            select(func.count()).select_from(SubmissionModel).where(SubmissionModel.is_deleted.is_(False))
        )
        submission_rows = dict(
            (
                await db.execute(
                    select(SubmissionModel.status, func.count())
                    .where(SubmissionModel.is_deleted.is_(False))
                    .group_by(SubmissionModel.status)
                )
            ).all()
        )

        # 结算：总数 + 应发金额合计
        settlement_total = await db.scalar(
            select(func.count()).select_from(SettlementModel).where(SettlementModel.is_deleted.is_(False))
        )
        payable_amount = await db.scalar(
            select(func.coalesce(func.sum(SettlementModel.payable_amount), 0)).where(
                SettlementModel.is_deleted.is_(False)
            )
        )

        # 基础数据计数
        project_count = await db.scalar(
            select(func.count()).select_from(ProjectModel).where(ProjectModel.is_deleted.is_(False))
        )
        company_count = await db.scalar(
            select(func.count()).select_from(CompanyModel).where(CompanyModel.is_deleted.is_(False))
        )
        institution_count = await db.scalar(
            select(func.count()).select_from(InstitutionModel).where(InstitutionModel.is_deleted.is_(False))
        )
        category_count = await db.scalar(
            select(func.count()).select_from(TaskCategoryModel).where(TaskCategoryModel.is_deleted.is_(False))
        )
        template_count = await db.scalar(
            select(func.count()).select_from(TaskTemplateModel).where(TaskTemplateModel.is_deleted.is_(False))
        )

        return DashboardOverviewSchema(
            task=TaskStatSchema(
                total=task_total or 0,
                in_progress=task_rows.get(TaskStatus.IN_PROGRESS.value, 0),
                completed=task_rows.get(TaskStatus.COMPLETED.value, 0),
                settled=task_rows.get(TaskStatus.SETTLED.value, 0),
            ),
            submission=SubmissionStatSchema(
                total=submission_total or 0,
                # 「待审核」= PENDING，并兼容历史 DRAFT 数据（提交动作在 2026-11 前写的是 DRAFT）
                pending=submission_rows.get(SubmissionStatus.PENDING.value, 0)
                + submission_rows.get(SubmissionStatus.DRAFT.value, 0),
                approved=submission_rows.get(SubmissionStatus.APPROVED.value, 0),
                rejected=submission_rows.get(SubmissionStatus.REJECTED.value, 0),
            ),
            settlement=SettlementStatSchema(
                total=settlement_total or 0,
                payable_amount=float(payable_amount or 0),
            ),
            project_count=project_count or 0,
            company_count=company_count or 0,
            institution_count=institution_count or 0,
            category_count=category_count or 0,
            template_count=template_count or 0,
        )

    async def insights(self) -> DashboardInsightsSchema:
        """近 14 天成果提交趋势 + 最新待审核成果队列。

        趋势按「提交时间」分桶，而非审核时间：它回答的是「这两天提交量怎么变」，
        与上面按当前状态统计的分布条互补。
        """
        db = self.db

        # 本地（北京时间）今天往前 13 天 00:00 起算，换算成 UTC 下推给查询
        today_local = datetime.now(LOCAL_TZ).date()
        days = [today_local - timedelta(days=offset) for offset in range(TREND_DAYS - 1, -1, -1)]
        window_start = datetime.combine(days[0], time.min, tzinfo=LOCAL_TZ).astimezone(UTC)

        trend_rows = (
            await db.execute(
                select(SubmissionModel.created_time, SubmissionModel.status).where(
                    SubmissionModel.is_deleted.is_(False),
                    SubmissionModel.created_time >= window_start,
                )
            )
        ).all()

        queue_rows = (
            await db.execute(
                select(
                    SubmissionModel.id,
                    SubmissionModel.period,
                    SubmissionModel.created_time,
                    SubmissionModel.subject_name,
                    InstitutionModel.name.label("institution_name"),
                    TaskModel.name.label("task_name"),
                )
                .join(AssignmentModel, AssignmentModel.id == SubmissionModel.assignment_id)
                .join(TaskModel, TaskModel.id == AssignmentModel.task_id)
                # 机构被软删除时仍保留队列行（退回 subject_name），所以过滤放进 ON 而不是 WHERE
                .outerjoin(
                    InstitutionModel,
                    and_(
                        InstitutionModel.id == SubmissionModel.institution_id,
                        InstitutionModel.is_deleted.is_(False),
                    ),
                )
                .where(
                    SubmissionModel.is_deleted.is_(False),
                    AssignmentModel.is_deleted.is_(False),
                    TaskModel.is_deleted.is_(False),
                    SubmissionModel.status.in_(
                        [SubmissionStatus.PENDING.value, SubmissionStatus.DRAFT.value]
                    ),
                )
                .order_by(SubmissionModel.created_time.desc())
                .limit(QUEUE_LIMIT)
            )
        ).all()

        return DashboardInsightsSchema(
            submission_trend=build_trend(trend_rows, days),
            pending_submissions=[
                PendingSubmissionRowSchema(
                    id=row.id,
                    subject=row.institution_name or row.subject_name or SUBJECT_FALLBACK,
                    task_name=row.task_name or "",
                    period=row.period,
                    created_at=(row.created_time if row.created_time.tzinfo else row.created_time.replace(tzinfo=UTC))
                    .astimezone(LOCAL_TZ)
                    .isoformat(),
                )
                for row in queue_rows
            ],
        )
