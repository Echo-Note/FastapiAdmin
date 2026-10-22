from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import CompanyModel
from .schema import CompanyCreateSchema, CompanyUpdateSchema


class CompanyCRUD(MarketCRUDBase[CompanyModel, CompanyCreateSchema, CompanyUpdateSchema]):
    """医药公司数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=CompanyModel, auth=auth, db=db)
