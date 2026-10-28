"""运营工作台（市场数据概览）统计服务。

统计口径：所有指标均排除软删除记录（``is_deleted == False``），
统计对象基于重写后的新模型（项目/公司/机构/一级分类/二级模板/任务/成果/结算）。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.modules.market.enums import SubmissionStatus, TaskStatus
from app.modules.market.models import (
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
    DashboardOverviewSchema,
    SettlementStatSchema,
    SubmissionStatSchema,
    TaskStatSchema,
)


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
                pending=submission_rows.get(SubmissionStatus.PENDING.value, 0),
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
