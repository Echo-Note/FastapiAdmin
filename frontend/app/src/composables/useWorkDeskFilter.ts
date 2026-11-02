import { ref } from 'vue'

/**
 * 「跳工作台并定位到某个筛选」的跨页传参。
 *
 * 为什么不用路由 query：目标页是 TabBar 页，`uni.switchTab` 不支持带参数
 * （小程序端会直接丢掉 query）。这里用一个模块级的一次性信号：首页写入，
 * 工作台 onShow 读取并清空，跨端行为一致。
 */
export type WorkDeskFilter
  = | 'PENDING'
    | 'ACCEPTED'
    | 'REJECTED'
    | 'RESULT_PENDING'
    | 'RESULT_APPROVED'
    | 'RESULT_REJECTED'

const pendingFilter = ref<WorkDeskFilter | null>(null)

export function useWorkDeskFilter() {
  /** 记录一次待应用的筛选（下一次进入工作台时生效） */
  function request(filter: WorkDeskFilter) {
    pendingFilter.value = filter
  }

  /** 取出并清空，避免下次进入工作台又跳一次 */
  function consume(): WorkDeskFilter | null {
    const value = pendingFilter.value
    pendingFilter.value = null
    return value
  }

  return { request, consume }
}
