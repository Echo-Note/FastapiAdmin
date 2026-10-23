<script setup lang="ts">
import type { TaskItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { TASK_KIND_MAP, statusMeta } from '@/constants'
import { useMarketListPage } from '@/composables/useMarketListPage'

definePage({ name: 'market-task-hall', style: { navigationBarTitleText: '任务大厅', enablePullDownRefresh: true } })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

const { list, total, loading, loadData, refreshData, loadNext } = useMarketListPage<TaskItem>({
  fetcher: p => MarketAPI.getTaskHall({ ...p }),
  onError: () => toast.error(t('common.loadFailed')),
})

function amountText(item: TaskItem) {
  return `¥${Number((item.unit_price ?? 0) * (item.exec_qty ?? 0)).toFixed(2)}`
}

function deadlineText(item: TaskItem) {
  return (item.exec_time_end || '').slice(0, 16)
}

function kindInfo(item: TaskItem) {
  return statusMeta(TASK_KIND_MAP, item.task_kind)
}

function remainText(item: TaskItem) {
  // 仅定额任务按总份数限量展示剩余份数；周期性任务不限总份数
  if (item.task_kind !== 'quota')
    return ''
  const limit = item.exec_qty
  if (limit == null)
    return ''
  const remain = limit - (item.claimed_count ?? 0)
  return remain > 0 ? `${t('market.remain')} ${remain}` : t('market.claimedFull')
}

/** 卡片点击统一跳任务详情页（详情页内完成接单） */
function goDetail(item: TaskItem) {
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
                  <wd-text class="wot-text-text-main text-4 font-medium" :text="item.task_no ?? ''" />
                  <wd-tag :type="kindInfo(item).type" plain :title="kindInfo(item).label" />
                </view>
                <view class="mt-1 flex items-center gap-3">
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${item.period ?? '-'}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.unitPrice')} ¥${Number(item.unit_price ?? 0).toFixed(2)}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.execQty')} ${item.exec_qty ?? 0}`" />
                </view>
                <view class="mt-1 flex items-center gap-3">
                  <wd-text v-if="item.exec_time_end" class="wot-text-text-auxiliary text-2.5" :text="`${t('market.deadline')} ${deadlineText(item)}`" />
                  <wd-text v-if="remainText(item)" class="wot-text-warning-main text-2.5" :text="remainText(item)" />
                </view>
              </view>
              <view class="flex flex-col items-end gap-2">
                <wd-text class="wot-text-error-main text-4 font-semibold" :text="amountText(item)" />
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
