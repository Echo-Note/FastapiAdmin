"""成果导入解析器。

把成果素材 xlsx 解析成结构化数据（``dataclass``），供导入服务写库使用。
仅做「读取 + 结构化」，不涉及任何数据库操作。

对内/对外结算单均为「合并单元格 + 跨行省略」的报表结构：纵向合并的
「类型 / 项目 / 单位 / 单价 / 必选 / 标准」等定义列需向下填充（forward fill），
而「实际执行数量 / 金额」是稀疏数据（仅实际执行的行有值），不可填充。
"""

from dataclasses import dataclass
from typing import Any

from openpyxl import load_workbook

# 对内结算单需向下填充的「定义列」索引（类型/项目/单位/单价/必选/执行标准）
_INNER_FILL_COLS = {1, 2, 4, 5, 6, 7}
# 对外结算单需向下填充的「定义列」索引（类型/项目/单位/单价）
_OUTER_FILL_COLS = {1, 2, 3, 4}


@dataclass(frozen=True)
class InnerSettlementRow:
    """对内结算单中「实际执行」的一条计价项。

    对应结算单里「实际执行-数量」大于 0 的行，是任务归集结算的输入。
    """

    task_no: int  # 计价项序号（1-44，对应 market_task_type.task_no）
    service_type: str  # 三级-类型
    service_item: str  # 三级-项目
    service_task: str  # 三级-任务
    unit: str  # 计价单位
    price: float  # 单价
    qty: int  # 实际执行数量
    amount: float  # 费用金额
    executor: str  # 执行人（熊丽 / 熊志鹏）
    required: bool  # 是否必选
    exec_standard: str | None  # 执行标准


@dataclass(frozen=True)
class OuterSettlementRow:
    """对外服务项目结算单中「实际执行」的一条服务项目。

    对应结算单里「数量」大于 0 的行，是对外报告/结算的输入。
    """

    service_no: int  # 服务项目号（1-37，对应 market_service_item.service_no）
    service_type: str  # 对外两级-类型
    service_item: str  # 对外两级-项目
    unit: str  # 计费单位
    price: float  # 单价
    qty: int  # 数量
    amount: float  # 小计


def _to_float(value: Any) -> float:
    """把单元格值转为 float：None/空 → 0，数字字符串去千分位，其余按 float 解析。"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text in ("/", "-", "—"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _to_int(value: Any) -> int:
    """把单元格值转为 int，用于数量类字段。"""
    return int(_to_float(value))


def _forward_fill(rows: list[list[Any]], columns: set[int]) -> list[list[Any]]:
    """对指定列的纵向合并单元格做向下填充：None 继承上一行同列的值。

    参数:
    - rows: 数据行（二维列表）。
    - columns: 需要向下填充的列索引集合。

    返回:
    - 填充后的数据行副本。
    """
    filled = [row[:] for row in rows]
    for i in range(1, len(filled)):
        prev = filled[i - 1]
        row = filled[i]
        for idx in columns:
            if idx < len(row) and row[idx] is None and idx < len(prev):
                # 用上一行同列值填充（类型/项目等纵向合并列）
                row[idx] = prev[idx]
    return filled


def parse_inner_settlement(path: str, executor: str) -> list[InnerSettlementRow]:
    """解析对内结算单，返回「实际执行数量 > 0」的计价项列表。

    参数:
    - path: xlsx 文件路径。
    - executor: 执行人（从文件名反查）。

    返回:
    - 实际执行的计价项列表。
    """
    wb = load_workbook(path, data_only=True)
    rows: list[InnerSettlementRow] = []
    for ws in wb.worksheets:
        raw = [list(r) for r in ws.iter_rows(values_only=True)]
        # 定位表头行：含「任务」与「序号」的那一行
        header_idx = next(
            (i for i, r in enumerate(raw) if r and any("任务" in str(c) and "序号" in str(c) for c in r if c)),
            None,
        )
        if header_idx is None:
            continue
        data = _forward_fill(raw[header_idx + 1 :], _INNER_FILL_COLS)
        for r in data:
            if r is None or not r or r[0] is None:
                continue
            task_no = _to_int(r[0])
            qty = _to_int(r[8]) if len(r) > 8 else 0
            if task_no <= 0 or qty <= 0:
                continue
            required = str(r[6]).strip().startswith("必选") if len(r) > 6 and r[6] else False
            rows.append(
                InnerSettlementRow(
                    task_no=task_no,
                    service_type=str(r[1] or ""),
                    service_item=str(r[2] or ""),
                    service_task=str(r[3] or ""),
                    unit=str(r[4] or ""),
                    price=_to_float(r[5]) if len(r) > 5 else 0.0,
                    qty=qty,
                    amount=_to_float(r[9]) if len(r) > 9 else 0.0,
                    executor=executor,
                    required=required,
                    exec_standard=str(r[7]) if len(r) > 7 and r[7] else None,
                )
            )
    return rows


def parse_outer_settlement(path: str) -> list[OuterSettlementRow]:
    """解析对外服务项目结算单，返回「数量 > 0」的服务项目列表。

    参数:
    - path: xlsx 文件路径。

    返回:
    - 实际执行的服务项目列表。
    """
    wb = load_workbook(path, data_only=True)
    rows: list[OuterSettlementRow] = []
    for ws in wb.worksheets:
        raw = [list(r) for r in ws.iter_rows(values_only=True)]
        header_idx = next(
            (i for i, r in enumerate(raw) if r and any("序号" in str(c) for c in r if c)),
            None,
        )
        if header_idx is None:
            continue
        data = _forward_fill(raw[header_idx + 1 :], _OUTER_FILL_COLS)
        for r in data:
            if r is None or not r or r[0] is None:
                continue
            service_no = _to_int(r[0])
            qty = _to_int(r[5]) if len(r) > 5 else 0
            if service_no <= 0 or qty <= 0:
                continue
            rows.append(
                OuterSettlementRow(
                    service_no=service_no,
                    service_type=str(r[1] or ""),
                    service_item=str(r[2] or ""),
                    unit=str(r[3] or ""),
                    price=_to_float(r[4]) if len(r) > 4 else 0.0,
                    qty=qty,
                    amount=_to_float(r[6]) if len(r) > 6 else 0.0,
                )
            )
    return rows


def detect_kind(path: str) -> str | None:
    """识别结算单文件类型。

    参数:
    - path: xlsx 文件路径。

    返回:
    - "inner"（对内结算单）/ "outer"（对外服务项目结算单）/ None（无法识别）。
    """
    wb = load_workbook(path, data_only=True)
    headers: list[str] = []
    for ws in wb.worksheets:
        # 提取每个 sheet 前 4 行的所有单元格（覆盖标题行 + 表头行）
        for row in ws.iter_rows(max_row=4, values_only=True):
            headers.extend(str(c) for c in row if c)
    joined = " ".join(headers)
    # 对内结算单有「实际执行」列，对外结算单有「小计」列，二者互斥
    if "实际执行" in joined:
        return "inner"
    if "小计" in joined:
        return "outer"
    return None
