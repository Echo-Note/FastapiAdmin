<script setup lang="ts">
import type { AssignmentItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { ASSIGNMENT_STATUS_MAP, taskKindText, statusMeta } from '@/constants'
import { useMarketListPage } from '@/composables/useMarketListPage'

definePage({ name: 'market-my-task', style: { navigationBarTitleText: '我的任务', enablePullDownRefresh: true } })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

/** 顶部状态筛选 Tab：与后端 AssignmentStatus 六档一致（进行中 = SUBMITTING） */
const TAB_OPTIONS = [
  { label: '全部', value: undefined },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'PENDING').label, value: 'PENDING' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'ACCEPTED').label, value: 'ACCEPTED' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'SUBMITTING').label, value: 'SUBMITTING' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'SUBMITTED').label, value: 'SUBMITTED' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'REVIEWED').label, value: 'REVIEWED' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'SETTLED').label, value: 'SETTLED' },
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
  return statusMeta(ASSIGNMENT_STATUS_MAP, status)
}

function amountText(item: AssignmentItem) {
  return `¥${Number(item.task?.unit_price ?? 0).toFixed(2)}`
}

function handleTabChange(e: { index: number }) {
  activeStatus.value = TAB_OPTIONS[e.index]?.value
  toFirst()
}

/** 卡片点击统一跳任务详情页（详情页内完成接收 / 去提交） */
function goDetail(item: AssignmentItem) {
  router.push({
    name: 'market-task-detail',
    query: { assignment_id: String(item.id) },
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
            @click="goDetail(item)"
          >
            <view class="flex items-center justify-between">
              <wd-text class="wot-text-text-main text-4 font-medium" :text="item.task?.task_no ?? ''" />
              <wd-tag :type="statusInfo(item.status).type" plain :title="statusInfo(item.status).label" />
            </view>
            <view class="mt-2 flex items-center gap-3">
              <wd-text class="wot-text-text-auxiliary text-2.5" :text="taskKindText(item.task?.task_kind)" />
              <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${item.task?.period ?? '-'}`" />
              <wd-text v-if="item.task?.exec_time_end" class="wot-text-text-auxiliary text-2.5" :text="`${t('market.deadline')} ${(item.task?.exec_time_end || '').slice(0, 10)}`" />
            </view>
            <view class="mt-3 flex items-center justify-between">
              <view>
                <wd-text class="wot-text-text-auxiliary text-2.5" :text="t('market.amount')" />
                <wd-text class="wot-text-error-main text-4 font-semibold" :text="amountText(item)" />
              </view>
              <wd-icon name="arrow-right" size="18px" custom-class="wot-text-text-secondary" />
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
