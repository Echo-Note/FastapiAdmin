<script setup lang="ts">
import type { TaskItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useMarketListPage } from '@/composables/useMarketListPage'

definePage({ name: 'market-task-hall', style: { navigationBarTitleText: '任务大厅', enablePullDownRefresh: true } })

const { t } = useI18n()
const toast = useToast()

const { list, total, loading, loadData, refreshData, reload, loadNext } = useMarketListPage<TaskItem>({
  fetcher: p => MarketAPI.getTaskHall({ ...p }),
  onError: () => toast.error(t('common.loadFailed')),
})

const claimingId = ref<number>()

function amountText(item: TaskItem) {
  return `¥${Number((item.unit_price ?? 0) * (item.exec_qty ?? 0)).toFixed(2)}`
}

function deadlineText(item: TaskItem) {
  return (item.deadline_at || '').slice(0, 16)
}

function remainText(item: TaskItem) {
  const limit = item.assign_limit
  if (limit == null)
    return ''
  const remain = limit - (item.claimed_count ?? 0)
  return remain > 0 ? `${t('market.remain')} ${remain}` : t('market.claimedFull')
}

async function handleClaim(item: TaskItem) {
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: t('common.title'),
      content: `${t('market.claimConfirm')}\n${item.task_no ?? ''} · ${t('market.amount')} ${amountText(item)}`,
      success: res => resolve(res.confirm),
      fail: () => resolve(false),
    })
  })
  if (!confirmed)
    return
  claimingId.value = item.id
  try {
    await MarketAPI.claimTask(item.id!)
    toast.success(t('market.claimSuccess'))
    reload()
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    claimingId.value = undefined
  }
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
          >
            <view class="flex items-start justify-between gap-2">
              <view class="min-w-0 flex-1">
                <view class="flex items-center gap-2">
                  <wd-text class="wot-text-text-main text-4 font-medium" :text="item.task_no ?? ''" />
                  <wd-tag v-if="item.company?.name" type="primary" plain :title="item.company.name" />
                </view>
                <view class="mt-1 flex items-center gap-3">
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${item.period ?? '-'}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.unitPrice')} ¥${Number(item.unit_price ?? 0).toFixed(2)}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.execQty')} ${item.exec_qty ?? 0}`" />
                </view>
                <view class="mt-1 flex items-center gap-3">
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.deadline')} ${deadlineText(item)}`" />
                  <wd-text v-if="remainText(item)" class="wot-text-text-auxiliary text-2.5" :text="remainText(item)" />
                </view>
              </view>
              <view class="flex flex-col items-end gap-2">
                <wd-text class="wot-text-error-main text-4 font-semibold" :text="amountText(item)" />
                <wd-button
                  type="primary"
                  size="small"
                  :loading="claimingId === item.id"
                  @click="handleClaim(item)"
                >
                  {{ t('market.claim') }}
                </wd-button>
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
