"""市场管理域 —— 微信小程序端聚合路由。

统一挂载小程序端接口：任务大厅、任务单详情、我的任务、分派单详情、接收任务、大厅接单、
提交成果、我的成果、我的发放/津贴、机构列表。
认证使用 ``require_market_member``：要求登录、**并保证该用户有启用的 C 端成员档案**
（`market_member`，首次访问自动建档），不要求运营端 RBAC 权限码。
「是不是 C 端」由档案判定，不看角色——角色是多对多的权限概念，用它推断身份会模棱两可。
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, File, Path, Query, Request, Security, UploadFile
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam, UploadResponseSchema
from app.core.dependencies import db_getter, redis_getter
from app.core.router_class import OperationLogRoute
from app.modules.common.file.service import FileService

from .institution.schema import InstitutionOutSchema
from .institution.service import InstitutionService
from .member.dependencies import require_market_member
from .payout.service import PayoutService
from .product.schema import ProductSearchItemSchema, ProductSearchQueryParam
from .product.service import ProductService
from .task.schema import (
    AssignmentOutSchema,
    AssignmentQueryParam,
    MiniAssignmentGroupSchema,
    MiniTaskGroupSchema,
    MyAssignmentStatsOutSchema,
    SubmissionCreateSchema,
    SubmissionOutSchema,
    SubmissionQueryParam,
    SubmissionUpdateSchema,
    TaskOutSchema,
)
from .task.service import AssignmentService, SubmissionService, TaskService

MiniRouter = APIRouter(route_class=OperationLogRoute, prefix="/mini", tags=["市场-小程序"])


@MiniRouter.get("/tasks", summary="任务大厅(公开接单任务)", response_model=ResponseSchema[PageResultSchema[TaskOutSchema]])
async def mini_task_hall_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """任务大厅：公开接单任务列表（定向分派任务走「我的任务」）。"""
    result = await TaskService(auth, db).hall_tasks(redis=redis, page_no=page.page_no, page_size=page.page_size)
    return SuccessResponse(data=result, msg="获取任务大厅成功")


@MiniRouter.get("/tasks/grouped", summary="任务大厅分组(按项目)", response_model=ResponseSchema[list[MiniTaskGroupSchema]])
async def mini_task_hall_grouped_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    """任务大厅分组：复用大厅可见性语义，一次性返回全部可见任务并按项目分组。"""
    result = await TaskService(auth, db).grouped_hall_tasks()
    return SuccessResponse(data=result, msg="获取任务大厅分组成功")


@MiniRouter.get("/tasks/{id}", summary="任务单详情", response_model=ResponseSchema[TaskOutSchema])
async def mini_task_detail_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    """任务单详情：小程序任务详情页现取模板与单价。"""
    result = await TaskService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取任务详情成功")


@MiniRouter.get("/assignments", summary="我的任务", response_model=ResponseSchema[PageResultSchema[AssignmentOutSchema]])
async def mini_my_assignments_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AssignmentQueryParam, Query()],
) -> JSONResponse:
    result = await AssignmentService(auth, db).my_assignments(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="获取我的任务成功")


@MiniRouter.get("/assignments/grouped", summary="我的任务分组(按项目)", response_model=ResponseSchema[list[MiniAssignmentGroupSchema]])
async def mini_my_assignments_grouped_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    search: Annotated[AssignmentQueryParam, Query()],
) -> JSONResponse:
    """我的任务分组：复用我的任务语义，按当前用户分派并按任务项目分组。"""
    result = await AssignmentService(auth, db).grouped_my_assignments(search=search)
    return SuccessResponse(data=result, msg="获取我的任务分组成功")


@MiniRouter.get("/assignments/{id}", summary="分派单详情", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_assignment_detail_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    """分派单详情：小程序提交成果页现取模板。"""
    result = await AssignmentService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取分派详情成功")


@MiniRouter.post("/assignments/{id}/accept", summary="接收任务", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_accept_assignment_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).accept(id=id)
    return SuccessResponse(data=result, msg="接收任务成功")


@MiniRouter.post("/tasks/{id}/claim", summary="大厅接单", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_claim_task_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).claim(task_id=id, redis=redis)
    return SuccessResponse(data=result, msg="接单成功")


@MiniRouter.post("/submissions", summary="提交成果", response_model=ResponseSchema[SubmissionOutSchema])
async def mini_create_submission_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[SubmissionCreateSchema, Body(description="提交成果参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="提交成果成功")


@MiniRouter.put("/submissions/{id}", summary="修改成果(草稿/驳回重提)", response_model=ResponseSchema[SubmissionOutSchema])
async def mini_update_submission_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
    data: Annotated[SubmissionUpdateSchema, Body(description="修改成果参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改成果成功")


@MiniRouter.get("/submissions", summary="我的成果", response_model=ResponseSchema[PageResultSchema[SubmissionOutSchema]])
async def mini_my_submissions_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SubmissionQueryParam, Query()],
) -> JSONResponse:
    result = await SubmissionService(auth, db).my_submissions(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="获取我的成果成功")


@MiniRouter.get("/payout", summary="我的发放/津贴", response_model=ResponseSchema[dict])
async def mini_my_payout_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    period: Annotated[str, Query(description="周期(如 2026-03)")],
) -> JSONResponse:
    result = await PayoutService(auth, db).my_payout(user_id=auth.user.id, period=period)
    return SuccessResponse(data=result, msg="获取我的发放信息成功")


@MiniRouter.get("/task-stats", summary="我的待办计数", response_model=ResponseSchema[MyAssignmentStatsOutSchema])
async def mini_my_task_stats_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    """我的待办计数：分派状态分组 + 被驳回成果数（C 端 Tab / 状态 Tab 角标）。"""
    result = await AssignmentService(auth, db).my_stats()
    return SuccessResponse(data=result, msg="获取我的待办计数成功")


@MiniRouter.get("/submissions/{id}", summary="我的成果详情", response_model=ResponseSchema[SubmissionOutSchema])
async def mini_my_submission_detail_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
) -> JSONResponse:
    """我的成果详情：驳回后修改重提需要回填原表单与表单结构，运营端接口要 RBAC 权限码用不了。"""
    result = await SubmissionService(auth, db).my_detail(id=id)
    return SuccessResponse(data=result, msg="获取成果详情成功")


@MiniRouter.get(
    "/products/search", summary="产品检索(产品库, 提交成果自动填充)", response_model=ResponseSchema[list[ProductSearchItemSchema]]
)
async def mini_product_search_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    search: Annotated[ProductSearchQueryParam, Query()],
) -> JSONResponse:
    """C 端产品检索：按产品名称模糊匹配，命中后由前端回填规格与生产企业。

    可见范围由审核状态决定：已通过的产品对所有人可见；自己提交的待审核产品仅本人可见；
    已驳回的产品不参与检索。认证使用 get_current_user（不要求运营权限码）。
    """
    result = await ProductService(auth, db).search(keyword=search.keyword, limit=search.limit)
    return SuccessResponse(data=result, msg="检索产品成功")


@MiniRouter.get("/institutions", summary="机构列表(提交成果选择)", response_model=ResponseSchema[PageResultSchema[InstitutionOutSchema]])
async def mini_institution_list_controller(
    auth: Annotated[AuthSchema, Security(require_market_member)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """机构列表：供 C 端（小程序）用户提交成果时选择对象机构。

    从 Redis 缓存读取启用机构全量列表后内存分页；认证使用 get_current_user。
    """
    items = await InstitutionService(auth, db).enabled_list(redis=redis)
    total = len(items)
    start = (page.page_no - 1) * page.page_size
    page_items = items[start : start + page.page_size]
    result = PageResultSchema(
        page_no=page.page_no,
        page_size=page.page_size,
        total=total,
        has_next=start + page.page_size < total,
        items=page_items,
    )
    return SuccessResponse(data=result, msg="获取机构列表成功")


@MiniRouter.post(
    "/upload",
    summary="C端上传文件(提交成果图片/附件)",
    response_model=ResponseSchema[UploadResponseSchema],
    dependencies=[Security(require_market_member)],
)
async def mini_upload_controller(
    request: Request,
    file: Annotated[UploadFile, File(description="上传文件")],
    upload_type: Annotated[
        Literal["file", "avatar"] | None,
        Query(description="上传类型: file=通用文件(成果图片/附件), avatar=头像"),
    ] = "file",
) -> JSONResponse:
    """C端文件上传：提交成果的图片/附件，登录即可，不要求运营端 RBAC 权限码。"""
    result = await FileService.upload_service(
        base_url=str(request.base_url),
        file=file,
        upload_type=upload_type or "file",
    )
    return SuccessResponse(data=result, msg="上传文件成功")
