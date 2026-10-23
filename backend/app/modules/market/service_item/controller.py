from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import ServiceItemCreateSchema, ServiceItemOutSchema, ServiceItemQueryParam, ServiceItemUpdateSchema
from .service import ServiceItemService

ServiceItemRouter = APIRouter(route_class=OperationLogRoute, prefix="/service-items", tags=["市场-对外服务项目"])


@ServiceItemRouter.get("/list", summary="查询对外服务项目", response_model=ResponseSchema[PageResultSchema[ServiceItemOutSchema]])
async def get_service_item_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:service_item:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ServiceItemQueryParam, Query()],
) -> JSONResponse:
    result = await ServiceItemService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询对外服务项目成功")


@ServiceItemRouter.get("/detail/{id}", summary="查询对外服务项目详情", response_model=ResponseSchema[ServiceItemOutSchema])
async def get_service_item_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:service_item:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="对外服务项目ID", ge=1)],
) -> JSONResponse:
    result = await ServiceItemService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="查询对外服务项目详情成功")


@ServiceItemRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建对外服务项目", response_model=ResponseSchema[ServiceItemOutSchema])
async def create_service_item_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:service_item:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ServiceItemCreateSchema, Body(description="创建对外服务项目参数")],
) -> JSONResponse:
    result = await ServiceItemService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建对外服务项目成功")


@ServiceItemRouter.put("/update/{id}", summary="修改对外服务项目", response_model=ResponseSchema[ServiceItemOutSchema])
async def update_service_item_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:service_item:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="对外服务项目ID", ge=1)],
    data: Annotated[ServiceItemUpdateSchema, Body(description="修改对外服务项目参数")],
) -> JSONResponse:
    result = await ServiceItemService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改对外服务项目成功")


@ServiceItemRouter.delete("/delete", summary="删除对外服务项目", response_model=ResponseSchema[None])
async def delete_service_item_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:service_item:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await ServiceItemService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除对外服务项目成功")
