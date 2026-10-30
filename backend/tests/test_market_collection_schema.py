"""market 域单元测试：机构管理采集表 form_schema 与生成源的一致性。

`app.modules.market.task.collection_schema` 是种子与存量订正共用的生成源，
本测试保证种子 JSON 不会与它漂移（否则新库与老库的字段会不一致）。
"""

import json

import pytest

from app.config.path_conf import SCRIPT_DIR
from app.modules.market.task.collection_schema import (
    EXCEPTION_FIELD,
    ITEM_FORM_SCHEMAS,
    UNALIGNED_ITEM_CODES,
    build_form_schema,
)

# 对齐范围内的 26 个三级任务：等级/基层/民营各 5、零售 6、商业 5
_EXPECTED_ALIGNED = 26


def _load_seed_items() -> dict[str, dict]:
    data = json.loads((SCRIPT_DIR / "market_task_item.json").read_text(encoding="utf-8"))
    return {item["code"]: item for item in data}


def _seed_schema(code: str) -> list[dict]:
    """读种子里的 form_schema，并按脚本同样的剪枝规则归一（去掉 False 的 required / None 值）。"""
    config = _load_seed_items()[code]["config"]
    return _prune(config["form_schema"])


def _prune(value):
    if isinstance(value, dict):
        return {k: _prune(v) for k, v in value.items() if not (k == "required" and v is False) and v is not None}
    if isinstance(value, list):
        return [_prune(item) for item in value]
    return value


def _generated_schema(code: str) -> list[dict]:
    schema = ITEM_FORM_SCHEMAS[code]
    return _prune([section.model_dump(exclude_none=True) for section in schema])


class TestSeedMatchesGenerator:
    def test_aligned_scope_size(self) -> None:
        """对齐范围是 26 个三级任务，且不含素材缺失的 ITEM-0027/ITEM-0028。"""
        assert len(ITEM_FORM_SCHEMAS) == _EXPECTED_ALIGNED
        for code in UNALIGNED_ITEM_CODES:
            assert code not in ITEM_FORM_SCHEMAS
            assert build_form_schema(code) is None

    @pytest.mark.parametrize("code", sorted(ITEM_FORM_SCHEMAS))
    def test_seed_matches_generated_schema(self, code: str) -> None:
        """每个三级任务的种子 form_schema 与生成源逐字一致。"""
        assert _seed_schema(code) == _generated_schema(code)

    def test_unaligned_items_untouched(self) -> None:
        """素材缺失的三级任务保留原有 form_schema（本轮不对齐）。"""
        items = _load_seed_items()
        for code in UNALIGNED_ITEM_CODES:
            schema = items[code]["config"]["form_schema"]
            assert schema, f"{code} 应保留原有 form_schema"


class TestAlignedContent:
    def test_delivery_coordination_has_eight_columns(self) -> None:
        """配送协调对齐真实采集表：8 列（含产品规格/生产企业/验收情况/配送商业）+ 异常说明。"""
        section = next(s for s in ITEM_FORM_SCHEMAS["ITEM-0011"] if s.code == "delivery_coordination")
        columns = section.fields["delivery_coordination"].columns
        assert [c.label for c in columns] == [
            "产品名称",
            "产品规格",
            "生产企业",
            "批号",
            "配送数量",
            "配送时间",
            "验收情况",
            "配送商业",
        ]
        assert EXCEPTION_FIELD in section.fields

    def test_commercial_delivery_ends_with_terminal_org(self) -> None:
        """商业公司管理的配送协调末列是「终端机构」，不是「配送商业」。"""
        section = next(s for s in ITEM_FORM_SCHEMAS["ITEM-0023"] if s.code == "delivery_coordination")
        columns = section.fields["delivery_coordination"].columns
        assert columns[-1].label == "终端机构"

    @pytest.mark.parametrize(
        ("code", "field_name", "label"),
        [
            ("ITEM-0001", "hospital_level", "医院等级"),  # 等级医院管理
            ("ITEM-0006", "org_type", "机构类型"),  # 基层医疗管理
            ("ITEM-0011", "entity_type", "单体／集团"),  # 民营医疗管理
            ("ITEM-0017", "chain_type", "连锁／单体"),  # 零售药店管理
            ("ITEM-0023", "org_name", "商业公司名称"),  # 商业公司管理
        ],
    )
    def test_execution_info_has_institution_specific_field(self, code: str, field_name: str, label: str) -> None:
        """执行信息带各机构类型的专属字段，且执行人仍是自动填充只读。"""
        execution = ITEM_FORM_SCHEMAS[code][0]
        assert execution.code == "execution_info"
        assert execution.fields[field_name].label == label
        assert execution.fields["executor"].autofill == "current_user"

    def test_sections_ordered_like_excel(self) -> None:
        """分节顺序对齐采集表：执行信息 → 工作区 → 管理核实。"""
        for code, schema in ITEM_FORM_SCHEMAS.items():
            codes = [section.code for section in schema]
            assert codes[0] == "execution_info", code
            assert codes[-1] == "management_verification", code
            assert len(codes) == 3, code

    def test_product_columns_carry_product_role(self) -> None:
        """产品三要素列带 product_role，供 C 端检索产品库并回填。"""
        section = next(s for s in ITEM_FORM_SCHEMAS["ITEM-0011"] if s.code == "delivery_coordination")
        roles = {c.name: c.product_role for c in section.fields["delivery_coordination"].columns}
        assert roles["product_name"] == "name"
        assert roles["product_spec"] == "spec"
        assert roles["manufacturer"] == "manufacturer"

    def test_competitor_rows_do_not_use_product_keys(self) -> None:
        """竞品调研用 competitor_* 前缀，避免竞品被当成自家产品检索/入库。"""
        section = next(s for s in ITEM_FORM_SCHEMAS["ITEM-0014"] if s.code == "competitor_research")
        columns = section.fields["competitor_research"].columns
        assert [c.name for c in columns][:3] == ["competitor_name", "competitor_spec", "competitor_manufacturer"]
        assert all(c.product_role is None for c in columns)
        # 竞品调研没有「异常说明」，表后是优势/劣势
        assert EXCEPTION_FIELD not in section.fields
        assert {"advantage", "disadvantage"} <= set(section.fields)

    def test_display_optimization_is_image_not_table(self) -> None:
        """陈列优化真实采集表只有一个「陈列照片」，不是多行子表。"""
        section = next(s for s in ITEM_FORM_SCHEMAS["ITEM-0016"] if s.code == "display_optimization")
        assert section.fields["display_photo"].type == "image"
        assert all(f.type != "table" for f in section.fields.values())
