from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import InstitutionModel
from .schema import InstitutionCreateSchema, InstitutionUpdateSchema


class InstitutionCRUD(MarketCRUDBase[InstitutionModel, InstitutionCreateSchema, InstitutionUpdateSchema]):
    """机构数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=InstitutionModel, auth=auth, db=db)
