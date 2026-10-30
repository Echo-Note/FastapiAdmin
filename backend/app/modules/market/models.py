"""market 域模型统一注册入口。

market 域模型间存在 ``TYPE_CHECKING`` 循环引用（如 task↔project↔payout↔institution），
SQLAlchemy 解析 ``relationship`` 字符串引用时依赖所有模型均已注册到 mapper registry。
正常启动由 ``routers.py`` 全量导入各 controller 触发注册；本模块供「独立加载模型集」的
场景（脚本、单元测试）显式导入，避免 mapper 初始化失败。
"""

from .institution.model import InstitutionImageModel, InstitutionModel
from .member.model import MemberModel
from .numbering import MarketNumberCounterModel
from .payout.model import (
    AllowanceDetailModel,
    AllowanceModel,
    PayoutConfigModel,
    SettlementItemModel,
    SettlementModel,
)
from .product.model import ProductModel
from .project.model import CompanyModel, ProjectItemModel, ProjectModel, ReportModel
from .task.model import (
    AssignmentModel,
    SubmissionModel,
    TaskCategoryModel,
    TaskItemModel,
    TaskModel,
    TaskTemplateModel,
)

__all__ = [
    "AllowanceDetailModel",
    "AllowanceModel",
    "AssignmentModel",
    "CompanyModel",
    "InstitutionImageModel",
    "InstitutionModel",
    "MarketNumberCounterModel",
    "MemberModel",
    "PayoutConfigModel",
    "ProductModel",
    "ProjectModel",
    "ProjectItemModel",
    "ReportModel",
    "SettlementItemModel",
    "SettlementModel",
    "SubmissionModel",
    "TaskCategoryModel",
    "TaskItemModel",
    "TaskModel",
    "TaskTemplateModel",
]
