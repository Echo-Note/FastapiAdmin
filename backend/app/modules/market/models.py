"""market 域模型统一注册入口。

market 域模型间存在 ``TYPE_CHECKING`` 循环引用（如 assignment↔submission、task↔template），
SQLAlchemy 解析 ``relationship`` 字符串引用时依赖所有模型均已注册到 mapper registry。
正常启动由 ``routers.py`` 全量导入各 controller 触发注册；本模块供「独立加载模型集」的
场景（如成果导入服务、单元测试、命令行脚本）显式导入，避免 mapper 初始化失败。
"""

from .assignment.model import AssignmentModel
from .company.model import CompanyModel
from .institution.model import InstitutionModel
from .payout.model import AllowanceDetailModel, AllowanceModel, PayoutConfigModel
from .project.model import ProjectModel, ProjectTaskModel
from .report.model import ReportModel
from .service_item.model import ServiceItemModel, ServiceItemTaskModel
from .settlement.model import SettlementItemModel, SettlementModel
from .submission.model import SubmissionModel
from .task.model import TaskModel, TaskTypeModel
from .template.model import TemplateModel

__all__ = [
    "AllowanceDetailModel",
    "AllowanceModel",
    "AssignmentModel",
    "CompanyModel",
    "InstitutionModel",
    "PayoutConfigModel",
    "ProjectModel",
    "ProjectTaskModel",
    "ReportModel",
    "ServiceItemModel",
    "ServiceItemTaskModel",
    "SettlementItemModel",
    "SettlementModel",
    "SubmissionModel",
    "TaskModel",
    "TaskTypeModel",
    "TemplateModel",
]
