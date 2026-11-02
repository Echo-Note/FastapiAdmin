import { onShow } from '@dcloudio/uni-app'
import { useTabbar } from '@/composables/useTabbar'

/**
 * tab 页 onShow 时同步底部导航高亮。
 *
 * 直接写 useTabbar 的 active 状态，而不是只发事件：从别的 Tab 用 `pushTab` 跳过来时
 * （例如首页点「待接收」跳到工作台），没有任何组件监听事件，底栏会停在原来那个 Tab 上。
 * 通过 getCurrentPages 校验当前路由，避免从子页面返回时误触发。
 */
export function useTabbarActive(route: string, tabKey: string, onActive?: () => void) {
  const { setTabbarItemActive } = useTabbar()

  onShow(() => {
    const pages = getCurrentPages()
    if (pages.length > 0 && pages[pages.length - 1].route === route) {
      setTabbarItemActive(tabKey)
      uni.$emit('updateTabbar', tabKey)
      onActive?.()
    }
  })
}
