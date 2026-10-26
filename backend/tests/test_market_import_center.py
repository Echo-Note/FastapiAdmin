"""market 域导入中心单元测试：文件名/拼音转换 + 结算单解析（不依赖数据库）。

覆盖 parser.py 的纯函数（_to_float/_to_int/_forward_fill/detect_kind/parse_*）与
service.py 的文件名约定解析函数（_username_from_name/_company_name_from_filename/_executor_from_filename）。
"""

from pathlib import Path

from openpyxl import Workbook

from app.modules.market.import_center.parser import (
    _forward_fill,
    _to_float,
    _to_int,
    detect_kind,
    parse_inner_settlement,
    parse_outer_settlement,
)
from app.modules.market.import_center.service import (
    _company_name_from_filename,
    _executor_from_filename,
    _username_from_name,
)


def _write_xlsx(path: Path, rows: list[list]) -> None:
    """把二维列表写入 xlsx 文件（单 sheet，None 记为空格）。"""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(path)


class TestFilenameHelpers:
    """文件名约定解析与拼音账号生成。"""

    def test_username_from_name(self) -> None:
        assert _username_from_name("熊丽") == "xiongli"
        assert _username_from_name("熊志鹏") == "xiongzhipeng"

    def test_username_same_pinyin(self) -> None:
        """同音不同字（黄莉/黄丽）拼音相同，需靠 service 层数字后缀去重。"""
        assert _username_from_name("黄莉") == "huangli"
        assert _username_from_name("黄丽") == "huangli"

    def test_company_name_from_filename(self) -> None:
        assert _company_name_from_filename("复星万邦-聚苯乙烯磺酸钙散-服务项目结算单.xlsx") == "复星万邦"
        assert _company_name_from_filename("华润三九-某产品-服务项目结算单.xlsx") == "华润三九"

    def test_company_name_empty_prefix(self) -> None:
        """首段为空（文件名以连字符开头）时返回 None。"""
        assert _company_name_from_filename("-服务项目结算单.xlsx") is None

    def test_executor_from_filename(self) -> None:
        assert _executor_from_filename("0.重庆-省平台项目结算单-重庆熊丽.xlsx") == "熊丽"
        assert _executor_from_filename("0.重庆-省平台项目结算单-重庆熊志鹏.xlsx") == "熊志鹏"


class TestCellConverters:
    """单元格值类型转换。"""

    def test_to_float(self) -> None:
        assert _to_float(None) == 0.0
        assert _to_float(1234) == 1234.0
        assert _to_float("1,234") == 1234.0
        assert _to_float("/") == 0.0
        assert _to_float("-") == 0.0
        assert _to_float("abc") == 0.0
        assert _to_float("3.14") == 3.14

    def test_to_int(self) -> None:
        assert _to_int(None) == 0
        assert _to_int("4") == 4
        assert _to_int(2.9) == 2


class TestForwardFill:
    """合并单元格纵向向下填充。"""

    def test_fill_merged_columns(self) -> None:
        rows = [[1, "A", None], [2, None, "B"]]
        filled = _forward_fill(rows, {1})
        assert filled[0][1] == "A"
        assert filled[1][1] == "A"  # None 继承上一行同列
        assert filled[1][2] == "B"  # 非填充列不受影响

    def test_original_not_mutated(self) -> None:
        rows = [[1, "A"], [2, None]]
        _forward_fill(rows, {1})
        assert rows[1][1] is None  # 原列表不被修改


class TestDetectKind:
    """结算单文件类型识别。"""

    def test_inner(self, tmp_path: Path) -> None:
        p = tmp_path / "inner.xlsx"
        _write_xlsx(p, [["市场管理服务结算清单"], ["任务\n序号", "实际执行", "数量"]])
        assert detect_kind(str(p)) == "inner"

    def test_outer(self, tmp_path: Path) -> None:
        p = tmp_path / "outer.xlsx"
        _write_xlsx(p, [["服务项目结算单"], ["序号", "服务项目", "小计"]])
        assert detect_kind(str(p)) == "outer"

    def test_unknown(self, tmp_path: Path) -> None:
        p = tmp_path / "unknown.xlsx"
        _write_xlsx(p, [["标题"], ["其它", "内容"]])
        assert detect_kind(str(p)) is None


class TestParseInner:
    """对内结算单解析：合并单元格 fill + 仅保留实际执行行。"""

    def test_parse_rows(self, tmp_path: Path) -> None:
        p = tmp_path / "0.重庆-省平台项目结算单-重庆熊丽.xlsx"
        _write_xlsx(
            p,
            [
                ["市场管理服务结算清单"],
                ["任务\n序号", "服务项目", None, None, "费用标准", None, "执行要求", None, "实际执行", None],
                [None, "类型", "项目", "任务", "单位", "单价", "执行数量", "执行标准", "数量", "费用金额"],
                [1, "终端服务", "空白市场开发", "空白等级医院开发", "元/家", 25000, "非必选", "/", None, None],
                [2, None, None, "空白基层医疗进院开发", None, 10000, None, None, 5, 50000],
            ],
        )
        rows = parse_inner_settlement(str(p), "熊丽")
        assert len(rows) == 1  # 仅 task_no=2 数量 > 0
        r = rows[0]
        assert r.task_no == 2
        assert r.executor == "熊丽"
        assert r.qty == 5
        assert r.amount == 50000.0
        assert r.price == 10000.0
        # 纵向合并的「类型/项目/单位」向下填充自上一行
        assert r.service_type == "终端服务"
        assert r.service_item == "空白市场开发"
        assert r.unit == "元/家"
        assert r.service_task == "空白基层医疗进院开发"
        assert r.required is False

    def test_required_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "inner.xlsx"
        _write_xlsx(
            p,
            [
                ["市场管理服务结算清单"],
                ["任务\n序号", "服务项目", None, None, "费用标准", None, "执行要求", None, "实际执行", None],
                [None, "类型", "项目", "任务", "单位", "单价", "执行数量", "执行标准", "数量", "费用金额"],
                [5, "终端服务", "等级医院管理", "配送协调", "元/月/家", 1000, "必选\n（1家起）", "完成2项", 4, 4000],
            ],
        )
        rows = parse_inner_settlement(str(p), "熊丽")
        assert len(rows) == 1
        assert rows[0].required is True


class TestParseOuter:
    """对外服务项目结算单解析。"""

    def test_parse_rows(self, tmp_path: Path) -> None:
        p = tmp_path / "复星万邦-服务项目结算单.xlsx"
        _write_xlsx(
            p,
            [
                ["服务项目结算单"],
                ["序号", "服务项目", None, "计费单位", "单价", "数量", "小计"],
                [1, "合作开发服务", "空白等级医院开发", "元/家", 25000, None, 0],
                [2, None, "空白基层医疗进院开发", None, 10000, 3, 30000],
            ],
        )
        rows = parse_outer_settlement(str(p))
        assert len(rows) == 1  # 仅 service_no=2 数量 > 0
        r = rows[0]
        assert r.service_no == 2
        assert r.qty == 3
        assert r.amount == 30000.0
        assert r.price == 10000.0
        # 纵向合并的「类型/单位」向下填充自上一行
        assert r.service_type == "合作开发服务"
        assert r.service_item == "空白基层医疗进院开发"
        assert r.unit == "元/家"
