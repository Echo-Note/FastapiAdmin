from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import CompanyCreateSchema, CompanyOutSchema, CompanyQueryParam, CompanyUpdateSchema
from .service import CompanyService

CompanyRouter = APIRouter(route_class=OperationLogRoute, prefix="/companies", tags=["市场-医药公司"])


@CompanyRouter.get("/list", summary="查询医药公司", response_model=ResponseSchema[PageResultSchema[CompanyOutSchema]])
async def get_company_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:company:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CompanyQueryParam, Query()],
) -> JSONResponse:
    result = await CompanyService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询医药公司成功")


@CompanyRouter.get("/detail/{id}", summary="查询医药公司详情", response_model=ResponseSchema[CompanyOutSchema])
async def get_company_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:company:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="医药公司ID", ge=1)],
) -> JSONResponse:
    result = await CompanyService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取医药公司详情成功")


@CompanyRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建医药公司", response_model=ResponseSchema[CompanyOutSchema])
async def create_company_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:company:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[CompanyCreateSchema, Body(description="创建医药公司参数")],
) -> JSONResponse:
    result = await CompanyService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建医药公司成功")


@CompanyRouter.put("/update/{id}", summary="修改医药公司", response_model=ResponseSchema[CompanyOutSchema])
async def update_company_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:company:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="医药公司ID", ge=1)],
    data: Annotated[CompanyUpdateSchema, Body(description="修改医药公司参数")],
) -> JSONResponse:
    result = await CompanyService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改医药公司成功")


@CompanyRouter.delete("/delete", summary="删除医药公司", response_model=ResponseSchema[None])
async def delete_company_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:company:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await CompanyService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除医药公司成功")
