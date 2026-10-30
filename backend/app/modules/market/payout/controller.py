"""发放管理域接口层：归集结算 + 发放额度 + 个人任务津贴。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    AllowanceDetailOutSchema,
    AllowanceOutSchema,
    PayoutConfigCreateSchema,
    PayoutConfigOutSchema,
    PayoutConfigQueryParam,
    PayoutConfigUpdateSchema,
    PayoutResultOutSchema,
    PayoutResultQueryParam,
    SettlementOutSchema,
    SettlementQueryParam,
)
from .service import AllowanceService, PayoutService, SettlementService

SettlementRouter = APIRouter(route_class=OperationLogRoute, prefix="/settlements", tags=["市场-结算"])
PayoutRouter = APIRouter(route_class=OperationLogRoute, prefix="/payout", tags=["市场-发放"])


@SettlementRouter.get("/list", summary="查询结算单", response_model=ResponseSchema[PageResultSchema[SettlementOutSchema]])
async def get_settlement_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SettlementQueryParam, Query()],
) -> JSONResponse:
    result = await SettlementService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询结算单成功")


@SettlementRouter.get("/detail/{id}", summary="查询结算单详情", response_model=ResponseSchema[SettlementOutSchema])
async def get_settlement_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="结算单ID", ge=1)],
) -> JSONResponse:
    result = await SettlementService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取结算单详情成功")


@SettlementRouter.post("/settle", summary="归集结算", response_model=ResponseSchema[list[SettlementOutSchema]])
async def settle_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:run"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    task_id: Annotated[int, Body(description="任务ID", ge=1, embed=True)],
    period: Annotated[str, Body(description="结算月份(如 2026-03)", embed=True)],
) -> JSONResponse:
    result = await SettlementService(auth, db).settle(task_id=task_id, period=period)
    return SuccessResponse(data=result, msg="归集结算成功")


@SettlementRouter.post("/confirm/{id}", summary="确认结算单", response_model=ResponseSchema[SettlementOutSchema])
async def confirm_settlement_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:confirm"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="结算单ID", ge=1)],
) -> JSONResponse:
    result = await SettlementService(auth, db).confirm(id=id)
    return SuccessResponse(data=result, msg="确认结算单成功")


@PayoutRouter.get("/list", summary="查询发放额度配置", response_model=ResponseSchema[PageResultSchema[PayoutConfigOutSchema]])
async def get_payout_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[PayoutConfigQueryParam, Query()],
) -> JSONResponse:
    result = await PayoutService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询发放额度配置成功")


@PayoutRouter.get("/results", summary="查询发放结果", response_model=ResponseSchema[PageResultSchema[PayoutResultOutSchema]])
async def get_payout_results_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[PayoutResultQueryParam, Query()],
) -> JSONResponse:
    result = await PayoutService(auth, db).results(
        page_no=page.page_no, page_size=page.page_size, user_id=search.user_id, period=search.period
    )
    return SuccessResponse(data=result, msg="查询发放结果成功")


@PayoutRouter.get("/detail/{id}", summary="查询发放额度配置详情", response_model=ResponseSchema[PayoutConfigOutSchema])
async def get_payout_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="配置ID", ge=1)],
) -> JSONResponse:
    result = await PayoutService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取发放额度配置详情成功")


@PayoutRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建发放额度配置", response_model=ResponseSchema[PayoutConfigOutSchema])
async def create_payout_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[PayoutConfigCreateSchema, Body(description="创建发放额度配置参数")],
) -> JSONResponse:
    result = await PayoutService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建发放额度配置成功")


@PayoutRouter.put("/update/{id}", summary="修改发放额度配置", response_model=ResponseSchema[PayoutConfigOutSchema])
async def update_payout_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="配置ID", ge=1)],
    data: Annotated[PayoutConfigUpdateSchema, Body(description="修改发放额度配置参数")],
) -> JSONResponse:
    result = await PayoutService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改发放额度配置成功")


@PayoutRouter.delete("/delete", summary="删除发放额度配置", response_model=ResponseSchema[None])
async def delete_payout_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await PayoutService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除发放额度配置成功")


@PayoutRouter.get("/allowance", summary="查询津贴账户", response_model=ResponseSchema[PageResultSchema[AllowanceOutSchema]])
async def get_allowance_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    result = await AllowanceService(auth, db).page(page_no=page.page_no, page_size=page.page_size, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询津贴账户成功")


@PayoutRouter.get("/allowance/detail", summary="查询津贴明细", response_model=ResponseSchema[PageResultSchema[AllowanceDetailOutSchema]])
async def get_allowance_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:payout:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    user_id: Annotated[int | None, Query(description="C端用户ID", ge=1)] = None,
) -> JSONResponse:
    result = await AllowanceService(auth, db).detail_page(page_no=page.page_no, page_size=page.page_size, user_id=user_id, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询津贴明细成功")
