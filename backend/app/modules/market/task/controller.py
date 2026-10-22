from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter, redis_getter
from app.core.router_class import OperationLogRoute

from ..settlement.schema import SettlementOutSchema
from ..settlement.service import SettlementService
from .schema import (
    TaskCreateSchema,
    TaskOutSchema,
    TaskPublishSchema,
    TaskQueryParam,
    TaskTypeCreateSchema,
    TaskTypeOutSchema,
    TaskTypeQueryParam,
    TaskTypeUpdateSchema,
    TaskUpdateSchema,
)
from .service import TaskService, TaskTypeService

TaskTypeRouter = APIRouter(route_class=OperationLogRoute, prefix="/task-types", tags=["市场-任务类型"])
TaskRouter = APIRouter(route_class=OperationLogRoute, prefix="/tasks", tags=["市场-任务"])


@TaskTypeRouter.get("/list", summary="查询任务类型模板", response_model=ResponseSchema[PageResultSchema[TaskTypeOutSchema]])
async def get_task_type_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:tasktype:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TaskTypeQueryParam, Query()],
) -> JSONResponse:
    result = await TaskTypeService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询任务类型成功")


@TaskTypeRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建任务类型模板", response_model=ResponseSchema[TaskTypeOutSchema])
async def create_task_type_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:tasktype:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TaskTypeCreateSchema, Body(description="创建任务类型参数")],
) -> JSONResponse:
    result = await TaskTypeService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建任务类型成功")


@TaskTypeRouter.put("/update/{id}", summary="修改任务类型模板", response_model=ResponseSchema[TaskTypeOutSchema])
async def update_task_type_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:tasktype:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务类型ID", ge=1)],
    data: Annotated[TaskTypeUpdateSchema, Body(description="修改任务类型参数")],
) -> JSONResponse:
    result = await TaskTypeService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改任务类型成功")


@TaskTypeRouter.delete("/delete", summary="删除任务类型模板", response_model=ResponseSchema[None])
async def delete_task_type_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:tasktype:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await TaskTypeService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除任务类型成功")


@TaskRouter.get("/list", summary="查询任务", response_model=ResponseSchema[PageResultSchema[TaskOutSchema]])
async def get_task_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TaskQueryParam, Query()],
) -> JSONResponse:
    result = await TaskService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询任务成功")


@TaskRouter.get("/detail/{id}", summary="查询任务详情", response_model=ResponseSchema[TaskOutSchema])
async def get_task_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await TaskService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取任务详情成功")


@TaskRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建任务", response_model=ResponseSchema[TaskOutSchema])
async def create_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TaskCreateSchema, Body(description="创建任务参数")],
) -> JSONResponse:
    result = await TaskService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建任务成功")


@TaskRouter.put("/update/{id}", summary="修改任务", response_model=ResponseSchema[TaskOutSchema])
async def update_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
    data: Annotated[TaskUpdateSchema, Body(description="修改任务参数")],
) -> JSONResponse:
    result = await TaskService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改任务成功")


@TaskRouter.delete("/delete", summary="删除任务", response_model=ResponseSchema[None])
async def delete_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await TaskService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除任务成功")


@TaskRouter.post("/publish/{id}", summary="发布任务", response_model=ResponseSchema[TaskOutSchema])
async def publish_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:publish"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
    data: Annotated[TaskPublishSchema | None, Body(description="发布参数")] = None,
) -> JSONResponse:
    result = await TaskService(auth, db).publish(redis=redis, id=id, data=data)
    return SuccessResponse(data=result, msg="发布任务成功")


@TaskRouter.post("/settle/{id}", summary="触发归集结算", response_model=ResponseSchema[list[SettlementOutSchema]])
async def settle_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:run"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await SettlementService(auth, db).settle(task_id=id)
    return SuccessResponse(data=result, msg="归集结算成功")
