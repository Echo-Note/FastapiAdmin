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

/** 公开任务（任务大厅展示，对应后端 TaskOutSchema） */
export interface TaskItem {
  id?: number
  task_no?: string
  task_type_id?: number
  task_type?: { id?: number, name?: string, unit?: string, exec_standard?: string | null, form_schema?: FormSchemaField[] } | null
  task_kind?: string
  period?: string
  exec_time_start?: string | null
  exec_time_end?: string | null
  unit_price?: number
  exec_qty?: number
  assign_mode?: string
  claimed_count?: number
  status?: string
  published_at?: string | null
}

/** 任务分派/接收（我的任务） */
export interface AssignmentItem {
  id?: number
  task_id?: number
  user_id?: number
  source?: string
  status?: string
  accepted_at?: string | null
  submitted_at?: string | null
  task?: {
    id?: number
    task_no?: string
    task_kind?: string
    period?: string
    unit_price?: number
    exec_qty?: number
    status?: string
    exec_time_end?: string | null
    task_type?: {
      id?: number
      name?: string
      unit?: string
      form_schema?: FormSchemaField[]
    } | null
  } | null
}

/** 我的收益汇总（后端 /market/mini/summary） */
export interface EarningsSummary {
  period?: string
  month_payable?: number
  settlement_count?: number
  allowance_balance?: number
  payout_limit?: number
}

/** 我的待办计数（后端 /market/mini/task-stats） */
export interface TaskStats {
  pending?: number
  accepted?: number
  submitting?: number
  submitted?: number
  reviewed?: number
  settled?: number
  rejected_submissions?: number
}

/** 动态表单字段定义（来自任务类型模板的 form_schema） */
export interface FormSchemaField {
  name: string
  label?: string
  type?: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'radio' | 'checkbox' | 'image' | 'file'
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

/** 我的发放/津贴（对应后端 mini/payout 返回） */
export interface PayoutSummary {
  user_id?: number
  period?: string
  payout_limit?: number
  allowance_balance?: number
  allowance_items?: {
    id?: number
    user_id?: number
    from_period?: string
    amount?: number
    status?: string
  }[]
}

export const MarketAPI = {
  /** 任务大厅：公开接单任务列表 */
  getTaskHall(params?: Record<string, any>) {
    return http.Get<MarketPageResult<TaskItem>>(`${MARKET_BASE}/mini/tasks`, params)
  },

  /**
   * 任务大厅任务详情（C 端）
   *
   * 不能用 `/market/tasks/detail/{id}`：该接口要求 `module_market:task:query` 权限码，
   * C 端用户调用必然 403。mini 详情接口的可见范围与大厅列表一致。
   */
  getTaskDetail(taskId: number) {
    const method = http.Get<TaskItem>(`${MARKET_BASE}/mini/tasks/${taskId}`)
    method.config.cacheFor = 0
    return method
  },

  /** 大厅接单：公开任务由用户自行接单 */
  claimTask(taskId: number): Promise<AssignmentItem> {
    return http.Post(`${MARKET_BASE}/mini/tasks/${taskId}/claim`)
  },

  /** 我的任务：当前用户的全部任务分派 */
  getMyAssignments(params?: Record<string, any>) {
    return http.Get<MarketPageResult<AssignmentItem>>(`${MARKET_BASE}/mini/assignments`, params)
  },

  /** 接收任务（定向分派） */
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

  /** 我的成果详情（驳回后修改重提回填原表单；只能看自己的成果） */
  getMySubmission(id: number) {
    const method = http.Get<SubmissionItem>(`${MARKET_BASE}/mini/submissions/${id}`)
    method.config.cacheFor = 0
    return method
  },

  /** 我的成果列表 */
  getMySubmissions(params?: Record<string, any>) {
    return http.Get<MarketPageResult<SubmissionItem>>(`${MARKET_BASE}/mini/submissions`, params)
  },

  /** 我的收益汇总（「我的」页收益卡：本月应发 / 津贴余额 / 发放额度） */
  getMySummary(period?: string) {
    const params: Record<string, any> = {}
    if (period)
      params.period = period
    const method = http.Get<EarningsSummary>(`${MARKET_BASE}/mini/summary`, params)
    method.config.cacheFor = 0
    return method
  },

  /** 我的待办计数（Tab 角标：分派状态计数 + 被驳回成果数） */
  getMyTaskStats() {
    const method = http.Get<TaskStats>(`${MARKET_BASE}/mini/task-stats`)
    method.config.cacheFor = 0
    return method
  },

  /** 我的发放额度/津贴 */
  getMyPayout(period: string) {
    const params: Record<string, any> = { period }
    const method = http.Get<PayoutSummary>(`${MARKET_BASE}/mini/payout`, params)
    method.config.cacheFor = 0
    return method
  },

  /** 机构列表（提交成果选择对象机构，走小程序端 mini 接口，无需运营端 RBAC 权限） */
  getInstitutions(params?: Record<string, any>) {
    return http.Get<MarketPageResult<InstitutionItem>>(`${MARKET_BASE}/mini/institutions`, params)
  },

  /**
   * 采集成果文件上传（图片/附件）
   *
   * 走统一 http 层 upload（`requestType: 'upload'`），上传到 `/common/file/upload`，
   * upload_type=file（通用文件）。返回 uni.uploadFile 成功结果，调用方需解析
   * `JSON.parse(res.data).data.file_url` 得到文件访问地址。
   *
   * @param filePath 本地临时文件路径（uni.chooseImage / uni.chooseFile 选择结果）
   * @returns uni.uploadFile 成功回调结果（statusCode + data 响应体字符串）
   */
  uploadFile(filePath: string): Promise<UniApp.UploadFileSuccessCallbackResult> {
    return http.Post('/common/file/upload?upload_type=file', { filePath, name: 'file' }, { requestType: 'upload' })
  },
}
