"""市场管理域 —— 状态与类型枚举。

统一定义任务、分派、成果、结算单、报告、限额各实体的状态机取值，
以及机构类型枚举，供模型与序列化器共享，避免魔法字符串分散在代码各处。

取值与设计文档《03-流程与状态流转.md》的状态机保持一致（大写字符串）。
"""

from enum import StrEnum


class TaskStatus(StrEnum):
    """任务状态机：草稿 → 发布 → 进行中 → 截止 → 归集中 → 已结算 → 归档。"""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    IN_PROGRESS = "IN_PROGRESS"
    DEADLINE = "DEADLINE"
    SETTLING = "SETTLING"
    SETTLED = "SETTLED"
    ARCHIVED = "ARCHIVED"


class AssignmentStatus(StrEnum):
    """分派/接收状态机：待接收 → 已接收 → 进行中 → 已提交 → 已审核 → 已结算。"""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
    SETTLED = "SETTLED"


class SubmissionStatus(StrEnum):
    """成果状态机：草稿 → 待审核 → 通过 / 驳回（驳回可修改重提，版本 +1）。"""

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SettlementStatus(StrEnum):
    """结算单状态机：待结算 → 已计算 → 已确认 → 已入报告 → 已支付（二期）。"""

    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    PAID = "PAID"


class ReportStatus(StrEnum):
    """报告状态机：草稿 → 已生成 → 已提交。"""

    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    SUBMITTED = "SUBMITTED"


class CarryoverStatus(StrEnum):
    """顺延金额状态：待结算（滚入下一周期）→ 已结算（被下一周期消费）。"""

    PENDING = "PENDING"
    SETTLED = "SETTLED"


class InstitutionType(StrEnum):
    """机构类型（采集/提交对象）。"""

    GRADE_HOSPITAL = "grade_hospital"  # 等级医院
    PRIMARY_CARE = "primary_care"  # 基层医疗
    PRIVATE_MEDICAL = "private_medical"  # 民营医疗
    RETAIL_PHARMACY = "retail_pharmacy"  # 零售药店
    COMMERCIAL = "commercial"  # 商业公司


class AssignMode(StrEnum):
    """任务分配方式：定向分派 / 公开大厅。"""

    DIRECT = "direct"  # 定向分派（运营指定用户）
    OPEN = "open"  # 公开大厅（用户自行接单）


class AssignmentSource(StrEnum):
    """任务实例来源：运营分派 / 大厅接单。"""

    ASSIGNED = "assigned"  # 运营定向分派生成
    CLAIMED = "claimed"  # 用户大厅接单生成
