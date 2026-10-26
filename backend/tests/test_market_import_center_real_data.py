"""market 域成果导入冒烟测试：用真实素材文件验证解析链路（不依赖数据库）。

素材来源：``docs/materials/重庆任务成果素材``。断言对内（熊丽/熊志鹏）与对外（万邦）
结算单的解析行数与金额合计，防止模板格式或解析逻辑回归。该链路服务于前端「成果导入」
页面的上传解析（前端仅透传文件，xlsx 内容解析在后端，故冒烟测试落在后端 parser 层）。
"""

from pathlib import Path

from app.modules.market.import_center.parser import (
    InnerSettlementRow,
    OuterSettlementRow,
    detect_kind,
    parse_inner_settlement,
    parse_outer_settlement,
)

# backend/tests -> backend -> 项目根，再进入 docs/materials
_MATERIALS_DIR = Path(__file__).resolve().parents[2] / "docs" / "materials" / "重庆任务成果素材"


def _parse_inner(person: str) -> list[InnerSettlementRow]:
    """解析指定执行人的对内结算单，返回实际执行行列表。"""
    path = _MATERIALS_DIR / f"重庆-{person}" / f"0.重庆-省平台项目结算单-重庆{person}.xlsx"
    assert path.exists(), f"素材文件不存在: {path}"
    assert detect_kind(str(path)) == "inner"
    return parse_inner_settlement(str(path), person)


def test_real_inner_xiongli() -> None:
    """真实素材：熊丽对内结算单解析 8 行，金额合计 20900。"""
    rows = _parse_inner("熊丽")
    assert len(rows) == 8
    assert sum(r.qty for r in rows) == 59
    assert sum(r.amount for r in rows) == 20900.0
    assert all(r.executor == "熊丽" for r in rows)


def test_real_inner_xiongzhipeng() -> None:
    """真实素材：熊志鹏对内结算单解析 2 行，金额合计 1600。"""
    rows = _parse_inner("熊志鹏")
    assert len(rows) == 2
    assert sum(r.qty for r in rows) == 3
    assert sum(r.amount for r in rows) == 1600.0
    assert all(r.executor == "熊志鹏" for r in rows)


def test_real_outer_wanbang() -> None:
    """真实素材：万邦对外服务项目结算单解析 9 行，金额合计 57400。"""
    path = _MATERIALS_DIR / "项目服务成果（TO 万邦）" / "复星万邦-聚苯乙烯磺酸钙散-服务项目结算单.xlsx"
    assert path.exists(), f"素材文件不存在: {path}"
    assert detect_kind(str(path)) == "outer"
    rows: list[OuterSettlementRow] = parse_outer_settlement(str(path))
    assert len(rows) == 9
    assert sum(r.qty for r in rows) == 73
    assert sum(r.amount for r in rows) == 57400.0
