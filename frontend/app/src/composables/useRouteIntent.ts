import { ref } from 'vue'

/**
 * 跨页传参的「一次性路由意图」。
 *
 * 为什么不用路由 query：`router.push({ query })` 在本项目的运行时（H5 hash / 小程序）里
 * 不会把参数带进目标页的 `onLoad(query)` —— 已实际踩过三次（任务详情 id 丢失、
 * 提交成果 assignment_id 变 NaN、公告详情拿不到 id）。
 *
 * 用法：跳转前 `set(name, params)`，目标页 `onLoad` 里 `take(name)`；
 * 读一次即清空，不会污染下次进入。URL 上的 query 仍然作为兜底（分享 / 深链）。
 */
interface RouteIntent {
  name: string
  params: Record<string, string>
}

const intent = ref<RouteIntent | null>(null)

export function useRouteIntent() {
  /** 记录一次跳转意图（只在紧接着的那次导航后有效） */
  function set(name: string, params: Record<string, string>) {
    intent.value = { name, params }
  }

  /** 目标页取用：名字匹配才返回并清空，避免串页 */
  function take(name: string): Record<string, string> | null {
    if (intent.value?.name !== name)
      return null
    const params = intent.value.params
    intent.value = null
    return params
  }

  return { set, take }
}
