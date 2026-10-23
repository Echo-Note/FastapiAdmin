"""market 域单元测试：状态枚举、周期推进、表单规则校验等纯逻辑。"""

import pytest

from app.core.exceptions import CustomException
from app.modules.market.enums import (
    AllowanceStatus,
    AssignmentStatus,
    InstitutionType,
    ProjectStatus,
    ReportStatus,
    SettlementStatus,
    SubmissionStatus,
    TaskKind,
    TaskStatus,
)
from app.modules.market.submission.service import _validate_form


class TestEnums:
    """状态与类型枚举取值测试。"""

    def test_task_status_values(self) -> None:
        assert TaskStatus.DRAFT.value == "DRAFT"
        assert TaskStatus.PUBLISHED.value == "PUBLISHED"
        assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TaskStatus.COMPLETED.value == "COMPLETED"
        assert TaskStatus.SETTLING.value == "SETTLING"
        assert TaskStatus.SETTLED.value == "SETTLED"
        assert TaskStatus.ARCHIVED.value == "ARCHIVED"

    def test_task_kind_values(self) -> None:
        assert TaskKind.PERIODIC.value == "periodic"
        assert TaskKind.QUOTA.value == "quota"

    def test_project_status_values(self) -> None:
        assert ProjectStatus.DRAFT.value == "DRAFT"
        assert ProjectStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert ProjectStatus.COMPLETED.value == "COMPLETED"
        assert ProjectStatus.CLOSED.value == "CLOSED"

    def test_assignment_status_values(self) -> None:
        assert AssignmentStatus.PENDING.value == "PENDING"
        assert AssignmentStatus.ACCEPTED.value == "ACCEPTED"
        assert AssignmentStatus.SUBMITTING.value == "SUBMITTING"
        assert AssignmentStatus.SUBMITTED.value == "SUBMITTED"
        assert AssignmentStatus.REVIEWED.value == "REVIEWED"
        assert AssignmentStatus.SETTLED.value == "SETTLED"

    def test_submission_status_values(self) -> None:
        assert SubmissionStatus.DRAFT.value == "DRAFT"
        assert SubmissionStatus.PENDING.value == "PENDING"
        assert SubmissionStatus.APPROVED.value == "APPROVED"
        assert SubmissionStatus.REJECTED.value == "REJECTED"

    def test_settlement_status_values(self) -> None:
        assert SettlementStatus.PENDING.value == "PENDING"
        assert SettlementStatus.CALCULATED.value == "CALCULATED"
        assert SettlementStatus.CONFIRMED.value == "CONFIRMED"
        assert SettlementStatus.REPORTED.value == "REPORTED"
        assert SettlementStatus.PAID.value == "PAID"

    def test_report_status_values(self) -> None:
        assert ReportStatus.DRAFT.value == "DRAFT"
        assert ReportStatus.GENERATED.value == "GENERATED"
        assert ReportStatus.SUBMITTED.value == "SUBMITTED"

    def test_allowance_status_values(self) -> None:
        assert AllowanceStatus.PENDING.value == "PENDING"
        assert AllowanceStatus.PAID.value == "PAID"

    def test_institution_type_values(self) -> None:
        assert InstitutionType.GRADE_HOSPITAL.value == "grade_hospital"
        assert InstitutionType.PRIMARY_CARE.value == "primary_care"
        assert InstitutionType.PRIVATE_MEDICAL.value == "private_medical"
        assert InstitutionType.RETAIL_PHARMACY.value == "retail_pharmacy"
        assert InstitutionType.COMMERCIAL.value == "commercial"


class TestValidateForm:
    """采集表单规则校验测试。"""

    def test_empty_schema_ok(self) -> None:
        _validate_form([], {})  # 空 schema 不报错

    def test_required_missing_raises(self) -> None:
        schema = [{"name": "hospital_name", "label": "医院名称", "required": True}]
        with pytest.raises(CustomException):
            _validate_form(schema, {})

    def test_required_empty_string_raises(self) -> None:
        schema = [{"name": "hospital_name", "label": "医院名称", "required": True}]
        with pytest.raises(CustomException):
            _validate_form(schema, {"hospital_name": ""})

    def test_required_present_ok(self) -> None:
        schema = [{"name": "hospital_name", "label": "医院名称", "required": True}]
        _validate_form(schema, {"hospital_name": "XX医院"})  # 不报错

    def test_optional_missing_ok(self) -> None:
        schema = [{"name": "remark", "label": "备注", "required": False}]
        _validate_form(schema, {})  # 非必填缺失不报错

    def test_field_without_name_skipped(self) -> None:
        schema = [{"label": "无名字段", "required": True}]
        _validate_form(schema, {})  # 无 name 字段跳过，不报错

    def test_missing_required_message_contains_label(self) -> None:
        schema = [{"name": "hospital_name", "label": "医院名称", "required": True}]
        with pytest.raises(CustomException, match="医院名称"):
            _validate_form(schema, {})
