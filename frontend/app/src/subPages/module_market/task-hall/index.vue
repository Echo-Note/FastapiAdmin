<script setup lang="ts">
import type { AssignmentItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useMarketListPage } from '@/composables/useMarketListPage'

definePage({ name: 'market-task-hall', style: { navigationBarTitleText: '任务大厅', enablePullDownRefresh: true } })

const { t } = useI18n()
const toast = useToast()

const { list, total, loading, loadData, refreshData, reload, loadNext } = useMarketListPage<AssignmentItem>({
  fetcher: p => MarketAPI.getTaskHall({ ...p }),
  onError: () => toast.error(t('common.loadFailed')),
})

const acceptingId = ref<number>()

function amountText(item: AssignmentItem) {
  return `¥${Number(item.assign_amount ?? 0).toFixed(2)}`
}

function deadlineText(item: AssignmentItem) {
  return (item.task?.deadline_at || '').slice(0, 16)
}

async function handleAccept(item: AssignmentItem) {
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: t('common.title'),
      content: `${t('market.receiveConfirm')}\n${item.task?.task_no ?? ''} · ${t('market.amount')} ${amountText(item)}`,
      success: res => resolve(res.confirm),
      fail: () => resolve(false),
    })
  })
  if (!confirmed)
    return
  acceptingId.value = item.id
  try {
    await MarketAPI.acceptAssignment(item.id!)
    toast.success(t('market.receiveConfirm'))
    reload()
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    acceptingId.value = undefined
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
                  <wd-text class="wot-text-text-main text-4 font-medium" :text="item.task?.task_no ?? ''" />
                  <wd-tag v-if="item.task?.company?.name" type="primary" plain :title="item.task.company.name" />
                </view>
                <view class="mt-1 flex items-center gap-3">
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${item.task?.period ?? '-'}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.unitPrice')} ¥${Number(item.task?.unit_price ?? 0).toFixed(2)}`" />
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.execQty')} ${item.task?.exec_qty ?? 0}`" />
                </view>
                <view class="mt-1">
                  <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.deadline')} ${deadlineText(item)}`" />
                </view>
              </view>
              <view class="flex flex-col items-end gap-2">
                <wd-text class="wot-text-error-main text-4 font-semibold" :text="amountText(item)" />
                <wd-button
                  type="primary"
                  size="small"
                  :loading="acceptingId === item.id"
                  @click="handleAccept(item)"
                >
                  {{ t('market.accept') }}
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
