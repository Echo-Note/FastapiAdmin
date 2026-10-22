from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import InstitutionCreateSchema, InstitutionOutSchema, InstitutionQueryParam, InstitutionUpdateSchema
from .service import InstitutionService

InstitutionRouter = APIRouter(route_class=OperationLogRoute, prefix="/institutions", tags=["市场-机构"])


@InstitutionRouter.get("/list", summary="查询机构", response_model=ResponseSchema[PageResultSchema[InstitutionOutSchema]])
async def get_institution_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[InstitutionQueryParam, Query()],
) -> JSONResponse:
    result = await InstitutionService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询机构成功")


@InstitutionRouter.get("/detail/{id}", summary="查询机构详情", response_model=ResponseSchema[InstitutionOutSchema])
async def get_institution_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="机构ID", ge=1)],
) -> JSONResponse:
    result = await InstitutionService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取机构详情成功")


@InstitutionRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建机构", response_model=ResponseSchema[InstitutionOutSchema])
async def create_institution_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[InstitutionCreateSchema, Body(description="创建机构参数")],
) -> JSONResponse:
    result = await InstitutionService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建机构成功")


@InstitutionRouter.put("/update/{id}", summary="修改机构", response_model=ResponseSchema[InstitutionOutSchema])
async def update_institution_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="机构ID", ge=1)],
    data: Annotated[InstitutionUpdateSchema, Body(description="修改机构参数")],
) -> JSONResponse:
    result = await InstitutionService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改机构成功")


@InstitutionRouter.delete("/delete", summary="删除机构", response_model=ResponseSchema[None])
async def delete_institution_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await InstitutionService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除机构成功")
