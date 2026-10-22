from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import ReportModel
from .schema import ReportCreateSchema


class ReportCRUD(MarketCRUDBase[ReportModel, ReportCreateSchema, dict[str, Any]]):
    """报告数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=ReportModel, auth=auth, db=db)
