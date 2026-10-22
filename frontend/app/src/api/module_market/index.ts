import { http } from '@/http'

const MARKET_BASE = '/market'

/**
 * market 域分页响应（与后端 PageResultSchema 对齐，字段为 items 而非 list）。
 *
 * 说明：现有 useListPage 组合式函数硬编码读取 `res.list`，与后端返回的 `items`
 * 不一致，故 market 域列表统一使用本类型 + useMarketListPage 读取 `items`。
 */
export interface MarketPageResult<T> {
  items: T[]
  total: number
  page_no?: number
  page_size?: number
  has_next?: boolean
}

/** 任务分派/接收（小程序端任务大厅与我的任务共用） */
export interface AssignmentItem {
  id?: number
  task_id?: number
  user_id?: number
  assign_amount?: number
  status?: string
  accepted_at?: string | null
  submitted_at?: string | null
  task?: {
    id?: number
    task_no?: string
    period?: string
    unit_price?: number
    exec_qty?: number
    status?: string
    deadline_at?: string | null
    company?: { id?: number, name?: string } | null
    task_type?: {
      id?: number
      name?: string
      unit?: string
      form_schema?: FormSchemaField[]
    } | null
  } | null
}

/** 动态表单字段定义（来自任务类型模板的 form_schema） */
export interface FormSchemaField {
  name: string
  label?: string
  type?: 'text' | 'textarea' | 'number' | 'select' | 'date' | 'radio' | 'checkbox'
  required?: boolean
  placeholder?: string
  options?: { label: string, value: string | number }[]
}

/** 成果提交 */
export interface SubmissionItem {
  id?: number
  assignment_id?: number
  user_id?: number
  institution_id?: number
  institution?: { id?: number, name?: string, type?: string } | null
  region?: string | null
  archive_no?: string | null
  form_data?: Record<string, unknown>
  status?: string
  version?: number
  review_comment?: string | null
  reviewed_at?: string | null
}

/** 机构（供成果提交选择） */
export interface InstitutionItem {
  id?: number
  name?: string
  type?: string
  level?: string
  region?: string
  address?: string
}

/** 我的额度/收益 */
export interface QuotaSummary {
  user_id?: number
  period?: string
  quota_amount?: number | null
  received_amount?: number
  payable_amount?: number
  over_amount?: number
  carryover_items?: {
    id?: number
    from_period?: string
    to_period?: string
    amount?: number
    status?: string
  }[]
}

export const MarketAPI = {
  /** 任务大厅：当前用户待接收的任务分派 */
  getTaskHall(params?: Record<string, any>) {
    return http.Get<MarketPageResult<AssignmentItem>>(`${MARKET_BASE}/mini/tasks`, params)
  },

  /** 我的任务：当前用户的全部任务分派 */
  getMyAssignments(params?: Record<string, any>) {
    return http.Get<MarketPageResult<AssignmentItem>>(`${MARKET_BASE}/mini/assignments`, params)
  },

  /** 接收任务 */
  acceptAssignment(id: number): Promise<AssignmentItem> {
    return http.Post(`${MARKET_BASE}/mini/assignments/${id}/accept`)
  },

  /** 提交成果 */
  createSubmission(data: Record<string, any>): Promise<SubmissionItem> {
    return http.Post(`${MARKET_BASE}/mini/submissions`, data)
  },

  /** 修改成果（草稿编辑/驳回重提） */
  updateSubmission(id: number, data: Record<string, any>): Promise<SubmissionItem> {
    return http.Put(`${MARKET_BASE}/mini/submissions/${id}`, data)
  },

  /** 我的成果列表 */
  getMySubmissions(params?: Record<string, any>) {
    return http.Get<MarketPageResult<SubmissionItem>>(`${MARKET_BASE}/mini/submissions`, params)
  },

  /** 我的额度/收益 */
  getMyQuota(period: string) {
    const params: Record<string, any> = { period }
    const method = http.Get<QuotaSummary>(`${MARKET_BASE}/mini/quota`, params)
    method.config.cacheFor = 0
    return method
  },

  /** 机构列表（提交成果选择对象机构，走小程序端 mini 接口，无需运营端 RBAC 权限） */
  getInstitutions(params?: Record<string, any>) {
    return http.Get<MarketPageResult<InstitutionItem>>(`${MARKET_BASE}/mini/institutions`, params)
  },
}
