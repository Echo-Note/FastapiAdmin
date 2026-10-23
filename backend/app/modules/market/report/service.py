from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..company.crud import CompanyCRUD
from ..enums import ReportStatus, SettlementStatus
from ..project.crud import ProjectCRUD, ProjectTaskCRUD
from ..settlement.crud import SettlementCRUD
from ..task.crud import TaskCRUD
from .crud import ReportCRUD
from .schema import ReportCreateSchema, ReportOutSchema, ReportQueryParam

# company 为 UserBySchema（含 created_by/updated_by），须嵌套预加载其审计关系，
# 避免 detail()/page() 序列化时在异步环境下触发懒加载 MissingGreenlet
_REPORT_PRELOAD = ["company", "company.created_by", "company.updated_by"]


class ReportService:
    """报告打包服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> ReportOutSchema:
        """查询报告详情。"""
        report = await ReportCRUD(self.auth, self.db).get_or_404(id=id, preload=_REPORT_PRELOAD)
        return ReportOutSchema.model_validate(report)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: ReportQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ReportOutSchema]:
        """分页查询报告。"""
        offset = (page_no - 1) * page_size
        return await ReportCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=ReportOutSchema,
            preload=_REPORT_PRELOAD,
        )

    async def generate(self, data: ReportCreateSchema) -> ReportOutSchema:
        """生成报告：按医药公司 × 周期汇总各项目下任务的完成量与结算金额。"""
        await CompanyCRUD(self.auth, self.db).get_or_404(id=data.company_id, msg="医药公司不存在")

        # 该周期下该医药公司的所有项目
        projects = await ProjectCRUD(self.auth, self.db).get_list(
            search={"company_id": data.company_id, "period": data.period}
        )
        if not projects:
            raise CustomException(msg="该周期下该医药公司无项目数据")

        # 这些项目归集的所有任务（跨项目去重）
        project_ids = [p.id for p in projects]
        links = await ProjectTaskCRUD(self.auth, self.db).get_list(search={"project_id": ("in", project_ids)})
        task_ids = list({link.task_id for link in links})
        if not task_ids:
            raise CustomException(msg="该周期下该医药公司无任务数据")

        tasks = await TaskCRUD(self.auth, self.db).get_list(search={"id": ("in", task_ids)}, preload=["task_type"])

        task_summary: list[dict[str, Any]] = []
        total_qty = 0
        total_amount = Decimal(0)
        for task in tasks:
            # 汇总该任务下的结算单
            settlements = await SettlementCRUD(self.auth, self.db).get_list(
                search={"task_id": task.id, "status": SettlementStatus.CALCULATED.value}
            )
            qty = sum(s.qty for s in settlements)
            amount = sum((Decimal(s.payable_amount) for s in settlements), Decimal(0))
            total_qty += qty
            total_amount += amount
            task_summary.append(
                {
                    "task_no": task.task_no,
                    "service_type": task.task_type.service_type,
                    "service_item": task.task_type.service_item,
                    "service_task": task.task_type.service_task,
                    "qty": qty,
                    "amount": float(amount),
                }
            )

        summary: dict[str, Any] = {
            "tasks": task_summary,
            "total_qty": total_qty,
            "total_amount": float(total_amount),
        }

        report = await ReportCRUD(self.auth, self.db).create(
            data={
                "company_id": data.company_id,
                "period": data.period,
                "summary": summary,
                "status": ReportStatus.GENERATED.value,
            }
        )
        return await self.detail(id=report.id)
