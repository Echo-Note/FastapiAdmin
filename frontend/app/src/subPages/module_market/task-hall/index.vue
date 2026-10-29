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

/** 单价（模板 config.price，仅数字） */
function amountText(item: HallTaskItem) {
  const price = item.template?.config?.price
  return price == null ? '' : Number(price).toFixed(2)
}

/** 计价单位 */
function unitText(item: HallTaskItem) {
  return item.template?.config?.unit ?? ''
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
        <view
          v-for="item in list"
          :key="item.id"
          class="hall-card"
          hover-class="hall-card--active"
          @click="goDetail(item)"
        >
          <view class="hall-card__bar" />
          <view class="hall-card__body">
            <view class="hall-card__title">
              {{ item.name ?? item.task_no ?? '' }}
            </view>
            <view class="mt-2 flex flex-wrap items-center gap-2">
              <view class="hall-card__meta">
                {{ t('market.period') }} {{ item.period ?? '-' }}
              </view>
              <view class="hall-card__meta">
                {{ assignModeText(item) }}
              </view>
            </view>
          </view>
          <view class="hall-card__price">
            <view class="hall-card__amount">
              <text class="text-3">
                ¥
              </text>{{ amountText(item) || '—' }}
            </view>
            <view v-if="unitText(item)" class="hall-card__unit">
              / {{ unitText(item) }}
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
.hall-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 28rpx 24rpx 28rpx 20rpx;
  margin-bottom: 20rpx;
  background: var(--wot-bg-filled-oppo, #fff);
  border-radius: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
  transition: transform 0.15s ease;
}

.hall-card--active {
  transform: scale(0.98);
}

.hall-card__bar {
  width: 8rpx;
  height: 72rpx;
  flex-shrink: 0;
  border-radius: 8rpx;
  background: linear-gradient(180deg, var(--wot-primary-6), var(--wot-primary-4));
}

.hall-card__body {
  flex: 1;
  min-width: 0;
}

.hall-card__title {
  overflow: hidden;
  font-size: 32rpx;
  font-weight: 600;
  line-height: 1.35;
  color: var(--wot-text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hall-card__meta {
  padding: 4rpx 14rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content, #f2f3f5);
  border-radius: 8rpx;
}

.hall-card__price {
  flex-shrink: 0;
  text-align: right;
}

.hall-card__amount {
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1.1;
  color: var(--wot-primary-6);
  white-space: nowrap;
}

.hall-card__unit {
  margin-top: 4rpx;
  font-size: 22rpx;
  line-height: 1.4;
  color: var(--wot-text-auxiliary);
}
</style>
