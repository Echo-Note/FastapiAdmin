import type { NavEntry, NavGroup, NavVisibility } from '@/constants/nav'
import { computed } from 'vue'
import { useUserStore } from '@/store/userStore'

/**
 * 入口可见性判定（唯一实现）。
 *
 * 口径：`superuser` 看全部；普通 C 端用户只看 `all`。
 * 只用于**导航入口**，不作为鉴权：越权请求由后端 RBAC 与本人数据过滤拦截。
 */
export function useAccess() {
  const userStore = useUserStore()

  const isSuperuser = computed(() => !!userStore.userInfo?.is_superuser)

  function canSee(visibleTo: NavVisibility = 'all'): boolean {
    return visibleTo === 'all' || isSuperuser.value
  }

  function visibleEntries(entries: NavEntry[]): NavEntry[] {
    return entries.filter(entry => canSee(entry.visibleTo))
  }

  /** 过滤分组：条目为空的分组整组隐藏（避免出现只有标题的空分组） */
  function visibleGroups(groups: NavGroup[]): NavGroup[] {
    return groups
      .map(group => ({ ...group, items: visibleEntries(group.items) }))
      .filter(group => group.items.length > 0)
  }

  return { isSuperuser, canSee, visibleEntries, visibleGroups }
}
