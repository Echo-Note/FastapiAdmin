from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import SettlementItemModel, SettlementModel


class SettlementCRUD(MarketCRUDBase[SettlementModel, dict[str, Any], dict[str, Any]]):
    """结算单数据层（结算单由系统归集生成，无对外创建/更新模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SettlementModel, auth=auth, db=db)


class SettlementItemCRUD(MarketCRUDBase[SettlementItemModel, dict[str, Any], dict[str, Any]]):
    """结算明细数据层（明细随结算单生成，无对外模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SettlementItemModel, auth=auth, db=db)

