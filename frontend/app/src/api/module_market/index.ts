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

/** 多行子表（type=table）的子列定义（对齐后端 FormSchemaColumn，不允许再嵌套 table） */
export interface FormSchemaColumn {
  name: string
  label: string
  type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'radio' | 'checkbox' | 'image' | 'file'
  required?: boolean
  placeholder?: string
  options?: { label: string, value: string }[]
}

/** 采集字段定义（对齐后端 form_schema.py FormSchemaField，字段名由外层 dict 的 key 表达） */
export interface FormSchemaField {
  label: string
  type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'radio' | 'checkbox' | 'image' | 'file' | 'table'
  required?: boolean
  placeholder?: string
  options?: { label: string, value: string }[]
  /** 子表列定义（仅 type=table 需要） */
  columns?: FormSchemaColumn[]
}

/** 采集表单分节：英文 code + 中文 name + 其下字段（对齐后端 FormSchemaSection） */
export interface FormSchemaSection {
  code: string
  name: string
  /** 分节是否必填（标题展示「(必填)」标记） */
  required?: boolean
  fields: Record<string, FormSchemaField>
}

/** 采集表单结构：有序分节列表 */
export type FormSchema = FormSchemaSection[]

/** 任务设计配置（对齐后端 config.py TaskConfig，JSONB 宿主） */
export interface TaskConfig {
  subject_type?: string
  unit?: string
  pricing_mode?: string
  price?: number | null
  exec_standard?: string | null
  executor_requirement?: string | null
  submit_rule?: { cadence?: string, max_per_day?: number | null, dedup?: string | null }
  form_schema?: FormSchema
  report_required?: boolean
}

/** 三级任务设计配置（对齐后端 config.py TaskItemConfig） */
export interface TaskItemConfig {
  form_schema?: FormSchema
  unit?: string | null
  price?: number | null
  exec_standard?: string | null
  executor_requirement?: string | null
  max_per_month?: number | null
}

/** 一级任务分类（对齐后端 TaskCategoryOutSchema） */
export interface TaskCategoryItem {
  id?: number
  code?: string
  name?: string
  sort?: number
  description?: string | null
}

/** 二级任务模板（对齐后端 TaskTemplateOutSchema） */
export interface TaskTemplateItem {
  id?: number
  code?: string
  name?: string
  category_id?: number
  category?: TaskCategoryItem | null
  config?: TaskConfig | null
  enabled?: boolean
}

/** 任务实例（对齐后端 TaskOutSchema） */
export interface TaskItem {
  id?: number
  task_no?: string
  project_id?: number
  template_id?: number
  template?: TaskTemplateItem | null
  name?: string
  period?: string
  assign_mode?: string
  status?: string
  publisher_id?: number | null
  published_at?: string | null
}

/** 任务分配/接收（对齐后端 AssignmentOutSchema） */
export interface AssignmentItem {
  id?: number
  task_id?: number
  task?: TaskItem | null
  user_id?: number
  source?: string
  status?: string
  accepted_at?: string | null
  submitted_at?: string | null
}

/** 成果提交（对齐后端 SubmissionOutSchema） */
export interface SubmissionItem {
  id?: number
  assignment_id?: number
  user_id?: number
  subject_type?: string
  institution_id?: number | null
  subject_name?: string | null
  region?: string | null
  archive_no?: string | null
  period?: string
  form_data?: Record<string, unknown>
  status?: string
  version?: number
  reviewer_id?: number | null
  review_comment?: string | null
  reviewed_at?: string | null
  ai_check_status?: string | null
  ai_check_result?: Record<string, unknown> | null
}

/** 机构（对齐后端 InstitutionOutSchema，供成果提交选择） */
export interface InstitutionItem {
  id?: number
  name?: string
  type?: string
  level?: string | null
  region?: string | null
  address?: string | null
  contact?: string | null
  contact_phone?: string | null
  status?: number
}

/** 我的发放/津贴（对齐后端 mini/payout 返回） */
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
    paid_at?: string | null
  }[]
}

export const MarketAPI = {
  /** 任务大厅：公开接单任务列表 */
  getTaskHall(params?: Record<string, any>) {
    return http.Get<MarketPageResult<TaskItem>>(`${MARKET_BASE}/mini/tasks`, params)
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

  /** 我的成果列表 */
  getMySubmissions(params?: Record<string, any>) {
    return http.Get<MarketPageResult<SubmissionItem>>(`${MARKET_BASE}/mini/submissions`, params)
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
