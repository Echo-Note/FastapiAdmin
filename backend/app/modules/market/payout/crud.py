"""发放管理域数据访问层。"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import AllowanceDetailModel, AllowanceModel, PayoutConfigModel, SettlementItemModel, SettlementModel
from .schema import PayoutConfigCreateSchema, PayoutConfigUpdateSchema


class SettlementCRUD(MarketCRUDBase[SettlementModel, dict[str, Any], dict[str, Any]]):
    """结算单数据层（结算单由系统归集生成，无对外创建/更新模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SettlementModel, auth=auth, db=db)


class SettlementItemCRUD(MarketCRUDBase[SettlementItemModel, dict[str, Any], dict[str, Any]]):
    """结算明细数据层（明细随结算单生成，无对外模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=SettlementItemModel, auth=auth, db=db)


class PayoutConfigCRUD(MarketCRUDBase[PayoutConfigModel, PayoutConfigCreateSchema, PayoutConfigUpdateSchema]):
    """发放额度配置数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=PayoutConfigModel, auth=auth, db=db)


class AllowanceCRUD(MarketCRUDBase[AllowanceModel, dict[str, Any], dict[str, Any]]):
    """个人任务津贴账户数据层（系统累计，无对外模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=AllowanceModel, auth=auth, db=db)


class AllowanceDetailCRUD(MarketCRUDBase[AllowanceDetailModel, dict[str, Any], dict[str, Any]]):
    """津贴明细数据层（系统生成，无对外模型）"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=AllowanceDetailModel, auth=auth, db=db)


__all__ = ["SettlementCRUD", "SettlementItemCRUD", "PayoutConfigCRUD", "AllowanceCRUD", "AllowanceDetailCRUD"]
