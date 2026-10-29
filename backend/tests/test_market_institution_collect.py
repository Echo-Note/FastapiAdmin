"""market 域机构归集单元测试。

机构（institution）由 C 端提交成果归集产生，本文件覆盖归集的两个核心纯函数：
``extract_institution_info``（从采集表单提取机构名称/区域/等级）与
``map_institution_type``（按二级模板名映射机构类型）。
"""

from app.modules.market.institution.service import extract_institution_info, map_institution_type


class TestExtractInstitutionInfo:
    """从采集表单 form_data 提取机构信息。"""

    def test_extract_hospital_fields(self) -> None:
        """商务类任务：execution_info 分节的 hospital_name/region/hospital_level。"""
        form_data = {
            "execution_info": {
                "region": "重庆",
                "hospital_name": "重庆市人民医院",
                "hospital_level": "三甲",
                "executor": "熊丽",
            },
            "price_check": {},
        }
        assert extract_institution_info(form_data) == {"name": "重庆市人民医院", "region": "重庆", "level": "三甲"}

    def test_extract_org_name(self) -> None:
        """档案调研类任务：basic_info 分节的 org_name。"""
        form_data = {"basic_info": {"org_name": "万邦医药", "region": "重庆", "credit_code": "91110000A"}}
        assert extract_institution_info(form_data) == {"name": "万邦医药", "region": "重庆", "level": ""}

    def test_no_name_returns_none(self) -> None:
        """无机构名称字段时返回 None，不归集。"""
        form_data = {"execution_info": {"region": "重庆", "executor": "熊丽"}}
        assert extract_institution_info(form_data) is None

    def test_ignores_non_dict_sections(self) -> None:
        """跳过非 dict 分节，仍能提取到机构名称。"""
        form_data = {"execution_info": {"hospital_name": "重庆医院"}, "bad": "not a dict"}
        assert extract_institution_info(form_data) == {"name": "重庆医院", "region": "", "level": ""}

    def test_empty_values_skipped(self) -> None:
        """空值字段不参与匹配，名称缺失返回 None。"""
        form_data = {"execution_info": {"hospital_name": "", "region": ""}}
        assert extract_institution_info(form_data) is None


class TestMapInstitutionType:
    """按二级模板名映射机构类型。"""

    def test_known_templates(self) -> None:
        assert map_institution_type("等级医疗管理") == "grade_hospital"
        assert map_institution_type("基层医疗管理") == "primary_care"
        assert map_institution_type("民营医疗管理") == "private_medical"
        assert map_institution_type("零售药店管理") == "retail_pharmacy"
        assert map_institution_type("商业公司管理") == "commercial"
        assert map_institution_type("市场档案信息调研") == "commercial"

    def test_unknown_template_returns_none(self) -> None:
        """宣传/科普类模板采集对象非机构主数据，返回 None。"""
        assert map_institution_type("产品宣传") is None
        assert map_institution_type("健康科普") is None
        assert map_institution_type("产品培训活动") is None
