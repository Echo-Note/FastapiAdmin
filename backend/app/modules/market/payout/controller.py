"""发放额度与个人任务津贴的接口层。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import PayoutConfigCreateSchema, PayoutConfigOutSchema, PayoutQueryParam
from .service import PayoutService

PayoutRouter = APIRouter(route_class=OperationLogRoute, prefix="/payout", tags=["市场-发放"])


@PayoutRouter.get("/list", summary="查询发放额度配置", response_model=ResponseSchema[PageResultSchema[PayoutConfigOutSchema]])
async def get_payout_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[PayoutQueryParam, Query()],
) -> JSONResponse:
    result = await PayoutService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询发放额度配置成功")


@PayoutRouter.post("/save", summary="配置每月发放额度(创建或更新)", response_model=ResponseSchema[PayoutConfigOutSchema])
async def save_payout_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:edit"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[PayoutConfigCreateSchema, Body(description="发放额度配置参数")],
) -> JSONResponse:
    result = await PayoutService(auth, db).save_config(data=data)
    return SuccessResponse(data=result, msg="配置发放额度成功")


@PayoutRouter.get("/usage", summary="查询发放情况", response_model=ResponseSchema[dict])
async def get_payout_usage_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Query(description="C端用户ID", ge=1)],
    period: Annotated[str, Query(description="周期(如 2026-10)")],
) -> JSONResponse:
    result = await PayoutService(auth, db).my_payout(user_id=user_id, period=period)
    return SuccessResponse(data=result, msg="查询发放情况成功")
