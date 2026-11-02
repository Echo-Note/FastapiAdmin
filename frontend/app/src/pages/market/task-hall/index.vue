<script setup lang="ts">
import type { TaskItem } from '@/api/module_market'
import type { NoticeItem } from '@/api/module_system/notice'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { NoticeAPI } from '@/api/module_system/notice'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'market-task-hall',
  type: 'home',
  layout: 'tabbar',
  style: { navigationBarTitleText: '任务大厅', enablePullDownRefresh: true },
})
useI18nNavTitle('hall.title')

const { t } = useI18n()
const router = useRouter()

useShare(() => ({ title: t('hall.shareTitle'), path: '/pages/market/task-hall/index' }))
useTabbarActive('pages/market/task-hall/index', 'market-task-hall')

/** 大厅容量：后端 page_size 上限 100，公开任务量级很小（PRD：量不大），一次取全再本地筛选 */
const HALL_PAGE_SIZE = 100

const tasks = ref<TaskItem[]>([])
const total = ref(0)
const loading = ref(false)
const failed = ref(false)
const keyword = ref('')
const kindFilter = ref<'' | 'periodic' | 'quota'>('')
const notice = ref<NoticeItem | null>(null)

const KIND_FILTERS = computed(() => [
  { value: '' as const, label: t('hall.filterAll') },
  { value: 'periodic' as const, label: t('hall.filterPeriodic') },
  { value: 'quota' as const, label: t('hall.filterQuota') },
])

/** 本地筛选：任务名称命中优先，其次任务编号；分类为硬过滤 */
const filteredTasks = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return tasks.value.filter((item) => {
    if (kindFilter.value && item.task_kind !== kindFilter.value)
      return false
    if (!kw)
      return true
    return taskName(item).toLowerCase().includes(kw) || (item.task_no ?? '').toLowerCase().includes(kw)
  })
})

/** 有任务但被筛选条件筛空 —— 空态要说清是「没任务」还是「没搜到」 */
const isFilteredOut = computed(() => tasks.value.length > 0 && filteredTasks.value.length === 0)

function taskName(item: TaskItem) {
  return item.task_type?.name || item.task_no || t('hall.unnamed')
}

function priceText(item: TaskItem) {
  return `¥${CommonUtil.formatMoney(item.unit_price)}`
}

function unitText(item: TaskItem) {
  const unit = item.task_type?.unit
  return unit ? `/${unit}` : ''
}

function periodText(item: TaskItem) {
  return item.period ? `${t('market.period')} ${item.period}` : ''
}

/** 定额任务按剩余份数展示；周期性任务不限总份数，不展示 */
function remainText(item: TaskItem) {
  if (item.task_kind !== 'quota' || item.exec_qty == null)
    return ''
  const remain = item.exec_qty - (item.claimed_count ?? 0)
  return remain > 0 ? t('hall.remain', { count: remain }) : t('market.claimedFull')
}

/** 截止语义：定额任务有结束时间；周期性任务只有周期，不假造倒计时 */
function deadlineInfo(item: TaskItem) {
  if (!item.exec_time_end)
    return null
  const end = new Date(item.exec_time_end.replace(/-/g, '/')).getTime()
  if (Number.isNaN(end))
    return null
  const days = Math.ceil((end - Date.now()) / 86_400_000)
  if (days < 0)
    return { days, text: t('hall.deadlinePassed'), urgent: true }
  if (days === 0)
    return { days, text: t('hall.deadlineToday'), urgent: true }
  return { days, text: t('hall.deadlineDays', { days }), urgent: days <= 3 }
}

async function loadNotices() {
  try {
    const list = await NoticeAPI.getAvailable(1)
    notice.value = list?.[0] ?? null
  }
  catch {
    // 公告失败不影响接单主流程，静默降级
    notice.value = null
  }
}

async function loadTasks() {
  loading.value = true
  failed.value = false
  try {
    const res = await MarketAPI.getTaskHall({ page_no: 1, page_size: HALL_PAGE_SIZE })
    tasks.value = res.items ?? []
    total.value = res.total ?? 0
  }
  catch {
    failed.value = true
  }
  finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

function goDetail(item: TaskItem) {
  if (!item.id)
    return
  router.push({ name: 'market-task-detail', query: { id: String(item.id) } })
}

function goNotices() {
  router.push({ name: 'work-notices' })
}

onLoad(() => {
  loadTasks()
  loadNotices()
})

onPullDownRefresh(() => {
  loadTasks()
  loadNotices()
})
</script>

<template>
  <view class="tabbar-wraper">
    <!-- 平台公告：C 端唯一的运营触达渠道，只展示最新一条 -->
    <view v-if="notice" class="mx-3 mt-3" @click="goNotices">
      <wd-notice-bar
        :text="notice.notice_title || ''"
        prefix="notification"
        type="info"
        closable
        custom-class="hall-notice"
      />
    </view>

    <!-- 搜索 + 分类筛选 -->
    <view class="mx-3 mt-3">
      <wd-search
        v-model="keyword"
        :placeholder="t('hall.searchPlaceholder')"
        variant="light"
        hide-cancel
      />
      <view class="mt-2 flex items-center gap-2">
        <view
          v-for="item in KIND_FILTERS"
          :key="item.value"
          class="hall-filter"
          :class="{ 'hall-filter--active': kindFilter === item.value }"
          @click="kindFilter = item.value"
        >
          {{ item.label }}
        </view>
        <text class="wot-text-text-auxiliary ml-auto text-2.5">
          {{ t('hall.count', { count: filteredTasks.length }) }}
        </text>
      </view>
    </view>

    <SkeletonPage v-if="loading && tasks.length === 0" :rows="4" class="mt-3" />

    <!-- 失败态：明确说清是「加载失败」并给重试，不能退化成「暂无任务」 -->
    <view v-else-if="failed" class="mx-3 mt-8 flex flex-col items-center gap-3">
      <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
      <wd-text :text="t('common.loadFailed')" class="wot-text-text-secondary text-3" />
      <wd-button size="small" round @click="loadTasks">
        {{ t('common.retry') }}
      </wd-button>
    </view>

    <view v-else-if="tasks.length === 0" class="mx-3 mt-8">
      <wd-empty :tip="t('market.emptyTaskHall')" />
    </view>

    <view v-else-if="isFilteredOut" class="mx-3 mt-8">
      <wd-empty :tip="t('hall.emptySearch')" />
    </view>

    <view v-else class="mx-3 mt-3 flex flex-col gap-3">
      <view
        v-for="item in filteredTasks"
        :key="item.id"
        class="task-card"
        hover-class="task-card--pressed"
        @click="goDetail(item)"
      >
        <view class="flex items-start gap-3">
          <view class="min-w-0 flex-1">
            <view class="task-card__name">
              {{ taskName(item) }}
            </view>
            <view class="task-card__no">
              {{ item.task_no }}
            </view>
          </view>
          <view class="shrink-0 text-right">
            <view class="task-card__price">
              {{ priceText(item) }}
            </view>
            <view v-if="unitText(item)" class="task-card__unit">
              {{ unitText(item) }}
            </view>
          </view>
        </view>

        <view class="task-card__footer">
          <view class="min-w-0 flex items-center gap-1.5">
            <text
              v-if="deadlineInfo(item)"
              class="hall-chip"
              :class="deadlineInfo(item)?.urgent ? 'hall-chip--urgent' : 'hall-chip--calm'"
            >
              {{ deadlineInfo(item)?.text }}
            </text>
            <text v-if="remainText(item)" class="hall-chip hall-chip--calm">
              {{ remainText(item) }}
            </text>
            <text v-if="!deadlineInfo(item) && periodText(item)" class="task-card__period">
              {{ periodText(item) }}
            </text>
          </view>
          <text class="task-card__link">
            {{ t('hall.view') }} ›
          </text>
        </view>
      </view>
    </view>

    <view v-if="!loading && !failed && total > tasks.length" class="mx-3 my-3">
      <wd-text
        :text="t('hall.truncated', { count: tasks.length })"
        class="wot-text-text-auxiliary block text-center text-2.5"
      />
    </view>

    <wd-gap height="40rpx" />
  </view>
</template>

<style lang="scss" scoped>
/* 列表卡片：单一表面 + 内部细线分层，不用描边卡片堆叠（避免模板化观感） */
.task-card {
  padding: 28rpx 28rpx 20rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.72;
  }

  &__name {
    font-size: 32rpx;
    font-weight: 600;
    line-height: 1.35;
    color: var(--wot-text-main);
    /* 长任务名最多两行，避免把金额挤到卡片外 */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__no {
    margin-top: 6rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
    letter-spacing: 0.5rpx;
  }

  &__price {
    font-size: 38rpx;
    font-weight: 700;
    line-height: 1.2;
    color: var(--wot-danger-main);
    /* 金额按位数对齐，多个任务纵向比较时不会跳动 */
    font-variant-numeric: tabular-nums;
  }

  &__unit {
    margin-top: 4rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16rpx;
    margin-top: 20rpx;
    padding-top: 16rpx;
    border-top: 1rpx solid var(--wot-border-light);
  }

  &__period {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__link {
    flex-shrink: 0;
    font-size: 24rpx;
    font-weight: 500;
    color: var(--wot-primary-6);
  }
}

/* 分类筛选（触控高度 ≥ 44px 的一半以上由 padding 保证，视觉更紧凑但点击区间足够） */
.hall-filter {
  padding: 10rpx 26rpx;
  border-radius: 9999rpx;
  font-size: 24rpx;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-oppo);
  border: 1rpx solid var(--wot-border-light);

  &--active {
    color: #fff;
    font-weight: 600;
    background: var(--wot-primary-6);
    border-color: var(--wot-primary-6);
  }
}

/* 状态标签：截止/剩余用同一套形状，靠颜色区分紧急度（不只靠颜色：文案本身写明「剩 2 天」） */
.hall-chip {
  padding: 4rpx 14rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;

  &--urgent {
    color: var(--wot-warning-main);
    background: var(--wot-warning-surface);
  }

  &--calm {
    color: var(--wot-success-main);
    background: var(--wot-success-surface);
  }
}
</style>
