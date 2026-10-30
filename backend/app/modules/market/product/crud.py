"""产品库 CRUD 层（继承 ``MarketCRUDBase``，数据范围由 Service 层显式控制）。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import ProductModel
from .schema import ProductCreateSchema, ProductUpdateSchema


class ProductCRUD(MarketCRUDBase[ProductModel, ProductCreateSchema, ProductUpdateSchema]):
    """产品库数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ProductModel, auth=auth, db=db)
