"""market 域单元测试：状态与类型枚举取值。"""

from app.modules.market.enums import (
    AllowanceStatus,
    AssignmentStatus,
    InstitutionType,
    PricingMode,
    ProjectStatus,
    ReportStatus,
    SettlementStatus,
    SubjectType,
    SubmissionStatus,
    SubmitCadence,
    TaskStatus,
)


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

    def test_subject_type_values(self) -> None:
        assert SubjectType.INSTITUTION.value == "institution"
        assert SubjectType.STAFF.value == "staff"
        assert SubjectType.PATIENT.value == "patient"
        assert SubjectType.MEETING.value == "meeting"

    def test_pricing_mode_values(self) -> None:
        assert PricingMode.FIXED.value == "fixed"
        assert PricingMode.ACTUAL.value == "actual"

    def test_submit_cadence_values(self) -> None:
        assert SubmitCadence.MONTHLY.value == "monthly"
        assert SubmitCadence.ONCE.value == "once"
        assert SubmitCadence.UNLIMITED.value == "unlimited"

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
