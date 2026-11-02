import type { NavEntry } from '@/constants/nav'
import { computed, ref } from 'vue'
import { TABBAR_ITEMS } from '@/constants/nav'

export interface TabbarItem {
  name: string
  value?: number
  active: boolean
  titleKey: string
  icon: string
}

/**
 * TabBar 条目直接由 `constants/nav.ts` 的 TABBAR_ITEMS 派生，
 * 避免「导航配置」与「Tab 渲染」两处各写一份而漂移。
 */
function createTabbarItems(): TabbarItem[] {
  return TABBAR_ITEMS.map((entry: NavEntry, index: number) => ({
    name: entry.name,
    active: index === 0,
    titleKey: entry.titleKey,
    icon: entry.icon,
  }))
}

const tabbarItems = ref<TabbarItem[]>(createTabbarItems())

export function useTabbar() {
  const tabbarList = computed(() => tabbarItems.value)

  const activeTabbar = computed(() => {
    const item = tabbarItems.value.find(item => item.active)
    return item || tabbarItems.value[0]
  })

  const getTabbarItemValue = (name: string) => {
    const item = tabbarItems.value.find(item => item.name === name)
    return item?.value
  }

  const setTabbarItem = (name: string, value: number) => {
    const tabbarItem = tabbarItems.value.find(item => item.name === name)
    if (tabbarItem) {
      tabbarItem.value = value
    }
  }

  const setTabbarItemActive = (name: string) => {
    tabbarItems.value.forEach((item) => {
      if (item.name === name) {
        item.active = true
      }
      else {
        item.active = false
      }
    })
  }

  return {
    tabbarList,
    activeTabbar,
    getTabbarItemValue,
    setTabbarItem,
    setTabbarItemActive,
  }
}
