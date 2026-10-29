<script setup lang="ts">
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useMarketListPage } from '@/composables/useMarketListPage'
import { ASSIGNMENT_STATUS_MAP, statusMeta } from '@/constants'

definePage({ name: 'market-my-task', style: { navigationBarTitleText: '我的任务', enablePullDownRefresh: true } })

/** 分派单（对齐后端 AssignmentOutSchema，task 为任务摘要 name/period） */
interface MyAssignmentItem {
  id?: number
  task_id?: number
  status?: string
  accepted_at?: string | null
  submitted_at?: string | null
  task?: {
    id?: number
    name?: string
    period?: string
  } | null
}

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

/** 顶部状态筛选 Tab：与后端 AssignmentStatus 六档一致 */
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

const { list, total, loading, loadData, refreshData, loadNext, toFirst } = useMarketListPage<MyAssignmentItem>({
  fetcher: p => MarketAPI.getMyAssignments({
    ...p,
    status: activeStatus.value,
  }) as any,
  onError: () => toast.error(t('common.loadFailed')),
})

function statusInfo(status?: string) {
  return statusMeta(ASSIGNMENT_STATUS_MAP, status)
}

/** 状态语义色 → 卡片左侧色条颜色 */
const STATUS_BAR_COLOR: Record<string, string> = {
  info: 'var(--wot-grey-6)',
  primary: 'var(--wot-primary-6)',
  warning: 'var(--wot-warning-6)',
  success: 'var(--wot-success-6)',
  danger: 'var(--wot-danger-6)',
}
function barColor(status?: string) {
  return STATUS_BAR_COLOR[statusInfo(status).type] ?? 'var(--wot-grey-6)'
}

function handleTabChange(e: { index: number }) {
  activeStatus.value = TAB_OPTIONS[e.index]?.value
  toFirst()
}

/** 卡片点击统一跳任务详情页（详情页内完成接收 / 去提交） */
function goDetail(item: MyAssignmentItem) {
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
        <view
          v-for="item in list"
          :key="item.id"
          class="my-card"
          hover-class="my-card--active"
          @click="goDetail(item)"
        >
          <view class="my-card__bar" :style="{ background: barColor(item.status) }" />
          <view class="my-card__body">
            <view class="flex items-center justify-between gap-2">
              <view class="my-card__title">
                {{ item.task?.name ?? '-' }}
              </view>
              <wd-tag :type="statusInfo(item.status).type" plain :title="statusInfo(item.status).label" />
            </view>
            <view class="mt-2 flex flex-wrap items-center gap-2">
              <view class="my-card__meta">
                {{ t('market.period') }} {{ item.task?.period ?? '-' }}
              </view>
            </view>
          </view>
        </view>
      </view>
      <wd-loading v-if="loading && list.length > 0" size="20px" class="mx-auto my-2 block" />
      <view v-else-if="total > 0 && list.length >= total" class="wot-text-text-auxiliary my-2 text-center text-2.5">
        {{ t('common.noMore') }}
      </view>
      <wd-gap height="100rpx" safe-area-bottom />
    </template>
  </view>
</template>

<style lang="scss" scoped>
.my-card {
  display: flex;
  align-items: stretch;
  gap: 20rpx;
  padding: 28rpx 24rpx 28rpx 20rpx;
  margin-bottom: 20rpx;
  background: var(--wot-bg-filled-oppo, #fff);
  border-radius: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
  transition: transform 0.15s ease;
}

.my-card--active {
  transform: scale(0.98);
}

.my-card__bar {
  width: 8rpx;
  flex-shrink: 0;
  border-radius: 8rpx;
}

.my-card__body {
  flex: 1;
  min-width: 0;
}

.my-card__title {
  overflow: hidden;
  font-size: 32rpx;
  font-weight: 600;
  line-height: 1.35;
  color: var(--wot-text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-card__meta {
  padding: 4rpx 14rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content, #f2f3f5);
  border-radius: 8rpx;
}
</style>
