"""运营工作台（市场数据概览）统计响应模型。"""

from pydantic import BaseModel, Field


class TaskStatSchema(BaseModel):
    """任务统计"""

    total: int = Field(0, description="任务总数")
    in_progress: int = Field(0, description="进行中任务数")
    completed: int = Field(0, description="已完成任务数")
    settled: int = Field(0, description="已结算任务数")


class SubmissionStatSchema(BaseModel):
    """成果统计"""

    total: int = Field(0, description="成果总数")
    pending: int = Field(0, description="待审核成果数")
    approved: int = Field(0, description="已通过成果数")
    rejected: int = Field(0, description="已驳回成果数")


class SettlementStatSchema(BaseModel):
    """结算统计"""

    total: int = Field(0, description="结算单总数")
    payable_amount: float = Field(0, description="应发金额合计")


class DashboardOverviewSchema(BaseModel):
    """运营工作台概览"""

    task: TaskStatSchema = Field(description="任务统计")
    submission: SubmissionStatSchema = Field(description="成果统计")
    settlement: SettlementStatSchema = Field(description="结算统计")
    project_count: int = Field(0, description="项目数")
    company_count: int = Field(0, description="医药公司数")
    institution_count: int = Field(0, description="机构数")
    category_count: int = Field(0, description="一级任务分类数")
    template_count: int = Field(0, description="二级任务模板数")


class SubmissionTrendPointSchema(BaseModel):
    """成果提交量趋势点（一天一桶）"""

    date: str = Field(description="本地日期(YYYY-MM-DD，Asia/Shanghai)")
    pending: int = Field(0, description="当天提交且当前待审核")
    approved: int = Field(0, description="当天提交且当前已通过")
    rejected: int = Field(0, description="当天提交且当前已驳回")


class PendingSubmissionRowSchema(BaseModel):
    """待审核成果队列行（首页只展示判断所需的四个字段，不带采集表单）"""

    id: int = Field(description="成果ID")
    subject: str = Field(description="采集对象名称(机构名 → 对象名 → 未填写对象)")
    task_name: str = Field(description="任务名称")
    period: str = Field(description="所属月份(如 2026-03)")
    created_at: str = Field(description="提交时间(ISO8601，带 +08:00)")


class DashboardInsightsSchema(BaseModel):
    """运营工作台明细洞察：趋势 + 待办队列"""

    submission_trend: list[SubmissionTrendPointSchema] = Field(
        default_factory=list, description="近 14 天成果提交量(由旧到新，固定 14 点)"
    )
    pending_submissions: list[PendingSubmissionRowSchema] = Field(
        default_factory=list, description="最新待审核成果(最多 8 条)"
    )


__all__ = [
    "DashboardInsightsSchema",
    "DashboardOverviewSchema",
    "PendingSubmissionRowSchema",
    "SettlementStatSchema",
    "SubmissionStatSchema",
    "SubmissionTrendPointSchema",
    "TaskStatSchema",
]
