<script setup lang="ts">
import type { AssignmentItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useMarketListPage } from '@/composables/useMarketListPage'

definePage({ name: 'market-my-task', style: { navigationBarTitleText: '我的任务', enablePullDownRefresh: true } })

const { t } = useI18n()
const router = useRouter()
const toast = useToast()

/** 分派状态（C 端视角）→ 展示标签与色型 */
const ASSIGN_STATUS: Record<string, { label: string, type: 'primary' | 'success' | 'warning' | 'danger' | 'info' }> = {
  PENDING: { label: '待接收', type: 'info' },
  ACCEPTED: { label: '已接收', type: 'primary' },
  SUBMITTING: { label: '进行中', type: 'warning' },
  SUBMITTED: { label: '已提交', type: 'warning' },
  REVIEWED: { label: '已审核', type: 'success' },
  SETTLED: { label: '已结算', type: 'success' },
}

/** 顶部状态筛选 Tab */
const TAB_OPTIONS = [
  { label: '全部', value: undefined },
  { label: '待接收', value: 'PENDING' },
  { label: '进行中', value: 'ACCEPTED' },
  { label: '已提交', value: 'SUBMITTED' },
  { label: '已审核', value: 'REVIEWED' },
  { label: '已结算', value: 'SETTLED' },
]
const activeTab = ref(0)
const activeStatus = ref<string | undefined>()

const { list, total, loading, loadData, refreshData, loadNext, toFirst } = useMarketListPage<AssignmentItem>({
  fetcher: p => MarketAPI.getMyAssignments({
    ...p,
    status: activeStatus.value,
  }),
  onError: () => toast.error(t('common.loadFailed')),
})

function statusInfo(status?: string) {
  return ASSIGN_STATUS[status ?? ''] ?? { label: status || '-', type: 'info' as const }
}

function amountText(item: AssignmentItem) {
  return `¥${Number(item.task?.unit_price ?? 0).toFixed(2)}`
}

/** 可提交成果的状态：已接收 / 进行中 / 已提交（驳回可重提）/ 已审核 */
function canSubmit(status?: string) {
  return status === 'ACCEPTED' || status === 'SUBMITTING' || status === 'SUBMITTED' || status === 'REVIEWED'
}

function handleTabChange(e: { index: number }) {
  activeStatus.value = TAB_OPTIONS[e.index]?.value
  toFirst()
}

function goSubmit(item: AssignmentItem) {
  const formSchema = item.task?.task_type?.form_schema ?? []
  router.push({
    name: 'market-submission-form',
    query: {
      assignment_id: String(item.id),
      task_no: item.task?.task_no ?? '',
      form_schema: encodeURIComponent(JSON.stringify(formSchema)),
    },
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
    <wd-tabs v-model="activeTab" line-theme="text" sticky :offset-top="0" @change="handleTabChange">
      <wd-tab v-for="opt in TAB_OPTIONS" :key="opt.label" :title="opt.label" />
    </wd-tabs>

    <SkeletonPage v-if="loading && list.length === 0" :rows="5" search />
    <template v-else>
      <view class="px-3 pt-3">
        <wd-empty v-if="!loading && list.length === 0" :tip="t('market.emptyMyTask')" />
        <view v-else class="flex flex-col gap-3">
          <view
            v-for="item in list"
            :key="item.id"
            class="rounded-2 bg-white p-4 shadow-sm"
          >
            <view class="flex items-center justify-between">
              <wd-text class="wot-text-text-main text-4 font-medium" :text="item.task?.task_no ?? ''" />
              <wd-tag :type="statusInfo(item.status).type" plain :title="statusInfo(item.status).label" />
            </view>
            <view class="mt-2 flex items-center gap-3">
              <wd-text class="wot-text-text-auxiliary text-2.5" :text="item.task?.task_kind === 'quota' ? '定额' : '周期性'" />
              <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${item.task?.period ?? '-'}`" />
              <wd-text v-if="item.task?.exec_time_end" class="wot-text-text-auxiliary text-2.5" :text="`${t('market.deadline')} ${(item.task?.exec_time_end || '').slice(0, 10)}`" />
            </view>
            <view class="mt-3 flex items-center justify-between">
              <view>
                <wd-text class="wot-text-text-auxiliary text-2.5" :text="t('market.amount')" />
                <wd-text class="wot-text-error-main text-4 font-semibold" :text="amountText(item)" />
              </view>
              <wd-button v-if="canSubmit(item.status)" type="primary" size="small" @click="goSubmit(item)">
                {{ t('market.submitResult') }}
              </wd-button>
            </view>
          </view>
        </view>
      </view>
      <wd-loading v-if="loading && list.length > 0" size="20px" class="mx-auto my-2 block" />
      <wd-text v-else-if="total > 0 && list.length >= total" class="wot-text-text-auxiliary my-2 block text-center text-2.5" :text="t('common.noMore')" />
      <wd-gap height="100rpx" safe-area-bottom />
    </template>
  </view>
</template>
