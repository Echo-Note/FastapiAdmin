<script setup lang="ts">
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useMarketListPage } from '@/composables/useMarketListPage'

definePage({ name: 'market-task-hall', style: { navigationBarTitleText: '任务大厅', enablePullDownRefresh: true } })

/** 任务大厅列表项（对齐后端 TaskOutSchema：name 为 C 端显示名） */
interface HallTaskItem {
  id?: number
  task_no?: string
  name?: string
  period?: string
  project_id?: number
  template_id?: number
  assign_mode?: string
  status?: string
  published_at?: string | null
  template?: {
    id?: number
    name?: string
    config?: {
      unit?: string
      price?: number | null
    } | null
  } | null
}

/** 分配方式本地映射（direct 定向分派 / open 公开大厅） */
const ASSIGN_MODE_LABEL: Record<string, string> = {
  direct: '定向分派',
  open: '公开大厅',
}

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

const { list, total, loading, loadData, refreshData, loadNext } = useMarketListPage<HallTaskItem>({
  fetcher: p => MarketAPI.getTaskHall({ ...p }) as any,
  onError: () => toast.error(t('common.loadFailed')),
})

/** 单价（取自模板 config.price） */
function priceText(item: HallTaskItem) {
  const price = item.template?.config?.price
  if (price == null)
    return '—'
  return `¥${Number(price).toFixed(2)}`
}

/** 分配方式文案 */
function assignModeText(item: HallTaskItem) {
  return ASSIGN_MODE_LABEL[item.assign_mode ?? ''] ?? item.assign_mode ?? '—'
}

/** 卡片点击统一跳任务详情页（详情页内完成接单） */
function goDetail(item: HallTaskItem) {
  router.push({
    name: 'market-task-detail',
    query: { task_id: String(item.id) },
  })
}

onReachBottom(() => {
  if (!loading.value)
    loadNext()
})
onPullDownRefresh(async () => {
  try {
    await refreshData()
  }
  finally {
    uni.stopPullDownRefresh()
  }
})
onLoad(() => loadData())
</script>

<template>
  <view class="page-wraper">
    <SkeletonPage v-if="loading && list.length === 0" :rows="5" search />
    <template v-else>
      <view class="px-3 pt-3">
        <wd-empty v-if="!loading && list.length === 0" :tip="t('market.emptyTaskHall')" />
        <wd-cell-group v-else border custom-class="rounded-2! overflow-hidden">
          <view
            v-for="item in list"
            :key="item.id"
            class="border-b border-gray-100 bg-white px-4 py-3 last:border-b-0"
            @click="goDetail(item)"
          >
            <view class="flex items-start justify-between gap-2">
              <view class="min-w-0 flex-1">
                <view class="flex items-center gap-2">
                  <wd-text class="wot-text-text-main text-4 font-medium" :text="item.name ?? item.task_no ?? ''" />
                  <wd-tag type="primary" plain :title="assignModeText(item)" />
                </view>
                <view class="mt-1 flex items-center gap-3">
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${item.period ?? '-'}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.unitPrice')} ${priceText(item)}`" />
                </view>
              </view>
              <view class="flex flex-col items-end gap-2">
                <wd-text class="wot-text-error-main text-4 font-semibold" :text="priceText(item)" />
                <wd-icon name="arrow-right" size="18px" custom-class="wot-text-text-secondary" />
              </view>
            </view>
          </view>
        </wd-cell-group>
      </view>
      <wd-loading v-if="loading && list.length > 0" size="20px" class="mx-auto my-2 block" />
      <wd-text v-else-if="total > 0 && list.length >= total" class="wot-text-text-auxiliary my-2 block text-center text-2.5" :text="t('common.noMore')" />
      <wd-gap height="100rpx" safe-area-bottom />
    </template>
  </view>
</template>
