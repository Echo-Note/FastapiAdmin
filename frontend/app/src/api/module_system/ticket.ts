import { http } from '@/http'

const SYSTEM_BASE = '/system'

/**
 * 工单管理 API
 * 与 web 端 module_system/ticket.ts 对齐（完整字段定义）
 */
export const TicketAPI = {
  getPage(params?: Record<string, any>) {
    return http.Get<PageResult<TicketItem>>(`${SYSTEM_BASE}/ticket/list`, params)
  },
  getDetail(id: number) {
    const method = http.Get<TicketItem>(`${SYSTEM_BASE}/ticket/detail/${id}`)
    method.config.cacheFor = 0
    return method
  },
  create(data: TicketForm): Promise<TicketItem> {
    return http.Post(`${SYSTEM_BASE}/ticket/create`, data)
  },
  update(id: number, data: Record<string, any>): Promise<TicketItem> {
    return http.Put(`${SYSTEM_BASE}/ticket/update/${id}`, data)
  },
  remove(ids: number[]): Promise<void> {
    return http.Delete(`${SYSTEM_BASE}/ticket/delete`, ids)
  },
  batch(data: { ids: number[], status: number, assigned_id?: number }): Promise<void> {
    return http.Put(`${SYSTEM_BASE}/ticket/batch`, data)
  },
  exportTickets(params?: Record<string, any>): Promise<unknown> {
    return http.Post(`${SYSTEM_BASE}/ticket/export`, params)
  },
  getComments(ticketId: number, params?: Record<string, any>) {
    const method = http.Get<PageResult<TicketComment>>(`${SYSTEM_BASE}/ticket/${ticketId}/comments`, params)
    method.config.cacheFor = 0
    return method
  },
  createComment(ticketId: number, data: { content: string }): Promise<TicketComment> {
    return http.Post(`${SYSTEM_BASE}/ticket/${ticketId}/comments`, data)
  },
  /**
   * C 端意见反馈列表（`/system/ticket/mini/feedback`）
   *
   * 与 `/ticket/list` 的区别：那个接口要 `module_system:ticket:query` 权限码，
   * C 端必然 403；mini 接口只要求登录，且后端强制只返回本人提交的反馈。
   */
  getMyFeedback(params?: Record<string, any>) {
    const method = http.Get<PageResult<FeedbackItem>>(`${SYSTEM_BASE}/ticket/mini/feedback`, params)
    method.config.cacheFor = 0
    return method
  },

  /** 提交意见反馈（标题由后端从内容首行生成，C 端不填标题） */
  createFeedback(data: FeedbackForm) {
    return http.Post<FeedbackItem>(`${SYSTEM_BASE}/ticket/mini/feedback`, data)
  },

  /**
   * 工单聚合统计（待处理/处理中/已完成），由后端一次聚合返回，
   * 替代前端 3 次分页请求计数。alova 缓存 30 秒，work/mine 页共享。
   */
  getStats() {
    const method = http.Get<TicketStats>(`${SYSTEM_BASE}/ticket/stats`)
    method.config.cacheFor = 30_000
    return method
  },
}

/** C 端意见反馈提交表单 */
export interface FeedbackForm {
  /** 反馈内容（必填） */
  content: string
  /** 反馈类型：suggestion/bug/optimize/other */
  ticket_type?: string
  /** 图片 URL 列表（JSON 数组字符串，可选） */
  images?: string
}

/** C 端意见反馈条目（后端 mini 接口返回，含处理状态与运营回复） */
export interface FeedbackItem {
  id?: number
  title?: string
  ticket_content?: string
  ticket_type?: string
  status?: number
  reply?: string | null
  images?: string | null
  created_time?: string
}

export interface TicketForm extends BaseFormType {
  title: string
  ticket_content?: string
  summary?: string
  ticket_type: string
  images?: string
  reply?: string
  assigned_id?: number
  status?: number
  description?: string
}

export interface TicketItem extends BaseType {
  title?: string
  ticket_content?: string
  summary?: string
  ticket_type?: string
  status?: string | number
  assigned_id?: number
  assigned_by?: CommonType
  images?: string
  reply?: string
  description?: string
}

export interface TicketComment extends BaseType {
  ticket_id?: number
  user_id?: number
  username?: string
  content?: string
  created_by_name?: string
}

/** 工单聚合统计结果（后端一次性返回） */
export interface TicketStats {
  pending: number
  processing: number
  done: number
}
