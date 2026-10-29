from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter, redis_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    InstitutionImageCreateSchema,
    InstitutionImageOutSchema,
    InstitutionImageQueryParam,
    InstitutionImageUpdateSchema,
    InstitutionOutSchema,
    InstitutionQueryParam,
    InstitutionUpdateSchema,
)
from .service import InstitutionImageService, InstitutionService

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


@InstitutionRouter.put("/update/{id}", summary="修改机构", response_model=ResponseSchema[InstitutionOutSchema])
async def update_institution_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    id: Annotated[int, Path(description="机构ID", ge=1)],
    data: Annotated[InstitutionUpdateSchema, Body(description="修改机构参数")],
) -> JSONResponse:
    result = await InstitutionService(auth, db).update(redis=redis, id=id, data=data)
    return SuccessResponse(data=result, msg="修改机构成功")


@InstitutionRouter.delete("/delete", summary="删除机构", response_model=ResponseSchema[None])
async def delete_institution_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await InstitutionService(auth, db).delete(redis=redis, ids=ids)
    return SuccessResponse(msg="删除机构成功")


InstitutionImageRouter = APIRouter(route_class=OperationLogRoute, prefix="/institution-images", tags=["市场-机构图片"])


@InstitutionImageRouter.get("/list", summary="查询机构图片", response_model=ResponseSchema[PageResultSchema[InstitutionImageOutSchema]])
async def get_institution_image_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[InstitutionImageQueryParam, Query()],
) -> JSONResponse:
    result = await InstitutionImageService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询机构图片成功")


@InstitutionImageRouter.get("/by-institution/{institution_id}", summary="按机构归集查看图片", response_model=ResponseSchema[PageResultSchema[InstitutionImageOutSchema]])
async def get_institution_image_by_institution_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    institution_id: Annotated[int, Path(description="机构ID", ge=1)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    result = await InstitutionImageService(auth, db).list_by_institution(
        institution_id=institution_id, page_no=page.page_no, page_size=page.page_size
    )
    return SuccessResponse(data=result, msg="查询机构图片成功")


@InstitutionImageRouter.get("/detail/{id}", summary="查询机构图片详情", response_model=ResponseSchema[InstitutionImageOutSchema])
async def get_institution_image_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="机构图片ID", ge=1)],
) -> JSONResponse:
    result = await InstitutionImageService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取机构图片详情成功")


@InstitutionImageRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建机构图片", response_model=ResponseSchema[InstitutionImageOutSchema])
async def create_institution_image_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[InstitutionImageCreateSchema, Body(description="创建机构图片参数")],
) -> JSONResponse:
    result = await InstitutionImageService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建机构图片成功")


@InstitutionImageRouter.put("/update/{id}", summary="修改机构图片", response_model=ResponseSchema[InstitutionImageOutSchema])
async def update_institution_image_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="机构图片ID", ge=1)],
    data: Annotated[InstitutionImageUpdateSchema, Body(description="修改机构图片参数")],
) -> JSONResponse:
    result = await InstitutionImageService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改机构图片成功")


@InstitutionImageRouter.delete("/delete", summary="删除机构图片", response_model=ResponseSchema[None])
async def delete_institution_image_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:institution:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await InstitutionImageService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除机构图片成功")
