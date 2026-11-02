<script setup lang="ts">
import type { AssignmentItem, MyTaskStats, MyWeekProgress, PayoutSummary, TaskItem } from '@/api/module_market'
import type { NoticeItem } from '@/api/module_system/notice'
import type { WorkDeskFilter } from '@/composables/useWorkDeskFilter'
import { onLoad, onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { NoticeAPI } from '@/api/module_system/notice'
import { useNoticeDismiss } from '@/composables/useNoticeDismiss'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { useWorkDeskFilter } from '@/composables/useWorkDeskFilter'
import { taskDisplayName } from '@/constants'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'home',
  type: 'home',
  layout: 'tabbar',
  style: {
    navigationStyle: 'custom',
    navigationBarTitleText: '首页',
    enablePullDownRefresh: true,
  },
})

const { t, locale } = useI18n()
const router = useRouter()
const workDeskFilter = useWorkDeskFilter()
const { isDismissed, dismiss } = useNoticeDismiss()

useShare(() => ({ title: t('home.shareTitle'), path: '/pages/home/index' }))
useTabbarActive('pages/home/index', 'home')

const stats = ref<MyTaskStats>({})
const payout = ref<PayoutSummary | null>(null)
/** 待办预览：按截止日期最近的几条 */
const upcoming = ref<AssignmentItem[]>([])
/** 最新上架任务：给「顺手再接一单」留个入口 */
const latestTasks = ref<TaskItem[]>([])
const week = ref<MyWeekProgress | null>(null)
const notice = ref<NoticeItem | null>(null)
/** 条幅只在「最新公告还没看过」时出现；看过（或手动关闭）后收起 */
const showNoticeBar = computed(() => !!notice.value && !isDismissed(notice.value.id))

/** 点条幅 = 读它：收起条幅并跳到该公告详情 */
function openNoticeDetail() {
  if (!notice.value?.id)
    return
  dismiss(notice.value.id)
  router.push({ name: 'work-notices', query: { id: String(notice.value.id) } })
}
const loading = ref(true)
const failed = ref(false)

/** 「要交」= 已接收待提交 + 被驳回需要重提；待接收还没接，不能算成要交 */
const dueCount = computed(() => (stats.value.accepted ?? 0) + (stats.value.rejected_submissions ?? 0))
const hasDue = computed(() => dueCount.value > 0)

/** 还没接的单：单独提示，点进去是工作台的「待接收」 */
const pendingCount = computed(() => stats.value.pending ?? 0)

/** 成果概览三个数字：待审核 / 已通过 / 被驳回 */
const resultCells = computed(() => [
  { key: 'RESULT_PENDING' as const, label: t('home.resultPending'), count: stats.value.submissions_pending ?? 0 },
  { key: 'RESULT_APPROVED' as const, label: t('home.resultApproved'), count: stats.value.submissions_approved ?? 0 },
  { key: 'RESULT_REJECTED' as const, label: t('home.resultRejected'), count: stats.value.rejected_submissions ?? 0 },
])

/** 本周按时完成：本周没有到期任务时不画进度条 */
const weekDue = computed(() => week.value?.due ?? 0)
const weekDone = computed(() => week.value?.done ?? 0)
const weekPercent = computed(() => (weekDue.value > 0 ? Math.min(100, Math.round((weekDone.value / weekDue.value) * 100)) : 0))

/** 收益：本月应发 / 额度进度；额度为 0 时不画进度条，避免除零与假仪表盘 */
const payable = computed(() => Number(payout.value?.payable ?? 0))
const payoutLimit = computed(() => Number(payout.value?.payout_limit ?? 0))
const allowance = computed(() => Number(payout.value?.allowance_balance ?? 0))
const quotaPercent = computed(() =>
  payoutLimit.value > 0 ? Math.min(100, Math.round((payable.value / payoutLimit.value) * 100)) : 0,
)

/** 最近截止：取待交任务里最早的那条，并把任务名一起说出来 */
const nearestDeadline = computed(() => {
  const withDate = upcoming.value.filter(item => item.task?.period)
  if (!withDate.length)
    return null
  const first = [...withDate].sort((a, b) => String(a.task?.period).localeCompare(String(b.task?.period)))[0]
  return {
    name: taskDisplayName(first.task),
    date: String(first.task?.period).slice(0, 10),
  }
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

function taskPriceText(task: TaskItem) {
  const price = task.item?.config?.price ?? task.template?.config?.price
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
  const [statsRes, payoutRes, upcomingRes, noticeRes, weekRes, latestRes] = await Promise.allSettled([
    MarketAPI.getMyTaskStats(),
    MarketAPI.getMyPayout(currentPeriod()),
    MarketAPI.getMyAssignments({ page_no: 1, page_size: 3, status: 'ACCEPTED' }),
    NoticeAPI.getAvailable(1),
    MarketAPI.getMyWeekProgress(),
    MarketAPI.getTaskHall({ page_no: 1, page_size: 3 }),
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

  if (weekRes.status === 'fulfilled')
    week.value = weekRes.value

  if (latestRes.status === 'fulfilled')
    latestTasks.value = (latestRes.value.items ?? []).slice(0, 3)

  loading.value = false
  uni.stopPullDownRefresh()
}

/** 点「待接收/待提交/被驳回」跳到工作台并直接定位到对应筛选 */
function goDesk(filter: WorkDeskFilter) {
  workDeskFilter.request(filter)
  router.pushTab({ name: 'market-work-desk' })
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
      <!-- 头部 Hero：今天是几号、有几件事要交，三个数字可直接点进对应队列 -->
      <view class="hero">
        <view class="hero__date">
          {{ dateText }}
        </view>
        <view class="hero__say">
          <template v-if="hasDue">
            {{ t('home.dueHeadPrefix') }} <text class="hero__count">
              {{ dueCount }}
            </text> {{ t('home.dueHeadSuffix') }}
          </template>
          <template v-else>
            {{ t('home.todoEmpty') }}
          </template>
        </view>

        <!-- 公告：未读时滚动展示，点开即已读并收起 -->
        <view v-if="showNoticeBar" class="hero__notice">
          <wd-notice-bar
            :text="notice?.notice_title || ''"
            prefix="notification"
            scrollable
            color="#FFFFFF"
            background-color="rgba(255, 255, 255, 0.16)"
            custom-class="hero-notice"
            @click="openNoticeDetail"
          />
        </view>
        <view v-else-if="!notice" class="hero__notice-empty">
          {{ t('home.noNotice') }}
        </view>

        <!-- 待接收是「等你接的单」，与「要交的」分开说，不混成一个数字 -->
        <view v-if="pendingCount > 0" class="hero__hint" hover-class="hero__hint--pressed" @click="goDesk('PENDING')">
          <text class="hero__hint-text">
            {{ t('home.pendingHint', { count: pendingCount }) }}
          </text>
          <text class="hero__hint-arrow">
            ›
          </text>
        </view>

        <view v-if="nearestDeadline" class="hero__deadline">
          <text class="hero__deadline-label">
            {{ t('home.nearestDeadline') }}
          </text>
          <text class="hero__deadline-task">
            {{ nearestDeadline.name }} · {{ nearestDeadline.date }}
          </text>
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

      <!-- 本周进度：本周到期多少、交了多少 -->
      <view class="week mx-3 mt-3">
        <view class="week__row">
          <text class="week__label">
            {{ t('home.weekTitle') }}
          </text>
          <text v-if="weekDue > 0" class="week__value">
            {{ weekDone }} <text class="week__sub">
              / {{ weekDue }}
            </text>
          </text>
          <text v-else class="week__value week__value--muted">
            {{ t('home.weekNone') }}
          </text>
        </view>
        <view v-if="weekDue > 0" class="week__track">
          <view class="week__fill" :style="{ width: `${weekPercent}%` }" />
        </view>
      </view>

      <!-- 我的成果：三个数字，点进去看对应状态 -->
      <view class="results mx-3 mt-3">
        <view
          v-for="cell in resultCells"
          :key="cell.key"
          class="results__cell"
          hover-class="results__cell--pressed"
          @click="goDesk(cell.key)"
        >
          <text class="results__num" :class="{ 'results__num--alert': cell.key === 'RESULT_REJECTED' && cell.count > 0 }">
            {{ cell.count }}
          </text>
          <text class="results__label">
            {{ cell.label }}
          </text>
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

      <!-- 最新任务：顺手再接一单 -->
      <template v-if="latestTasks.length > 0">
        <view class="sect mx-3 mt-4">
          <text class="sect__title">
            {{ t('home.latestTasks') }}
          </text>
          <text class="sect__more" @click="router.pushTab({ name: 'market-task-hall' })">
            {{ t('home.viewAll') }} ›
          </text>
        </view>
        <view class="mx-3 mt-1 flex flex-col gap-2">
          <view
            v-for="task in latestTasks"
            :key="task.id"
            class="queue"
            hover-class="queue--pressed"
            @click="router.push({ name: 'market-task-detail', query: { id: String(task.id) } })"
          >
            <view class="queue__mark" />
            <view class="min-w-0 flex-1">
              <view class="queue__name">
                {{ taskDisplayName(task) }}
              </view>
              <view class="queue__meta">
                <text>{{ task.project?.name }}</text>
                <text class="queue__dot">
                  ·
                </text>
                <text>{{ deadlineChip(task.period).text }}</text>
              </view>
            </view>
            <view class="queue__side">
              <text class="queue__price">
                {{ taskPriceText(task) }}
              </text>
              <text class="queue__action">
                {{ t('hall.view') }}
              </text>
            </view>
          </view>
        </view>
      </template>

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
/* 头部 Hero：品牌渐变 + 白色文字，是首页唯一「有重量」的视觉块 */
.hero {
  position: relative;
  overflow: hidden;
  /* 自定义导航：hero 自己当头部，顶部让出状态栏 + 胶囊按钮区 */
  padding: calc(var(--status-bar-height, 0px) + 96rpx) 32rpx 30rpx;
  border-radius: 0 0 28rpx 28rpx;
  background: linear-gradient(135deg, var(--wot-primary-6), var(--wot-primary-4));
  box-shadow: 0 12rpx 32rpx rgba(28, 100, 253, 0.24);

  /* 右上角浅色光圈，避免大面积纯色显得平 */
  &::after {
    content: '';
    position: absolute;
    right: -80rpx;
    top: -100rpx;
    width: 320rpx;
    height: 320rpx;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.12);
  }

  &__date {
    position: relative;
    font-size: 22rpx;
    color: rgba(255, 255, 255, 0.82);
    letter-spacing: 0.5rpx;
  }

  &__say {
    position: relative;
    margin-top: 10rpx;
    font-size: 36rpx;
    font-weight: 600;
    line-height: 1.35;
    color: #fff;
  }

  &__count {
    font-size: 44rpx;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  &__notice {
    position: relative;
    margin-top: 24rpx;
    border-radius: 16rpx;
    overflow: hidden;
  }

  &__notice-empty {
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.78);
  }

  /* 待接收提示：可点，去工作台「待接收」 */
  &__hint {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 22rpx;
    padding: 14rpx 20rpx;
    border-radius: 12rpx;
    background: rgba(255, 255, 255, 0.16);

    &--pressed {
      opacity: 0.8;
    }
  }

  &__hint-text {
    font-size: 24rpx;
    color: #fff;
  }

  &__hint-arrow {
    font-size: 26rpx;
    color: rgba(255, 255, 255, 0.8);
  }

  &__deadline {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16rpx;
    margin-top: 18rpx;
    font-size: 22rpx;
    color: rgba(255, 255, 255, 0.78);
  }

  &__deadline-label {
    flex-shrink: 0;
  }

  &__deadline-task {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 24rpx;
    font-weight: 600;
    color: #fff;
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

/* 本周进度：一条细进度 + 一行数字 */
.week {
  padding: 24rpx 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &__row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }

  &__label {
    font-size: 24rpx;
    color: var(--wot-text-secondary);
  }

  &__value {
    font-size: 32rpx;
    font-weight: 700;
    color: var(--wot-success-main);
    font-variant-numeric: tabular-nums;

    &--muted {
      font-size: 24rpx;
      font-weight: 500;
      color: var(--wot-text-placeholder);
    }
  }

  &__sub {
    font-size: 22rpx;
    font-weight: 500;
    color: var(--wot-text-auxiliary);
  }

  &__track {
    height: 8rpx;
    margin-top: 16rpx;
    border-radius: 9999rpx;
    background: var(--wot-filled-content);
    overflow: hidden;
  }

  &__fill {
    height: 100%;
    border-radius: 9999rpx;
    background: var(--wot-success-main);
  }
}

/* 我的成果：三格数字，点进工作台的对应状态 */
.results {
  display: flex;
  padding: 24rpx 8rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &__cell {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4rpx;
    border-radius: 12rpx;

    &--pressed {
      opacity: 0.7;
    }
  }

  &__num {
    font-size: 38rpx;
    font-weight: 700;
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
}

.queue__price {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--wot-danger-main);
  font-variant-numeric: tabular-nums;
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
