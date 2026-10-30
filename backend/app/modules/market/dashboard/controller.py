"""运营工作台（市场数据概览）接口层。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import DashboardInsightsSchema, DashboardOverviewSchema
from .service import DashboardService

DashboardRouter = APIRouter(route_class=OperationLogRoute, prefix="/dashboard", tags=["市场-运营工作台"])


@DashboardRouter.get(
    "/overview",
    summary="运营工作台概览",
    response_model=ResponseSchema[DashboardOverviewSchema],
)
async def get_dashboard_overview(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:dashboard:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DashboardService(auth, db).overview()
    return SuccessResponse(data=result, msg="查询运营工作台概览成功")


@DashboardRouter.get(
    "/insights",
    summary="运营工作台明细（趋势 + 待办队列）",
    response_model=ResponseSchema[DashboardInsightsSchema],
)
async def get_dashboard_insights(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:dashboard:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DashboardService(auth, db).insights()
    return SuccessResponse(data=result, msg="查询运营工作台明细成功")
