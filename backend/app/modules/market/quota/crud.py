from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import QuotaCarryoverModel, QuotaConfigModel, QuotaUsageModel
from .schema import QuotaConfigCreateSchema, QuotaConfigUpdateSchema


class QuotaConfigCRUD(MarketCRUDBase[QuotaConfigModel, QuotaConfigCreateSchema, QuotaConfigUpdateSchema]):
    """限额配置数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=QuotaConfigModel, auth=auth, db=db)


class QuotaUsageCRUD(MarketCRUDBase[QuotaUsageModel, dict[str, Any], dict[str, Any]]):
    """限额使用数据层（系统累计，无对外模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=QuotaUsageModel, auth=auth, db=db)


class QuotaCarryoverCRUD(MarketCRUDBase[QuotaCarryoverModel, dict[str, Any], dict[str, Any]]):
    """顺延金额数据层（系统生成，无对外模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=QuotaCarryoverModel, auth=auth, db=db)
