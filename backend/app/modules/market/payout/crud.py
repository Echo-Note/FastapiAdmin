"""发放额度与个人任务津贴的数据访问层。"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import AllowanceDetailModel, AllowanceModel, PayoutConfigModel
from .schema import PayoutConfigCreateSchema, PayoutConfigUpdateSchema


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


__all__ = ["PayoutConfigCRUD", "AllowanceCRUD", "AllowanceDetailCRUD"]
