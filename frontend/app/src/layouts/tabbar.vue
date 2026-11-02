<script lang="ts" setup>
import { useI18n } from 'vue-i18n'
import { useTaskStats } from '@/composables/useTaskStats'

const router = useRouter()

const route = useRoute()

const { t } = useI18n()

const { activeTabbar, getTabbarItemValue, setTabbarItemActive, tabbarList } = useTabbar()

const { loadTaskStats } = useTaskStats()

const {
  enabled: watermarkEnabled,
  content: watermarkContent,
  color: watermarkColor,
  width: watermarkWidth,
  height: watermarkHeight,
  opacity: watermarkOpacity,
} = useWatermark()

function handleTabbarChange({ value }: { value: string }) {
  setTabbarItemActive(value)
  router.pushTab({ name: value })
}

onMounted(() => {
  // #ifdef APP
  uni.hideTabBar()
  // #endif
  // 待办角标：跟随 Tab 挂载刷新（内部 30s 节流）
  loadTaskStats()
  nextTick(() => {
    if (route.name && route.name !== activeTabbar.value.name) {
      setTabbarItemActive(route.name)
    }
  })
})
</script>

<script lang="ts">
export default {
  options: {
    addGlobalClass: true,
    virtualHost: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <slot />
  <wd-gap
    safe-area-bottom
    height="var(--wot-tabbar-height, 50px)"
    custom-class="tabbar-gap"
  />
  <wd-tabbar
    :model-value="activeTabbar.name" bordered safe-area-inset-bottom fixed
    @change="handleTabbarChange"
  >
    <wd-tabbar-item
      v-for="(item, index) in tabbarList" :key="index" :name="item.name"
      :value="getTabbarItemValue(item.name)" :title="t(item.titleKey)" :icon="item.icon"
    />
  </wd-tabbar>
  <wd-watermark
    v-if="watermarkEnabled"
    :content="watermarkContent"
    :color="watermarkColor"
    :width="watermarkWidth"
    :height="watermarkHeight"
    :opacity="watermarkOpacity"
    layout="grid"
  />
</template>
