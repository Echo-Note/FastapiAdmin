"""成果导入 —— 控制器。

提供结算单导入（对内/对外自动识别）与报告附件关联两个上传接口。
上传文件先落盘到 ``static/upload/import/`` 下，再交由服务层解析入库。
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Query, Security, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute
from app.utils.upload_util import UploadUtil

from .schema import ImportResultSchema
from .service import ImportService

ImportRouter = APIRouter(route_class=OperationLogRoute, prefix="/import", tags=["市场-成果导入"])

# 导入允许的文件扩展名（报告 pptx 不在通用上传白名单内，故在此独立放行）
_ALLOWED_EXTENSIONS = {".xlsx", ".pptx"}


async def _save_upload(file: UploadFile, subdir: str) -> str:
    """把上传文件保存到 ``static/upload/import/{subdir}/``，返回相对路径。

    参数:
    - file: 上传文件对象。
    - subdir: 子目录（如 settlement / report）。

    返回:
    - 文件相对路径（相对项目根目录）。

    异常:
    - CustomException: 文件类型不支持或保存失败。
    """
    if not file.filename:
        raise CustomException(msg="请选择要上传的文件")
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise CustomException(msg=f"仅支持导入 {'/'.join(sorted(_ALLOWED_EXTENSIONS))} 文件")

    # 保留原始文件名（仅清理危险字符）：执行人/公司名从文件名约定解析（如
    # ``0.重庆-省平台项目结算单-重庆熊丽.xlsx``），若用 generate_safe_filename
    # 追加时间戳后缀会污染解析结果（执行人被识别成「熊丽_20261026…A123」）
    safe_name = UploadUtil.sanitize_filename(file.filename)
    dir_path = settings.UPLOAD_FILE_PATH / "import" / subdir
    dir_path.mkdir(parents=True, exist_ok=True)
    filepath = dir_path / safe_name

    try:
        async with aiofiles.open(filepath, "wb") as f:
            while chunk := await file.read(8 * 1024 * 1024):
                await f.write(chunk)
    except OSError as e:
        raise CustomException(msg=f"文件保存失败: {e!s}") from e
    return str(filepath)


def _default_period() -> str:
    """默认结算周期：当前自然月（如 2026-10）。"""
    return datetime.now().strftime("%Y-%m")


@ImportRouter.post("/settlement", summary="导入结算单（对内/对外自动识别）", response_model=ResponseSchema[ImportResultSchema])
async def import_settlement_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:import:execute"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    files: Annotated[list[UploadFile], File(description="结算单 xlsx 文件（可多选）")],
    period: Annotated[str, Query(description="结算周期(如 2026-10)", pattern=r"^\d{4}-\d{2}$")] = "",
) -> JSONResponse:
    period = period or _default_period()
    saved_paths: list[str] = []
    for file in files:
        saved_paths.append(await _save_upload(file, "settlement"))
    result = await ImportService(auth, db).import_settlements(saved_paths, period)
    return SuccessResponse(data=result, msg="结算单导入完成")


@ImportRouter.post("/report", summary="关联报告附件(pptx)", response_model=ResponseSchema[None])
async def link_report_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:import:execute"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    file: Annotated[UploadFile, File(description="分析报告 pptx 文件")],
    service_no: Annotated[int, Query(description="对外服务项目号(1-37)", ge=1)],
    period: Annotated[str, Query(description="报告周期(如 2026-10)", pattern=r"^\d{4}-\d{2}$")] = "",
) -> JSONResponse:
    period = period or _default_period()
    attachment = await _save_upload(file, "report")
    ok = await ImportService(auth, db).link_report_attachment(service_no, period, attachment)
    if not ok:
        raise CustomException(msg=f"服务项目号 {service_no} 在该周期下无对应报告，无法关联附件")
    return SuccessResponse(msg="报告附件关联成功")
