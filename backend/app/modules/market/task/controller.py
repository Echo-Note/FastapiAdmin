"""任务管理域路由。

任务两级层级（分类/模板）+ 任务实例 + 分派 + 成果提交的运营端接口。
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
    AssignmentBatchCreateSchema,
    AssignmentCreateSchema,
    AssignmentOutSchema,
    AssignmentQueryParam,
    AssignmentUpdateSchema,
    CatalogUsageSchema,
    SubmissionOutSchema,
    SubmissionQueryParam,
    SubmissionReviewResultSchema,
    SubmissionReviewSchema,
    SubmissionUpdateSchema,
    TaskBatchPublishResultSchema,
    TaskBatchPublishSchema,
    TaskCategoryCreateSchema,
    TaskCategoryOutSchema,
    TaskCategoryQueryParam,
    TaskCategoryTreeSchema,
    TaskCategoryUpdateSchema,
    TaskCreateSchema,
    TaskFacetSchema,
    TaskItemCreateSchema,
    TaskItemOutSchema,
    TaskItemQueryParam,
    TaskItemUpdateSchema,
    TaskOutSchema,
    TaskQueryParam,
    TaskStatusUpdateSchema,
    TaskTemplateCreateSchema,
    TaskTemplateOutSchema,
    TaskTemplateQueryParam,
    TaskTemplateUpdateSchema,
    TaskUpdateSchema,
)
from .service import AssignmentService, SubmissionService, TaskCategoryService, TaskItemService, TaskService, TaskTemplateService

TaskCategoryRouter = APIRouter(route_class=OperationLogRoute, prefix="/categories", tags=["市场-任务分类"])
TaskTemplateRouter = APIRouter(route_class=OperationLogRoute, prefix="/templates", tags=["市场-任务模板"])
TaskItemRouter = APIRouter(route_class=OperationLogRoute, prefix="/items", tags=["市场-任务"])
TaskRouter = APIRouter(route_class=OperationLogRoute, prefix="/tasks", tags=["市场-任务"])
AssignmentRouter = APIRouter(route_class=OperationLogRoute, prefix="/assignments", tags=["市场-分派"])
SubmissionRouter = APIRouter(route_class=OperationLogRoute, prefix="/submissions", tags=["市场-成果"])


# ── 一级任务分类 ──────────────────────────────────────────────────────


@TaskCategoryRouter.get("/list", summary="查询一级分类", response_model=ResponseSchema[PageResultSchema[TaskCategoryOutSchema]])
async def get_task_category_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_category:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TaskCategoryQueryParam, Query()],
) -> JSONResponse:
    result = await TaskCategoryService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询一级分类成功")


@TaskCategoryRouter.get("/tree", summary="查询任务目录树", response_model=ResponseSchema[list[TaskCategoryTreeSchema]])
async def get_task_category_tree_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_category:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await TaskCategoryService(auth, db).tree()
    return SuccessResponse(data=result, msg="查询任务目录树成功")


@TaskCategoryRouter.get("/detail/{id}", summary="查询一级分类详情", response_model=ResponseSchema[TaskCategoryOutSchema])
async def get_task_category_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_category:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分类ID", ge=1)],
) -> JSONResponse:
    result = await TaskCategoryService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取一级分类详情成功")


@TaskCategoryRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建一级分类", response_model=ResponseSchema[TaskCategoryOutSchema])
async def create_task_category_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_category:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TaskCategoryCreateSchema, Body(description="创建一级分类参数")],
) -> JSONResponse:
    result = await TaskCategoryService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建一级分类成功")


@TaskCategoryRouter.put("/update/{id}", summary="修改一级分类", response_model=ResponseSchema[TaskCategoryOutSchema])
async def update_task_category_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_category:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分类ID", ge=1)],
    data: Annotated[TaskCategoryUpdateSchema, Body(description="修改一级分类参数")],
) -> JSONResponse:
    result = await TaskCategoryService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改一级分类成功")


@TaskCategoryRouter.delete("/delete", summary="删除一级分类", response_model=ResponseSchema[None])
async def delete_task_category_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_category:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await TaskCategoryService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除一级分类成功")


# ── 二级任务模板 ──────────────────────────────────────────────────────


@TaskTemplateRouter.get("/list", summary="查询二级模板", response_model=ResponseSchema[PageResultSchema[TaskTemplateOutSchema]])
async def get_task_template_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TaskTemplateQueryParam, Query()],
) -> JSONResponse:
    result = await TaskTemplateService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询二级模板成功")


@TaskTemplateRouter.get("/detail/{id}", summary="查询二级模板详情", response_model=ResponseSchema[TaskTemplateOutSchema])
async def get_task_template_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="模板ID", ge=1)],
) -> JSONResponse:
    result = await TaskTemplateService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取二级模板详情成功")


@TaskTemplateRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建二级模板", response_model=ResponseSchema[TaskTemplateOutSchema])
async def create_task_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TaskTemplateCreateSchema, Body(description="创建二级模板参数")],
) -> JSONResponse:
    result = await TaskTemplateService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建二级模板成功")


@TaskTemplateRouter.put("/update/{id}", summary="修改二级模板", response_model=ResponseSchema[TaskTemplateOutSchema])
async def update_task_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="模板ID", ge=1)],
    data: Annotated[TaskTemplateUpdateSchema, Body(description="修改二级模板参数")],
) -> JSONResponse:
    result = await TaskTemplateService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改二级模板成功")


@TaskTemplateRouter.delete("/delete", summary="删除二级模板", response_model=ResponseSchema[None])
async def delete_task_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await TaskTemplateService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除二级模板成功")


# ── 三级任务 ──────────────────────────────────────────────────────────


@TaskItemRouter.get("/list", summary="查询三级任务", response_model=ResponseSchema[PageResultSchema[TaskItemOutSchema]])
async def get_task_item_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TaskItemQueryParam, Query()],
) -> JSONResponse:
    result = await TaskItemService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询三级任务成功")


@TaskItemRouter.get("/usage", summary="目录已用统计(目录页只看已用)", response_model=ResponseSchema[CatalogUsageSchema])
async def get_task_item_usage_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    """返回被项目引用的三级任务与叶子模板 id，供任务目录页默认只展示「已用」条目。"""
    result = await TaskCategoryService(auth, db).catalog_usage()
    return SuccessResponse(data=result, msg="获取目录已用统计成功")


@TaskItemRouter.get("/detail/{id}", summary="查询三级任务详情", response_model=ResponseSchema[TaskItemOutSchema])
async def get_task_item_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await TaskItemService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取三级任务详情成功")


@TaskItemRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建三级任务", response_model=ResponseSchema[TaskItemOutSchema])
async def create_task_item_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TaskItemCreateSchema, Body(description="创建三级任务参数")],
) -> JSONResponse:
    result = await TaskItemService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建三级任务成功")


@TaskItemRouter.put("/update/{id}", summary="修改三级任务", response_model=ResponseSchema[TaskItemOutSchema])
async def update_task_item_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
    data: Annotated[TaskItemUpdateSchema, Body(description="修改三级任务参数")],
) -> JSONResponse:
    result = await TaskItemService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改三级任务成功")


@TaskItemRouter.delete("/delete", summary="删除三级任务", response_model=ResponseSchema[None])
async def delete_task_item_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task_template:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await TaskItemService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除三级任务成功")


# ── 任务实例 ──────────────────────────────────────────────────────────


@TaskRouter.get("/list", summary="查询任务", response_model=ResponseSchema[PageResultSchema[TaskOutSchema]])
async def get_task_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TaskQueryParam, Query()],
) -> JSONResponse:
    result = await TaskService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询任务成功")


@TaskRouter.get("/facets", summary="任务目录侧边栏统计(只含有任务的分类/模板)", response_model=ResponseSchema[list[TaskFacetSchema]])
async def get_task_facets_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    """返回确实有任务实例的（分类, 模板）组合及任务数，供侧边栏目录隐藏空节点。"""
    result = await TaskService(auth, db).facets()
    return SuccessResponse(data=result, msg="获取任务目录统计成功")


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
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await TaskService(auth, db).publish(id=id)
    return SuccessResponse(data=result, msg="发布任务成功")


@TaskRouter.post("/batch-publish", summary="批量发布任务", response_model=ResponseSchema[TaskBatchPublishResultSchema])
async def batch_publish_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:publish"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TaskBatchPublishSchema, Body(description="批量发布参数")],
) -> JSONResponse:
    result = await TaskService(auth, db).batch_publish(ids=data.ids)
    return SuccessResponse(data=result, msg="批量发布任务成功")


@TaskRouter.post("/status/{id}", summary="任务状态流转", response_model=ResponseSchema[TaskOutSchema])
async def change_task_status_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:task:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
    data: Annotated[TaskStatusUpdateSchema, Body(description="目标状态参数")],
) -> JSONResponse:
    result = await TaskService(auth, db).change_status(id=id, data=data)
    return SuccessResponse(data=result, msg="任务状态流转成功")


# ── 任务分派 ──────────────────────────────────────────────────────────


@AssignmentRouter.get("/list", summary="查询分派", response_model=ResponseSchema[PageResultSchema[AssignmentOutSchema]])
async def get_assignment_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AssignmentQueryParam, Query()],
) -> JSONResponse:
    result = await AssignmentService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询分派成功")


@AssignmentRouter.get("/detail/{id}", summary="查询分派详情", response_model=ResponseSchema[AssignmentOutSchema])
async def get_assignment_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取分派详情成功")


@AssignmentRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建分派", response_model=ResponseSchema[list[AssignmentOutSchema]])
async def create_assignment_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[AssignmentCreateSchema, Body(description="创建分派参数")],
) -> JSONResponse:
    result = await AssignmentService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建分派成功")


@AssignmentRouter.post("/batch-create", summary="批量分配", response_model=ResponseSchema[int])
async def batch_create_assignment_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[AssignmentBatchCreateSchema, Body(description="批量分配参数")],
) -> JSONResponse:
    result = await AssignmentService(auth, db).batch_assign_multi(task_ids=data.task_ids, user_ids=data.user_ids)
    return SuccessResponse(data=result, msg="批量分配成功")


@AssignmentRouter.put("/update/{id}", summary="修改分派", response_model=ResponseSchema[AssignmentOutSchema])
async def update_assignment_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
    data: Annotated[AssignmentUpdateSchema, Body(description="修改分派参数")],
) -> JSONResponse:
    result = await AssignmentService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改分派成功")


@AssignmentRouter.delete("/delete", summary="删除分派", response_model=ResponseSchema[None])
async def delete_assignment_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await AssignmentService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除分派成功")


# ── 成果提交 ──────────────────────────────────────────────────────────


@SubmissionRouter.get("/list", summary="查询成果", response_model=ResponseSchema[PageResultSchema[SubmissionOutSchema]])
async def get_submission_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SubmissionQueryParam, Query()],
) -> JSONResponse:
    result = await SubmissionService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询成果成功")


@SubmissionRouter.get("/detail/{id}", summary="查询成果详情", response_model=ResponseSchema[SubmissionOutSchema])
async def get_submission_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
) -> JSONResponse:
    result = await SubmissionService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取成果详情成功")


@SubmissionRouter.put("/update/{id}", summary="修改成果", response_model=ResponseSchema[SubmissionOutSchema])
async def update_submission_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
    data: Annotated[SubmissionUpdateSchema, Body(description="修改成果参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改成果成功")


@SubmissionRouter.delete("/delete", summary="删除成果", response_model=ResponseSchema[None])
async def delete_submission_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await SubmissionService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除成果成功")


@SubmissionRouter.post("/review/{id}", summary="审核成果", response_model=ResponseSchema[SubmissionReviewResultSchema])
async def review_submission_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:review"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
    data: Annotated[SubmissionReviewSchema, Body(description="审核参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).review(id=id, data=data)
    return SuccessResponse(data=result, msg="审核成果成功")
