from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import TemplateModel
from .schema import TemplateCreateSchema, TemplateUpdateSchema


class TemplateCRUD(MarketCRUDBase[TemplateModel, TemplateCreateSchema, TemplateUpdateSchema]):
    """采集模板数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=TemplateModel, auth=auth, db=db)
