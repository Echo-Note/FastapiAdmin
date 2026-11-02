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
  /** 产品库角色：name 列检索产品库并回填同行的 spec / manufacturer 列 */
  product_role?: 'name' | 'spec' | 'manufacturer' | null
}

/** 采集字段定义（对齐后端 form_schema.py FormSchemaField，字段名由外层 dict 的 key 表达） */
export interface FormSchemaField {
  label: string
  type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'radio' | 'checkbox' | 'image' | 'file' | 'table' | 'region'
  required?: boolean
  placeholder?: string
  options?: { label: string, value: string }[]
  /** 子表列定义（仅 type=table 需要） */
  columns?: FormSchemaColumn[]
  /** 自动填充来源(current_user=自动填当前登录用户并只读) */
  autofill?: 'current_user' | null
}

/** 产品库检索候选（对齐后端 ProductSearchItemSchema） */
export interface ProductCandidate {
  id: number
  name: string
  spec: string
  manufacturer: string
  /** 完整展示名：名称 / 规格 / 生产企业 */
  display_name: string
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

/** 三级任务（对齐后端 TaskItemOutSchema） */
export interface TaskItemDetail {
  id?: number
  code?: string
  name?: string
  template_id?: number
  config?: TaskItemConfig | null
  sort?: number
  enabled?: boolean
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
  /** 其下三级任务（对齐后端 TaskTemplateOutSchema.items） */
  items?: TaskItemDetail[]
}

/** 任务所属项目摘要（对齐后端 TaskProjectBriefSchema） */
export interface TaskProjectBrief {
  id?: number
  name?: string
  code?: string | null
}

/** 任务实例（对齐后端 TaskOutSchema） */
export interface TaskItem {
  id?: number
  task_no?: string
  project_id?: number
  /** 所属项目摘要（含项目名，供归属链路展示） */
  project?: TaskProjectBrief | null
  template_id?: number
  template?: TaskTemplateItem | null
  /** 三级任务ID（叶子模板任务为空） */
  item_id?: number | null
  /** 三级任务（嵌套在任务响应中） */
  item?: TaskItemDetail | null
  name?: string
  period?: string
  assign_mode?: string
  status?: string
  publisher_id?: number | null
  published_at?: string | null
  /** 执行标准（后端已扁平透出：item.config 优先，回退 template.config） */
  exec_standard?: string | null
  /** 执行要求（后端已扁平透出：item.config 优先，回退 template.config） */
  executor_requirement?: string | null
  /** 已分派/接收人数（列表聚合字段） */
  assignment_count?: number
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

/** 我的本周进度（对齐后端 mini/week-progress） */
export interface MyWeekProgress {
  week_start?: string
  week_end?: string
  due?: number
  done?: number
  approved?: number
}

/** 我的待办计数（对齐后端 mini/task-stats） */
export interface MyTaskStats {
  pending?: number
  accepted?: number
  submitted?: number
  reviewed?: number
  settled?: number
  rejected_submissions?: number
  submissions_pending?: number
  submissions_approved?: number
}

/** 我的发放/津贴（对齐后端 mini/payout 返回） */
/** C 端收益明细的一行：该周期的一条结算单（收益来源） */
export interface PayoutSettlement {
  id?: number
  task_id?: number
  task_no?: string
  /** 任务名（C 端显示名），即这笔钱的来源 */
  task_name?: string
  category_name?: string | null
  template_name?: string | null
  unit?: string | null
  price?: number | null
  qty?: number
  /** 应发金额 */
  payable?: number
  /** 实发金额（受当月发放额度封顶） */
  paid?: number
  pay_status?: string | null
}

export interface PayoutSummary {
  user_id?: number
  /** 出参所属周期；页面切月只改这个参数，其余数字都由后端按周期给出 */
  period?: string
  /** 当月应发（该周期结算单应发合计，收益卡主数字） */
  payable?: number
  /** 当月实发（该周期结算单实发合计） */
  paid?: number
  payout_limit?: number
  /** 期初滚存（上期期末未发放额） */
  prev_balance?: number
  /** 期末滚存（该期未结算时等于期初） */
  allowance_balance?: number
  /** 该周期结算单列表（按 id 升序） */
  settlements?: PayoutSettlement[]
}

/** C 端按项目分组的任务组（对齐后端 MiniTaskGroupSchema，任务大厅） */
export interface MiniTaskGroup {
  project_id?: number
  project_name?: string
  /** 项目截止日期 */
  period?: string | null
  /** 该项目下最小单元任务（已按 分类→模板→任务 排序） */
  tasks?: TaskItem[]
}

/** C 端按项目分组的分派单组（对齐后端 MiniAssignmentGroupSchema，我的任务） */
export interface MiniAssignmentGroup {
  project_id?: number
  project_name?: string
  /** 项目截止日期 */
  period?: string | null
  /** 该项目下当前用户的分派单（含内嵌 task 归属链路） */
  assignments?: AssignmentItem[]
}

export const MarketAPI = {
  /** 任务大厅：公开接单任务列表（分页平铺） */
  getTaskHall(params?: Record<string, any>) {
    return http.Get<MarketPageResult<TaskItem>>(`${MARKET_BASE}/mini/tasks`, { params })
  },

  /** 任务大厅分组：按项目分组返回全部可见任务（不分页） */
  getTaskHallGrouped(): Promise<MiniTaskGroup[]> {
    return http.Get(`${MARKET_BASE}/mini/tasks/grouped`)
  },

  /** 任务详情（单条） */
  getTaskDetail(taskId: number): Promise<TaskItem> {
    return http.Get(`${MARKET_BASE}/mini/tasks/${taskId}`)
  },

  /** 大厅接单：公开任务由用户自行接单 */
  claimTask(taskId: number): Promise<AssignmentItem> {
    return http.Post(`${MARKET_BASE}/mini/tasks/${taskId}/claim`)
  },

  /** 我的任务：当前用户的全部任务分派 */
  getMyAssignments(params?: Record<string, any>) {
    return http.Get<MarketPageResult<AssignmentItem>>(`${MARKET_BASE}/mini/assignments`, { params })
  },

  /** 我的任务分组：按项目分组返回当前用户分派单（不分页，支持 status 等筛选） */
  getMyAssignmentsGrouped(params?: Record<string, any>): Promise<MiniAssignmentGroup[]> {
    return http.Get(`${MARKET_BASE}/mini/assignments/grouped`, { params })
  },

  /** 任务分派详情（单条，含 task 内嵌） */
  getAssignmentDetail(assignmentId: number): Promise<AssignmentItem> {
    return http.Get(`${MARKET_BASE}/mini/assignments/${assignmentId}`)
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
    return http.Get<MarketPageResult<SubmissionItem>>(`${MARKET_BASE}/mini/submissions`, { params })
  },

  /** 我的发放额度/津贴 */
  /** 我的待办计数（TabBar / 状态 Tab 角标：分派状态分组 + 被驳回成果数） */
  getMyTaskStats() {
    const method = http.Get<MyTaskStats>(`${MARKET_BASE}/mini/task-stats`)
    method.config.cacheFor = 0
    return method
  },

  /** 我的本周进度（工作台顶部进度带） */
  getMyWeekProgress() {
    const method = http.Get<MyWeekProgress>(`${MARKET_BASE}/mini/week-progress`)
    method.config.cacheFor = 0
    return method
  },

  /** 我的成果详情（驳回后修改重提回填原表单；只能读自己的） */
  getMySubmission(id: number) {
    const method = http.Get<SubmissionItem>(`${MARKET_BASE}/mini/submissions/${id}`)
    method.config.cacheFor = 0
    return method
  },

  getMyPayout(period: string) {
    const params: Record<string, any> = { period }
    const method = http.Get<PayoutSummary>(`${MARKET_BASE}/mini/payout`, { params })
    method.config.cacheFor = 0
    return method
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
  /**
   * 产品库检索（提交成果时按产品名称联想）。
   *
   * 可见范围由后端决定：已通过的产品所有人可见，自己提交的待审产品仅本人可见。
   *
   * @param keyword 产品名称关键词
   * @param limit 返回条数上限（默认 20）
   */
  searchProducts(keyword: string, limit = 20): Promise<ProductCandidate[]> {
    return http.Get(`${MARKET_BASE}/mini/products/search`, { params: { keyword, limit } })
  },

  uploadFile(filePath: string): Promise<UniApp.UploadFileSuccessCallbackResult> {
    return http.Post(`${MARKET_BASE}/mini/upload?upload_type=file`, { filePath, name: 'file' }, { requestType: 'upload' })
  },
}
