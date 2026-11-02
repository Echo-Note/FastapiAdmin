import { ref } from 'vue'
import { MarketAPI } from '@/api/module_market'
import { useTabbar } from '@/composables/useTabbar'

/**
 * C 端待办角标（TabBar 红点数字）
 *
 * 口径：待接收 + 进行中（已接收未提交）+ 被驳回成果 —— 都是「用户现在要动手」的事。
 * TabBar 布局在每次切 Tab 时都会挂载，所以这里做 30 秒节流，避免来回切 Tab 反复打接口。
 */
const CACHE_TTL = 30_000

const todoCount = ref(0)
const rejectedCount = ref(0)
let lastLoadedAt = 0
let inflight: Promise<void> | null = null

export function useTaskStats() {
  const { setTabbarItem } = useTabbar()

  function syncBadge() {
    setTabbarItem('market-my-task', todoCount.value)
  }

  async function loadTaskStats(force = false) {
    if (!force && Date.now() - lastLoadedAt < CACHE_TTL) {
      syncBadge()
      return
    }
    if (inflight)
      return inflight

    inflight = (async () => {
      try {
        const stats = await MarketAPI.getMyTaskStats()
        todoCount.value = (stats.pending ?? 0) + (stats.accepted ?? 0) + (stats.rejected_submissions ?? 0)
        rejectedCount.value = stats.rejected_submissions ?? 0
        lastLoadedAt = Date.now()
        syncBadge()
      }
      catch {
        // 角标是辅助信息：接口失败静默降级，不打扰用户
      }
      finally {
        inflight = null
      }
    })()
    return inflight
  }

  return { todoCount, rejectedCount, loadTaskStats }
}
