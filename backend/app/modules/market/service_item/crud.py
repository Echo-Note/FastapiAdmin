from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import ServiceItemModel, ServiceItemTaskModel
from .schema import ServiceItemCreateSchema, ServiceItemUpdateSchema


class ServiceItemCRUD(MarketCRUDBase[ServiceItemModel, ServiceItemCreateSchema, ServiceItemUpdateSchema]):
    """对外服务项目价目数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ServiceItemModel, auth=auth, db=db)


class ServiceItemTaskCRUD(MarketCRUDBase[ServiceItemTaskModel, dict, dict]):
    """对内任务↔对外服务项目映射数据层（内部 CRUD 使用）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ServiceItemTaskModel, auth=auth, db=db)
