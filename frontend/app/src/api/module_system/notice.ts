import type { BatchSetStatus } from './user'
import { http } from '@/http'

const SYSTEM_BASE = '/system'

/**
 * 公告管理 API
 * 与 web 端 module_system/notice.ts 对齐（完整字段定义）
 */
export const NoticeAPI = {
  getPage(params?: Record<string, any>) {
    return http.Get<PageResult<NoticeItem>>(`${SYSTEM_BASE}/notice/list`, params)
  },
  getDetail(id: number) {
    const method = http.Get<NoticeItem>(`${SYSTEM_BASE}/notice/detail/${id}`)
    method.config.cacheFor = 0
    return method
  },
  create(data: NoticeForm): Promise<NoticeItem> {
    return http.Post(`${SYSTEM_BASE}/notice/create`, data)
  },
  update(id: number, data: NoticeForm): Promise<NoticeItem> {
    return http.Put(`${SYSTEM_BASE}/notice/update/${id}`, data)
  },
  remove(ids: number[]): Promise<void> {
    return http.Delete(`${SYSTEM_BASE}/notice/delete`, ids)
  },
  batchStatus(data: BatchSetStatus): Promise<void> {
    return http.Patch(`${SYSTEM_BASE}/notice/status/batch`, data)
  },
  /**
   * 已发布公告（`status=1`，倒序）
   *
   * 须知：这是**公开内容**接口，后端已绕过数据权限（否则非超管因为 `created_id` 过滤会一条都看不到）。
   * `limit` 缺省 10；C 端公告页传 50，避免公告多了只看得到最旧的几条。
   */
  getAvailable(limit?: number): Promise<NoticeItem[]> {
    const params: Record<string, any> = {}
    if (limit)
      params.limit = limit
    return http.Get(`${SYSTEM_BASE}/notice/available`, params)
  },
}

export interface NoticeForm extends BaseFormType {
  notice_title?: string
  notice_type?: string
  notice_content?: string
  status?: number
  description?: string
}

export interface NoticeItem extends BaseType, NoticeForm {}
