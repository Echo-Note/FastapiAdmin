import { ref } from 'vue'

/**
 * 「跳到公告列表并直接打开某条详情」的一次性信号。
 *
 * 不用路由 query：部分运行环境（小程序 / H5 的 replace 语义）下 query 可能丢失。
 * 首页/任务大厅写信号，公告页 onLoad 读取并清空，行为与工作台的筛选信号一致。
 */
const pendingOpenId = ref<number | null>(null)

export function useNoticeOpen() {
  function requestOpen(id?: number | null) {
    if (id != null)
      pendingOpenId.value = id
  }

  function consumeOpen(): number | null {
    const value = pendingOpenId.value
    pendingOpenId.value = null
    return value
  }

  return { requestOpen, consumeOpen }
}
