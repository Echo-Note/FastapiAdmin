"""产品库 Controller（运营端）。

权限码前缀与 market 域其它模块一致：``module_market:product:{query,create,update,delete,audit}``。
C 端检索接口在 ``app/modules/market/mini_controller.py``（只校验登录）。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    ProductAuditSchema,
    ProductCreateSchema,
    ProductOutSchema,
    ProductQueryParam,
    ProductUpdateSchema,
)
from .service import ProductService

ProductRouter = APIRouter(route_class=OperationLogRoute, prefix="/products", tags=["市场-产品库"])


@ProductRouter.get("/list", summary="查询产品库", response_model=ResponseSchema[PageResultSchema[ProductOutSchema]])
async def get_product_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:product:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ProductQueryParam, Query()],
) -> JSONResponse:
    result = await ProductService(auth, db).page(
        page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by
    )
    return SuccessResponse(data=result, msg="查询产品库成功")


@ProductRouter.get("/detail/{id}", summary="查询产品详情", response_model=ResponseSchema[ProductOutSchema])
async def get_product_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:product:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="产品ID", ge=1)],
) -> JSONResponse:
    result = await ProductService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取产品详情成功")


@ProductRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="新增产品", response_model=ResponseSchema[ProductOutSchema])
async def create_product_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:product:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ProductCreateSchema, Body(description="产品创建参数")],
) -> JSONResponse:
    result = await ProductService(auth, db).create(data)
    return SuccessResponse(data=result, msg="新增产品成功")


@ProductRouter.put("/update/{id}", summary="修改产品", response_model=ResponseSchema[ProductOutSchema])
async def update_product_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:product:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="产品ID", ge=1)],
    data: Annotated[ProductUpdateSchema, Body(description="产品修改参数")],
) -> JSONResponse:
    result = await ProductService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改产品成功")


@ProductRouter.delete("/delete", summary="删除产品", response_model=ResponseSchema[None])
async def delete_product_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:product:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="产品ID列表")],
) -> JSONResponse:
    await ProductService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除产品成功")


@ProductRouter.put("/audit", summary="审核产品(批量)", response_model=ResponseSchema[int])
async def audit_product_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:product:audit"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ProductAuditSchema, Body(description="产品审核参数")],
) -> JSONResponse:
    changed = await ProductService(auth, db).audit(data)
    return SuccessResponse(data=changed, msg=f"审核完成，变更 {changed} 条")
