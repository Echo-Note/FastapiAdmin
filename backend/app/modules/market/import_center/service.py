"""成果导入服务。

编排「结算单解析 → 基础数据创建 → 业务数据写库」全流程，并提供报告附件关联能力。
导入走 CRUD 层直接落库（绕过各 Service 层的状态机校验），并以唯一业务键做幂等，
重复导入同一文件不会产生重复数据。
"""

from pathlib import Path
from typing import Any

from pypinyin import lazy_pinyin
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.modules.system.user.crud import UserCRUD
from app.modules.system.user.schema import UserCreateSchema
from app.utils.password_util import PwdUtil

# 触发 market 域全部模型注册：模型间 TYPE_CHECKING 循环引用依赖全量导入，
# 独立使用 ImportService（脚本/单测）时不经过 routers 全量导入，需显式注册 mapper
from .. import models as market_models  # noqa: F401
from ..assignment.crud import AssignmentCRUD
from ..company.crud import CompanyCRUD
from ..enums import AssignmentSource, AssignmentStatus, ReportStatus, SettlementStatus, TaskStatus
from ..report.crud import ReportCRUD
from ..service_item.crud import ServiceItemCRUD
from ..settlement.crud import SettlementCRUD, SettlementItemCRUD
from ..task.crud import TaskCRUD, TaskTypeCRUD
from .parser import (
    InnerSettlementRow,
    OuterSettlementRow,
    detect_kind,
    parse_inner_settlement,
    parse_outer_settlement,
)
from .schema import ImportResultSchema


def _username_from_name(name: str) -> str:
    """把中文姓名转为拼音登录账号（如「熊丽」→ ``xiongli``）。

    username 需字母开头，故用 pypinyin 全拼拼接，避免硬编码姓名映射。
    """
    return "".join(lazy_pinyin(name))


def _company_name_from_filename(filename: str) -> str | None:
    """从对外结算单文件名解析委托方公司名（约定格式：``{公司名}-{产品}-服务项目结算单.xlsx``）。"""
    stem = Path(filename).stem
    if "服务项目结算单" in stem:
        stem = stem.split("服务项目结算单")[0].rstrip("-")
    return stem.split("-")[0].strip() or None


def _executor_from_filename(filename: str) -> str:
    """从对内结算单文件名提取执行人姓名（约定格式：``{序号}.{地区}-省平台项目结算单-{地区}{姓名}.xlsx``）。"""
    stem = Path(filename).stem
    region = stem.split(".")[1].split("-")[0] if "." in stem else ""
    tail = stem.rsplit("省平台项目结算单-", 1)[-1] if "省平台项目结算单-" in stem else stem
    executor = tail.removeprefix(region) if region and tail.startswith(region) else tail
    return executor or "未知"


class ImportService:
    """成果导入服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 结算单导入 ────────────────────────────────────────────────────

    async def import_settlements(self, file_paths: list[str], period: str) -> ImportResultSchema:
        """导入结算单（对内 + 对外，按文件内容自动识别）。

        参数:
        - file_paths: 已保存到磁盘的结算单 xlsx 路径列表。
        - period: 结算周期（如 2026-10）。

        返回:
        - ImportResultSchema: 导入结果统计。
        """
        result = ImportResultSchema()
        inner_rows: list[InnerSettlementRow] = []
        outer_groups: list[tuple[str, list[OuterSettlementRow]]] = []
        for path in file_paths:
            try:
                kind = detect_kind(path)
                if kind == "inner":
                    executor = _executor_from_filename(Path(path).name)
                    inner_rows.extend(parse_inner_settlement(path, executor))
                elif kind == "outer":
                    company_name = _company_name_from_filename(Path(path).name)
                    if not company_name:
                        result.errors.append(f"文件 {Path(path).name} 无法从文件名解析公司名，已跳过")
                        continue
                    outer_groups.append((company_name, parse_outer_settlement(path)))
                else:
                    result.errors.append(f"文件 {Path(path).name} 无法识别为结算单，已跳过")
            except Exception as e:  # noqa: BLE001 - 单文件失败不阻断整体导入
                result.errors.append(f"文件 {Path(path).name} 导入失败: {e!s}")
        # 跨文件统一导入：对内按 task_no 分组汇总各执行人数量，对外按公司逐个落报告
        await self._import_inner(inner_rows, period, result)
        for company_name, rows in outer_groups:
            await self._import_outer(rows, company_name, period, result)
        return result

    async def _import_inner(self, rows: list[InnerSettlementRow], period: str, result: ImportResultSchema) -> None:
        """导入对内结算单。

        按计价项序号（task_no）分组：一个计价项在一个周期内是一个 task（``exec_qty`` 汇总
        各执行人数量），再分派给多个执行人，每个执行人落一条 assignment + settlement。
        """
        by_task_no: dict[int, list[InnerSettlementRow]] = {}
        for row in rows:
            by_task_no.setdefault(row.task_no, []).append(row)

        for task_no, exec_rows in by_task_no.items():
            task_type = await TaskTypeCRUD(self.auth, self.db).get(task_no=task_no)
            if not task_type:
                result.errors.append(f"计价项任务号 {task_no} 未在库中找到，已跳过")
                continue
            total_qty = sum(r.qty for r in exec_rows)
            unit_price = exec_rows[0].price if exec_rows else 0.0
            task = await self._get_or_create_task(
                task_no, task_type.id, task_type.default_kind, period, unit_price, total_qty, result
            )
            for row in exec_rows:
                user_id = await self._get_or_create_user(row.executor, result)
                if user_id is None:
                    continue
                await self._import_inner_row(task.id, user_id, row, result)

    async def _get_or_create_task(
        self,
        task_no: int,
        task_type_id: int,
        task_kind: str,
        period: str,
        unit_price: float,
        exec_qty: int,
        result: ImportResultSchema,
    ) -> Any:
        """按计价项序号获取或创建运行期任务（幂等，以 task_no 流水号为业务键）。

        分次导入不同执行人的结算单时，task 已存在但 ``exec_qty`` 需同步为各执行人数量之和，
        因此已存在时也回写汇总数量。
        """
        task_no_str = f"TK{period}-{task_no:03d}"
        task = await TaskCRUD(self.auth, self.db).get(task_no=task_no_str)
        if task:
            if task.exec_qty != exec_qty:
                await TaskCRUD(self.auth, self.db).update(id=task.id, data={"exec_qty": exec_qty})
                task = await TaskCRUD(self.auth, self.db).get(task_no=task_no_str)
            return task
        task = await TaskCRUD(self.auth, self.db).create(
            data={
                "task_no": task_no_str,
                "task_type_id": task_type_id,
                "task_kind": task_kind,
                "period": period,
                "unit_price": unit_price,
                "exec_qty": exec_qty,
                "assign_mode": "direct",
                "status": TaskStatus.SETTLED.value,
            }
        )
        result.task_created += 1
        return task

    async def _import_inner_row(
        self,
        task_id: int,
        user_id: int,
        row: InnerSettlementRow,
        result: ImportResultSchema,
    ) -> None:
        """导入对内结算单单行：assignment → settlement（幂等）。"""
        assignment = await AssignmentCRUD(self.auth, self.db).get(task_id=task_id, user_id=user_id)
        if not assignment:
            await AssignmentCRUD(self.auth, self.db).create(
                data={
                    "task_id": task_id,
                    "user_id": user_id,
                    "source": AssignmentSource.ASSIGNED.value,
                    "status": AssignmentStatus.SETTLED.value,
                }
            )
            result.assignment_created += 1

        settlement = await SettlementCRUD(self.auth, self.db).get(task_id=task_id, user_id=user_id)
        if settlement:
            return
        amount = row.amount if row.amount > 0 else round(row.price * row.qty, 2)
        settlement = await SettlementCRUD(self.auth, self.db).create(
            data={
                "task_id": task_id,
                "user_id": user_id,
                "qty": row.qty,
                "payable_amount": amount,
                "status": SettlementStatus.CONFIRMED.value,
            }
        )
        await SettlementItemCRUD(self.auth, self.db).create(
            data={
                "settlement_id": settlement.id,
                "service_type": row.service_type,
                "service_item": row.service_item,
                "service_task": row.service_task,
                "unit": row.unit,
                "price": row.price,
                "qty": row.qty,
                "amount": amount,
            }
        )
        result.settlement_created += 1

    async def _import_outer(
        self,
        rows: list[OuterSettlementRow],
        company_name: str,
        period: str,
        result: ImportResultSchema,
    ) -> None:
        """导入对外服务项目结算单：创建委托公司，每个实际执行的服务项目落一份报告。

        参数:
        - rows: 该公司的实际执行服务项目行。
        - company_name: 委托方公司名（从文件名解析）。
        - period: 报告周期。
        - result: 导入结果统计。
        """
        if not rows:
            return
        company = await self._get_or_create_company(company_name, result)
        for row in rows:
            service_item = await ServiceItemCRUD(self.auth, self.db).get(service_no=row.service_no)
            if not service_item:
                result.errors.append(f"服务项目号 {row.service_no} 未在库中找到，已跳过")
                continue
            report = await ReportCRUD(self.auth, self.db).get(
                company_id=company.id, service_item_id=service_item.id, period=period
            )
            if report:
                continue
            summary: dict[str, Any] = {
                "service_type": row.service_type,
                "service_item": row.service_item,
                "unit": row.unit,
                "price": row.price,
                "qty": row.qty,
                "amount": row.amount,
            }
            await ReportCRUD(self.auth, self.db).create(
                data={
                    "company_id": company.id,
                    "service_item_id": service_item.id,
                    "period": period,
                    "summary": summary,
                    "status": ReportStatus.GENERATED.value,
                }
            )
            result.report_created += 1

    # ── 报告附件关联 ──────────────────────────────────────────────────

    async def link_report_attachment(self, service_no: int, period: str, attachment: str) -> bool:
        """把报告附件（pptx 相对路径）关联到对应服务项目的报告。

        参数:
        - service_no: 服务项目号（1-37）。
        - period: 报告周期。
        - attachment: 附件相对路径。

        返回:
        - 是否成功关联（服务项目或报告不存在时返回 False）。
        """
        service_item = await ServiceItemCRUD(self.auth, self.db).get(service_no=service_no)
        if not service_item:
            return False
        report = await ReportCRUD(self.auth, self.db).get(service_item_id=service_item.id, period=period)
        if not report:
            return False
        await ReportCRUD(self.auth, self.db).update(id=report.id, data={"attachment": attachment})
        return True

    # ── 基础数据创建 ──────────────────────────────────────────────────

    async def _get_or_create_user(self, executor: str, result: ImportResultSchema) -> int | None:
        """按执行人获取或创建 C 端用户，返回用户 ID（无法识别执行人时返回 None）。

        去重策略：
        - 先按 ``name`` 精确匹配，命中即复用（保证重复导入幂等）；因无法仅凭姓名区分
          「同一人重复导入」与「同名不同人」，命中时追加告警交由运营人工确认；
        - ``name`` 未命中但拼音 ``username`` 已被同音他人占用（如「黄莉」vs「黄丽」同拼
          ``huangli``），则追加数字后缀生成新账号，避免两个不同的人被合并到同一账号；
        - 两者都未命中时按拼音 ``username`` 直接创建。
        """
        if not executor or executor == "未知":
            result.errors.append(f"执行人「{executor}」无法识别，已跳过其成果")
            return None

        # 同名精确命中 → 复用（幂等）；同名可能是「同一人重复导入」或「同名不同人」，
        # 无法仅凭姓名区分，故追加告警交由运营人工确认/拆分
        existing = await UserCRUD(self.auth, self.db).get(name=executor)
        if existing:
            result.warnings.append(
                f"执行人「{executor}」与已有账号（{existing.username}）同名，成果已归并至该账号；若为不同人员请人工拆分"
            )
            return existing.id

        # 同名未命中 → 生成不冲突的拼音账号（同音不同字追加后缀）
        base_username = _username_from_name(executor)
        username = await self._next_available(base_username, UserCRUD(self.auth, self.db), "username")

        # 仿照 UserService.batch_import：先 hash 默认密码，再经 schema 校验。
        # hash 串含字母/数字/符号，天然满足密码强度要求；直接用 CRUD 落库避免二次 hash
        user_schema = UserCreateSchema(
            username=username,
            name=executor,
            password=await PwdUtil.ahash_password(settings.PASSWORD_IMPORT_DEFAULT),
            status=0,
        )
        new_user = await UserCRUD(self.auth, self.db).create(
            data=user_schema.model_dump(exclude_none=True, exclude={"role_ids", "position_ids"})
        )
        result.user_created += 1
        return new_user.id

    async def _next_available(self, base: str, crud: Any, field: str) -> str:
        """生成带数字后缀的唯一值（``base``、``base2``、``base3``…），直至 ``crud.get(field=值)`` 无命中。

        参数:
        - base: 拼音生成的候选前缀（如 ``huangli``）。
        - crud: 已实例化的 CRUD（支持 ``get(**{field: value})`` 关键字查询）。
        - field: 需要保持唯一的字段名（如 ``username`` / ``code``）。

        返回:
        - str: 目标字段在库中不存在的唯一值。
        """
        candidate = base
        suffix = 2
        while await crud.get(**{field: candidate}):
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate

    async def _get_or_create_company(self, company_name: str, result: ImportResultSchema) -> Any:
        """获取或创建委托公司（按公司名幂等，编码用拼音）。

        ``name`` 有唯一约束，精确命中即复用；``code`` 由拼音生成也有唯一约束，
        故同名（不同实体）未命中时对拼音编码追加数字后缀，避免撞唯一约束报错。
        """
        existing = await CompanyCRUD(self.auth, self.db).get(name=company_name)
        if existing:
            return existing
        base_code = _username_from_name(company_name)
        code = await self._next_available(base_code, CompanyCRUD(self.auth, self.db), "code")
        company = await CompanyCRUD(self.auth, self.db).create(data={"name": company_name, "code": code})
        result.company_created += 1
        return company
