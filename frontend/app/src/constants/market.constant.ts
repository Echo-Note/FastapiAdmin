/**
 * market 域状态/文案/语义色映射（C 端唯一真值源）。
 *
 * 与 Web 端 `frontend/web/src/api/module_market/constants.ts` 保持**同文案 + 同语义色**：
 * - type 取值限定为 wot-ui 支持的 5 类语义色：primary / success / warning / danger / info；
 * - 具体枚举值与后端 `backend/app/modules/market/enums.py` 的状态机一致（大写字符串）。
 *
 * 页面统一从这里导入，不再在页面内联写状态映射。
 */

/** 语义色类型（两端一致） */
export type MarketStatusType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

export interface MarketStatusMeta {
  label: string
  type: MarketStatusType
}

/** 任务状态机 */
export const TASK_STATUS_MAP: Record<string, MarketStatusMeta> = {
  DRAFT: { label: '草稿', type: 'info' },
  PUBLISHED: { label: '已发布', type: 'primary' },
  IN_PROGRESS: { label: '进行中', type: 'warning' },
  COMPLETED: { label: '已完成', type: 'primary' },
  SETTLING: { label: '归集中', type: 'warning' },
  SETTLED: { label: '已结算', type: 'success' },
  ARCHIVED: { label: '已归档', type: 'info' },
}

/** 任务分类（task_kind：周期性 / 定额） */
export const TASK_KIND_MAP: Record<string, MarketStatusMeta> = {
  periodic: { label: '周期性', type: 'info' },
  quota: { label: '定额', type: 'warning' },
}

/** 分派/接收状态机 */
export const ASSIGNMENT_STATUS_MAP: Record<string, MarketStatusMeta> = {
  PENDING: { label: '待接收', type: 'info' },
  ACCEPTED: { label: '已接收', type: 'primary' },
  SUBMITTING: { label: '进行中', type: 'warning' },
  SUBMITTED: { label: '已提交', type: 'warning' },
  REVIEWED: { label: '已审核', type: 'success' },
  SETTLED: { label: '已结算', type: 'success' },
}

/** 成果状态机 */
export const SUBMISSION_STATUS_MAP: Record<string, MarketStatusMeta> = {
  DRAFT: { label: '草稿', type: 'info' },
  PENDING: { label: '待审核', type: 'warning' },
  APPROVED: { label: '已通过', type: 'success' },
  REJECTED: { label: '已驳回', type: 'danger' },
}

/** 结算单状态机 */
export const SETTLEMENT_STATUS_MAP: Record<string, MarketStatusMeta> = {
  PENDING: { label: '待结算', type: 'info' },
  CALCULATED: { label: '已计算', type: 'warning' },
  CONFIRMED: { label: '已确认', type: 'primary' },
  REPORTED: { label: '已入报告', type: 'success' },
  PAID: { label: '已支付', type: 'success' },
}

/** 津贴明细状态 */
export const ALLOWANCE_STATUS_MAP: Record<string, MarketStatusMeta> = {
  PENDING: { label: '待发放', type: 'warning' },
  PAID: { label: '已发放', type: 'success' },
}

/**
 * 取状态展示元信息；未命中时回退为 info 灰 + 原值。
 */
export function statusMeta(map: Record<string, MarketStatusMeta>, status?: string | null): MarketStatusMeta {
  if (!status)
    return { label: '-', type: 'info' }
  return map[status] ?? { label: status, type: 'info' }
}

/**
 * 任务分类文案（任务大厅 / 我的任务共用）。
 */
export function taskKindText(kind?: string): string {
  return TASK_KIND_MAP[kind ?? '']?.label ?? '周期性'
}
