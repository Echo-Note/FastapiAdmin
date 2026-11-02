<script setup lang="ts">
import type { AssignmentItem, MyTaskStats, PayoutSummary } from '@/api/module_market'
import type { NoticeItem } from '@/api/module_system/notice'
import { onLoad, onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { NoticeAPI } from '@/api/module_system/notice'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { taskDisplayName } from '@/constants'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'home',
  type: 'home',
  layout: 'tabbar',
  style: { navigationBarTitleText: '首页', enablePullDownRefresh: true },
})
useI18nNavTitle('home.title')

const { t, locale } = useI18n()
const router = useRouter()

useShare(() => ({ title: t('home.shareTitle'), path: '/pages/home/index' }))
useTabbarActive('pages/home/index', 'home')

const stats = ref<MyTaskStats>({})
const payout = ref<PayoutSummary | null>(null)
/** 待办预览：按截止日期最近的几条 */
const upcoming = ref<AssignmentItem[]>([])
const notice = ref<NoticeItem | null>(null)
const loading = ref(true)
const failed = ref(false)

/** 首页所有的「今天要做的事」都来自这一个数字，与 TabBar 角标同口径 */
const todoCount = computed(
  () => (stats.value.pending ?? 0) + (stats.value.accepted ?? 0) + (stats.value.rejected_submissions ?? 0),
)

const hasWeekWork = computed(() => todoCount.value > 0)

/** 收益：本月应发 / 额度进度；额度为 0 时不画进度条，避免除零与假仪表盘 */
const payable = computed(() => Number(payout.value?.payable ?? 0))
const payoutLimit = computed(() => Number(payout.value?.payout_limit ?? 0))
const allowance = computed(() => Number(payout.value?.allowance_balance ?? 0))
const quotaPercent = computed(() =>
  payoutLimit.value > 0 ? Math.min(100, Math.round((payable.value / payoutLimit.value) * 100)) : 0,
)

/** 最晚截止：只取预览里的最小值，不额外请求 */
const latestDeadline = computed(() => {
  const dates = upcoming.value.map(item => item.task?.period).filter(Boolean) as string[]
  if (!dates.length)
    return ''
  return dates.sort()[0]!.slice(0, 10)
})

function currentPeriod() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

const WEEK_ZH = ['日', '一', '二', '三', '四', '五', '六']
const WEEK_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** 今天几号、周几：首页的「今日」锚点，日期是本地化信息而不是文案 */
const dateText = computed(() => {
  const now = new Date()
  const m = now.getMonth() + 1
  const d = now.getDate()
  return locale.value.startsWith('zh')
    ? `${m} 月 ${d} 日 周${WEEK_ZH[now.getDay()]}`
    : `${WEEK_EN[now.getDay()]}, ${m}/${d}`
})

function amountText(item: AssignmentItem) {
  const price = item.task?.item?.config?.price ?? item.task?.template?.config?.price
  return price == null ? t('taskDetail.priceTbd') : `¥${CommonUtil.formatMoney(price)}`
}

function daysLeft(period?: string) {
  if (!period)
    return null
  const end = new Date(String(period).replace(/-/g, '/')).getTime()
  if (Number.isNaN(end))
    return null
  return Math.ceil((end - Date.now()) / 86_400_000)
}

function deadlineChip(period?: string) {
  const days = daysLeft(period)
  if (days == null)
    return { text: '', urgent: false }
  if (days < 0)
    return { text: t('hall.deadlinePassed'), urgent: true }
  if (days === 0)
    return { text: t('hall.deadlineToday'), urgent: true }
  return { text: t('hall.deadlineDays', { days }), urgent: days <= 3 }
}

async function loadAll() {
  loading.value = true
  failed.value = false
  const [statsRes, payoutRes, upcomingRes, noticeRes] = await Promise.allSettled([
    MarketAPI.getMyTaskStats(),
    MarketAPI.getMyPayout(currentPeriod()),
    MarketAPI.getMyAssignments({ page_no: 1, page_size: 3, status: 'ACCEPTED' }),
    NoticeAPI.getAvailable(1),
  ])

  if (statsRes.status === 'fulfilled')
    stats.value = statsRes.value
  else
    failed.value = true

  if (payoutRes.status === 'fulfilled')
    payout.value = payoutRes.value

  if (upcomingRes.status === 'fulfilled') {
    upcoming.value = (upcomingRes.value.items ?? [])
      .filter(item => item.task?.period)
      .sort((a, b) => String(a.task?.period).localeCompare(String(b.task?.period)))
      .slice(0, 2)
  }

  if (noticeRes.status === 'fulfilled')
    notice.value = noticeRes.value?.[0] ?? null

  loading.value = false
  uni.stopPullDownRefresh()
}

function goto(name: string) {
  router.push({ name })
}

function goTask(item: AssignmentItem) {
  if (item.status === 'PENDING') {
    router.pushTab({ name: 'market-work-desk' })
    return
  }
  if (item.id)
    router.push({ name: 'market-submission-form', query: { assignment_id: String(item.id) } })
}

onLoad(() => {
  loadAll()
})

/** 回到首页时刷新：接单/提交后数字要立刻对得上 */
let shownOnce = false
onShow(() => {
  if (!shownOnce) {
    shownOnce = true
    return
  }
  loadAll()
})

onPullDownRefresh(() => {
  loadAll()
})
</script>

<template>
  <view class="tabbar-wraper">
    <SkeletonPage v-if="loading" :rows="4" class="mt-3" />

    <template v-else>
      <!-- 今日工作单：首页唯一带装饰的元素，其余一律平铺 -->
      <view class="slip mx-3 mt-3">
        <view class="slip__bar" />
        <view class="slip__body">
          <view class="slip__date">
            {{ dateText }}
          </view>
          <view class="slip__say">
            <template v-if="hasWeekWork">
              {{ t('home.todoHeadPrefix') }} <text class="slip__em">
                {{ todoCount }}
              </text> {{ t('home.todoHeadSuffix') }}
            </template>
            <template v-else>
              {{ t('home.todoEmpty') }}
            </template>
          </view>
          <view class="slip__grid">
            <view class="slip__cell">
              <text class="slip__num">
                {{ stats.pending ?? 0 }}
              </text>
              <text class="slip__label">
                {{ t('home.pending') }}
              </text>
            </view>
            <view class="slip__cell">
              <text class="slip__num">
                {{ stats.accepted ?? 0 }}
              </text>
              <text class="slip__label">
                {{ t('home.active') }}
              </text>
            </view>
            <view class="slip__cell">
              <text class="slip__num slip__num--alert">
                {{ stats.rejected_submissions ?? 0 }}
              </text>
              <text class="slip__label">
                {{ t('home.rejected') }}
              </text>
            </view>
          </view>
          <view v-if="latestDeadline" class="slip__deadline">
            <text>{{ t('home.latestDeadline') }}</text>
            <text class="slip__deadline-date">
              {{ latestDeadline }}
            </text>
          </view>
        </view>
      </view>

      <!-- 收益 -->
      <view class="card mx-3 mt-3" hover-class="card--pressed" @click="goto('market-my-earnings')">
        <view class="flex items-end justify-between">
          <view>
            <view class="card__label">
              {{ t('mine.monthPayable') }}
            </view>
            <view class="card__money">
              ¥{{ CommonUtil.formatMoney(payable, 2) }}
            </view>
          </view>
          <text class="card__link">
            {{ t('mine.earningsDetail') }} ›
          </text>
        </view>
        <view class="quota">
          <view class="quota__track">
            <view class="quota__fill" :style="{ width: `${quotaPercent}%` }" />
          </view>
          <view class="quota__cap">
            <text>{{ t('mine.payoutLimit') }} ¥{{ CommonUtil.formatMoney(payoutLimit, 2) }}</text>
            <text>{{ t('mine.allowanceBalance') }} ¥{{ CommonUtil.formatMoney(allowance, 2) }}</text>
          </view>
        </view>
      </view>

      <!-- 接下来要交的 -->
      <view class="sect mx-3 mt-4">
        <text class="sect__title">
          {{ t('home.nextTitle') }}
        </text>
        <text class="sect__more" @click="router.pushTab({ name: 'market-work-desk' })">
          {{ t('home.viewAll') }} ›
        </text>
      </view>

      <view v-if="upcoming.length === 0" class="mx-3 mt-1">
        <view class="card empty" hover-class="card--pressed" @click="router.pushTab({ name: 'market-task-hall' })">
          <text class="empty__text">
            {{ t('home.emptyTasks') }}
          </text>
          <text class="empty__cta">
            {{ t('home.goHall') }} ›
          </text>
        </view>
      </view>

      <view v-else class="mx-3 mt-1 flex flex-col gap-2">
        <view
          v-for="item in upcoming"
          :key="item.id"
          class="queue"
          hover-class="queue--pressed"
          @click="goTask(item)"
        >
          <view class="queue__mark" :class="{ 'queue__mark--urgent': deadlineChip(item.task?.period).urgent }" />
          <view class="min-w-0 flex-1">
            <view class="queue__name">
              {{ taskDisplayName(item.task) }}
            </view>
            <view class="queue__meta">
              <text>{{ item.task?.task_no }}</text>
              <text class="queue__dot">
                ·
              </text>
              <text>{{ amountText(item) }}</text>
            </view>
          </view>
          <view class="queue__side">
            <text class="queue__chip" :class="{ 'queue__chip--urgent': deadlineChip(item.task?.period).urgent }">
              {{ deadlineChip(item.task?.period).text }}
            </text>
            <text class="queue__action">
              {{ t('myTask.submit') }}
            </text>
          </view>
        </view>
      </view>

      <!-- 公告 -->
      <view v-if="notice" class="card row mx-3 mt-3" hover-class="card--pressed" @click="goto('work-notices')">
        <wd-icon name="notification" size="16px" color="var(--wot-primary-6)" />
        <text class="notice">
          {{ notice.notice_title }}
        </text>
        <text class="card__link">
          ›
        </text>
      </view>

      <!-- 数据没取到时的兜底：不给假数字，明确可重试 -->
      <view v-if="failed" class="mx-3 mt-3">
        <view class="card empty" hover-class="card--pressed" @click="loadAll">
          <text class="empty__text">
            {{ t('common.loadFailed') }}
          </text>
          <text class="empty__cta">
            {{ t('common.retry') }} ›
          </text>
        </view>
      </view>

      <wd-gap height="40rpx" />
    </template>
  </view>
</template>

<style lang="scss" scoped>
/* 今日工作单：唯一允许有装饰的元素（顶部色条 + 虚线分隔） */
.slip {
  border-radius: 20rpx;
  overflow: hidden;
  background: var(--wot-filled-oppo);

  &__bar {
    height: 6rpx;
    background: var(--wot-primary-6);
  }

  &__body {
    padding: 26rpx 28rpx 22rpx;
  }

  &__date {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
    letter-spacing: 0.5rpx;
  }

  &__say {
    margin-top: 8rpx;
    font-size: 34rpx;
    font-weight: 600;
    line-height: 1.35;
    color: var(--wot-text-main);
  }

  &__em {
    color: var(--wot-primary-6);
  }

  &__grid {
    display: flex;
    margin-top: 24rpx;
    padding-top: 20rpx;
    border-top: 1rpx dashed var(--wot-border-light);
  }

  &__cell {
    flex: 1;
  }

  &__num {
    display: block;
    font-size: 44rpx;
    font-weight: 700;
    line-height: 1.1;
    color: var(--wot-text-main);
    font-variant-numeric: tabular-nums;

    &--alert {
      color: var(--wot-danger-main);
    }
  }

  &__label {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__deadline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 20rpx;
    font-size: 22rpx;
    color: var(--wot-text-secondary);
  }

  &__deadline-date {
    font-size: 24rpx;
    font-weight: 600;
    color: var(--wot-text-main);
    font-variant-numeric: tabular-nums;
  }
}

.card {
  padding: 26rpx 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &--pressed {
    opacity: 0.72;
  }

  &__label {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__money {
    margin-top: 4rpx;
    font-size: 48rpx;
    font-weight: 700;
    line-height: 1.1;
    color: var(--wot-danger-main);
    font-variant-numeric: tabular-nums;
  }

  &__link {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }
}

/* 额度进度：用进度条表达「离发满还有多远」，比再放一个大数字更可读 */
.quota {
  margin-top: 20rpx;

  &__track {
    height: 8rpx;
    border-radius: 9999rpx;
    background: var(--wot-filled-content);
    overflow: hidden;
  }

  &__fill {
    height: 100%;
    border-radius: 9999rpx;
    background: var(--wot-primary-6);
  }

  &__cap {
    display: flex;
    justify-content: space-between;
    margin-top: 10rpx;
    font-size: 20rpx;
    color: var(--wot-text-auxiliary);
  }
}

.sect {
  display: flex;
  align-items: baseline;
  justify-content: space-between;

  &__title {
    font-size: 26rpx;
    font-weight: 600;
    color: var(--wot-text-main);
  }

  &__more {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }
}

/* 待办队列行：左侧状态条 + 名称 + 元信息，右侧截止与动作 */
.queue {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 22rpx 24rpx;
  border-radius: 16rpx;
  background: var(--wot-filled-oppo);

  &--pressed {
    opacity: 0.72;
  }

  &__mark {
    width: 6rpx;
    align-self: stretch;
    border-radius: 9999rpx;
    background: var(--wot-primary-6);

    &--urgent {
      background: var(--wot-warning-main);
    }
  }

  &__name {
    font-size: 28rpx;
    font-weight: 600;
    line-height: 1.35;
    color: var(--wot-text-main);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 6rpx;
    margin-top: 6rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__dot {
    color: var(--wot-text-disabled);
  }

  &__side {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8rpx;
    flex-shrink: 0;
  }

  &__chip {
    padding: 2rpx 12rpx;
    border-radius: 8rpx;
    font-size: 20rpx;
    color: var(--wot-text-secondary);
    background: var(--wot-filled-content);

    &--urgent {
      color: var(--wot-warning-main);
      background: var(--wot-warning-surface);
    }
  }

  &__action {
    font-size: 22rpx;
    font-weight: 600;
    color: var(--wot-primary-6);
  }
}

.empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;

  &__text {
    font-size: 24rpx;
    color: var(--wot-text-secondary);
  }

  &__cta {
    font-size: 24rpx;
    font-weight: 600;
    color: var(--wot-primary-6);
  }
}

.notice {
  flex: 1;
  min-width: 0;
  font-size: 24rpx;
  color: var(--wot-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
</style>
