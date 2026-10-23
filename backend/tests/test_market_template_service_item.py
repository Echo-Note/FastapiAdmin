"""market 域集成测试：采集模板 / 对外服务项目 / 采集对象抽象 / form_schema 序列化。"""

from fastapi.testclient import TestClient

from app.modules.market.form_schema import FormSchemaField
from app.modules.market.submission.schema import SubmissionCreateSchema


class TestFormSchema:
    """form_schema 结构扩展：section 分节 / table 多行子表 / columns 自引用。"""

    def test_section_type(self) -> None:
        field = FormSchemaField(name=None, label="一、执行信息", type="section")
        assert field.type == "section"
        assert field.name is None

    def test_table_type_with_columns(self) -> None:
        field = FormSchemaField(
            name="delivery",
            label="配送协调明细",
            type="table",
            columns=[
                FormSchemaField(name="product_name", label="产品名称", type="text"),
                FormSchemaField(name="delivery_qty", label="配送数量", type="number"),
            ],
        )
        assert field.type == "table"
        assert len(field.columns) == 2  # type: ignore[arg-type]
        assert field.columns[0].name == "product_name"  # type: ignore[index]

    def test_section_attribute(self) -> None:
        field = FormSchemaField(name="region", label="区域", type="text", section="一、执行信息", required=True)
        assert field.section == "一、执行信息"
        assert field.required is True


class TestSubmissionSubject:
    """采集对象抽象：机构类必填 institution_id，个人类必填 subject_name。"""

    def test_institution_requires_institution_id(self) -> None:
        from pydantic import ValidationError

        try:
            SubmissionCreateSchema(assignment_id=1, subject_type="institution", form_data={})
        except ValidationError:
            return
        raise AssertionError("机构类采集对象缺少 institution_id 应校验失败")

    def test_staff_requires_subject_name(self) -> None:
        from pydantic import ValidationError

        try:
            SubmissionCreateSchema(assignment_id=1, subject_type="staff", form_data={})
        except ValidationError:
            return
        raise AssertionError("个人类采集对象缺少 subject_name 应校验失败")

    def test_patient_with_subject_name_ok(self) -> None:
        schema = SubmissionCreateSchema(assignment_id=1, subject_type="patient", subject_name="患者A", form_data={})
        assert schema.subject_type == "patient"
        assert schema.subject_name == "患者A"
        assert schema.institution_id is None


class TestSeededData:
    """种子数据：模板 / 任务类型（模板关联+计价项字段）/ 服务项目（含映射）。"""

    def test_template_seeded_with_section_and_table(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/templates/list", params={"code": "grade_hospital_manage"}, headers=auth_headers)
        assert resp.json()["success"] is True
        assert resp.json()["data"]["total"] == 1
        item = resp.json()["data"]["items"][0]
        types = {f["type"] for f in item["form_schema"]}
        assert "section" in types
        assert "table" in types

    def test_task_type_has_template_and_pricing_fields(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/task-types/list", params={"code": "grade_hospital_delivery"}, headers=auth_headers)
        assert resp.json()["success"] is True
        item = resp.json()["data"]["items"][0]
        assert item["task_no"] == 5
        assert item["required"] is True
        assert item["min_qty"] == 1
        assert item["template_id"] is not None
        # 任务类型出参携带模板（含 form_schema），供 C 端渲染动态表单
        assert item["template"] is not None
        assert "form_schema" in item["template"]

    def test_task_type_dedup_rule(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/task-types/list", params={"code": "terminal_grade_hospital"}, headers=auth_headers)
        item = resp.json()["data"]["items"][0]
        assert item["dedup_rule"] == "单家终端一个季度只允许调研一次"

    def test_promotion_max_per_period(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/task-types/list", params={"code": "outdoor_academic_promo"}, headers=auth_headers)
        item = resp.json()["data"]["items"][0]
        assert item["max_per_period"] == 20

    def test_service_item_seeded_with_mapping(self, test_client: TestClient, auth_headers: dict) -> None:
        resp = test_client.get("/market/service-items/list", params={"code": "svc_grade_hospital_research"}, headers=auth_headers)
        assert resp.json()["success"] is True
        item = resp.json()["data"]["items"][0]
        assert item["service_no"] == 17
        # 已确认映射：对外 17 等级医院调研 ↔ 对内 27 等级医院调研
        assert 27 in item["task_type_ids"]
