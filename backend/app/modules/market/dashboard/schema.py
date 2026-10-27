"""运营工作台统计响应模型。"""
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
    service_item_count: int = Field(0, description="服务项目数")
