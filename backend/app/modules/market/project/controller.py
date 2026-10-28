"""项目管理（对外）、医药公司主数据、月度报告的接口层。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    CompanyCreateSchema,
    CompanyOutSchema,
    CompanyQueryParam,
    CompanyUpdateSchema,
    ProjectCreateSchema,
    ProjectOutSchema,
    ProjectQueryParam,
    ProjectStatusUpdateSchema,
    ProjectUpdateSchema,
    ReportCreateSchema,
    ReportOutSchema,
    ReportQueryParam,
    ReportUpdateSchema,
)
from .service import CompanyService, ProjectService, ReportService

CompanyRouter = APIRouter(route_class=OperationLogRoute, prefix="/companies", tags=["市场-医药公司"])
ProjectRouter = APIRouter(route_class=OperationLogRoute, prefix="/projects", tags=["市场-项目"])
ReportRouter = APIRouter(route_class=OperationLogRoute, prefix="/reports", tags=["市场-报告"])


# ── 医药公司 ──────────────────────────────────────────────────────────


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


# ── 项目 ──────────────────────────────────────────────────────────────


@ProjectRouter.get("/list", summary="查询项目", response_model=ResponseSchema[PageResultSchema[ProjectOutSchema]])
async def get_project_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ProjectQueryParam, Query()],
) -> JSONResponse:
    result = await ProjectService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询项目成功")


@ProjectRouter.get("/detail/{id}", summary="查询项目详情", response_model=ResponseSchema[ProjectOutSchema])
async def get_project_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
) -> JSONResponse:
    result = await ProjectService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取项目详情成功")


@ProjectRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建项目", response_model=ResponseSchema[ProjectOutSchema])
async def create_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ProjectCreateSchema, Body(description="创建项目参数")],
) -> JSONResponse:
    result = await ProjectService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建项目成功")


@ProjectRouter.put("/update/{id}", summary="修改项目", response_model=ResponseSchema[ProjectOutSchema])
async def update_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    data: Annotated[ProjectUpdateSchema, Body(description="修改项目参数")],
) -> JSONResponse:
    result = await ProjectService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改项目成功")


@ProjectRouter.delete("/delete", summary="删除项目", response_model=ResponseSchema[None])
async def delete_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await ProjectService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除项目成功")


@ProjectRouter.post("/publish/{id}", summary="发布项目", response_model=ResponseSchema[ProjectOutSchema])
async def publish_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:publish"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
) -> JSONResponse:
    result = await ProjectService(auth, db).publish(id=id)
    return SuccessResponse(data=result, msg="发布项目成功")


@ProjectRouter.post("/status/{id}", summary="项目状态流转", response_model=ResponseSchema[ProjectOutSchema])
async def change_project_status_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    data: Annotated[ProjectStatusUpdateSchema, Body(description="目标状态")],
) -> JSONResponse:
    result = await ProjectService(auth, db).change_status(id=id, data=data)
    return SuccessResponse(data=result, msg="项目状态流转成功")


@ProjectRouter.post("/templates/{id}", summary="项目关联二级模板", response_model=ResponseSchema[ProjectOutSchema])
async def add_project_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    template_id: Annotated[int, Body(description="二级模板ID")],
) -> JSONResponse:
    result = await ProjectService(auth, db).add_template(id=id, template_id=template_id)
    return SuccessResponse(data=result, msg="项目关联二级模板成功")


@ProjectRouter.delete("/templates/{id}/{template_id}", summary="项目移除二级模板", response_model=ResponseSchema[ProjectOutSchema])
async def remove_project_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    template_id: Annotated[int, Path(description="二级模板ID", ge=1)],
) -> JSONResponse:
    result = await ProjectService(auth, db).remove_template(id=id, template_id=template_id)
    return SuccessResponse(data=result, msg="项目移除二级模板成功")


# ── 月度报告 ──────────────────────────────────────────────────────────


@ReportRouter.get("/list", summary="查询月度报告", response_model=ResponseSchema[PageResultSchema[ReportOutSchema]])
async def get_report_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ReportQueryParam, Query()],
) -> JSONResponse:
    result = await ReportService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询月度报告成功")


@ReportRouter.get("/detail/{id}", summary="查询月度报告详情", response_model=ResponseSchema[ReportOutSchema])
async def get_report_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="报告ID", ge=1)],
) -> JSONResponse:
    result = await ReportService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取月度报告详情成功")


@ReportRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建月度报告", response_model=ResponseSchema[ReportOutSchema])
async def create_report_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ReportCreateSchema, Body(description="创建月度报告参数")],
) -> JSONResponse:
    result = await ReportService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建月度报告成功")


@ReportRouter.put("/update/{id}", summary="修改月度报告", response_model=ResponseSchema[ReportOutSchema])
async def update_report_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="报告ID", ge=1)],
    data: Annotated[ReportUpdateSchema, Body(description="修改月度报告参数")],
) -> JSONResponse:
    result = await ReportService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改月度报告成功")


@ReportRouter.delete("/delete", summary="删除月度报告", response_model=ResponseSchema[None])
async def delete_report_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await ReportService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除月度报告成功")


@ReportRouter.post("/generate", summary="生成月度报告", response_model=ResponseSchema[ReportOutSchema])
async def generate_report_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    project_id: Annotated[int, Body(description="项目ID")],
    template_id: Annotated[int | None, Body(description="二级模板ID(可空:全项目汇总)")],
    period: Annotated[str, Body(description="报告月份(如 2026-03)")],
) -> JSONResponse:
    result = await ReportService(auth, db).generate(project_id=project_id, template_id=template_id, period=period)
    return SuccessResponse(data=result, msg="生成月度报告成功")
