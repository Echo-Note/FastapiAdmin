<script setup lang="ts">
import type { AssignmentItem, MyTaskStats, SubmissionItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useMarketListPage } from '@/composables/useMarketListPage'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { useTaskStats } from '@/composables/useTaskStats'
import { taskDisplayName } from '@/constants'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'market-my-task',
  layout: 'tabbar',
  style: { navigationBarTitleText: '我的任务', enablePullDownRefresh: true },
})
useI18nNavTitle('myTask.title')

const { t } = useI18n()
const router = useRouter()
const { loadTaskStats } = useTaskStats()

useShare(() => ({ title: t('myTask.shareTitle'), path: '/pages/market/my-task/index' }))
useTabbarActive('pages/market/my-task/index', 'market-my-task')

type Layer = 'task' | 'result'
type LoadMode = 'first' | 'refresh' | 'next'

/** 分派状态（后端 AssignmentStatus，无 SUBMITTING 中间态） */
const TASK_TABS: { value?: string, labelKey: string }[] = [
  { value: undefined, labelKey: 'myTask.statusAll' },
  { value: 'PENDING', labelKey: 'myTask.statusPending' },
  { value: 'ACCEPTED', labelKey: 'myTask.statusActive' },
  { value: 'SUBMITTED', labelKey: 'myTask.statusSubmitted' },
  { value: 'REVIEWED', labelKey: 'myTask.statusReviewed' },
]

const RESULT_TABS: { value?: string, labelKey: string }[] = [
  { value: undefined, labelKey: 'myTask.resultAll' },
  { value: 'PENDING', labelKey: 'myTask.resultPending' },
  { value: 'APPROVED', labelKey: 'myTask.resultApproved' },
  { value: 'REJECTED', labelKey: 'myTask.resultRejected' },
]

/** 默认落在「进行中」：打开「我的任务」的人手里通常有活，比「全部」更接近真实意图 */
const DEFAULT_TASK_TAB = 2
const REJECTED_TAB = 3

const layer = ref<Layer>('task')
const LAYER_OPTIONS: { value: Layer, labelKey: string }[] = [
  { value: 'task', labelKey: 'myTask.tabTask' },
  { value: 'result', labelKey: 'myTask.tabResult' },
]

const taskTabIndex = ref(DEFAULT_TASK_TAB)
const taskStatus = ref<string | undefined>('ACCEPTED')
const resultTabIndex = ref(0)
const resultStatus = ref<string | undefined>()

const stats = ref<MyTaskStats>({})
const rejectedCount = computed(() => stats.value.rejected_submissions ?? 0)

const taskFailed = ref(false)
const taskLoaded = ref(false)
const resultFailed = ref(false)
const resultLoaded = ref(false)
const acceptingId = ref<number>()
const resubmittingId = ref<number>()

const taskPager = useMarketListPage<AssignmentItem>({
  fetcher: p => MarketAPI.getMyAssignments({ ...p, status: taskStatus.value }),
  onError: () => { taskFailed.value = true },
})
const { list: taskList, total: taskTotal, loading: taskLoading } = taskPager

const resultPager = useMarketListPage<SubmissionItem>({
  fetcher: p => MarketAPI.getMySubmissions({ ...p, status: resultStatus.value }),
  onError: () => { resultFailed.value = true },
})
const { list: resultList, total: resultTotal, loading: resultLoading } = resultPager

interface StatusMeta {
  labelKey: string
  tone: 'warn' | 'primary' | 'muted' | 'success' | 'danger'
}

const TASK_STATUS_META: Record<string, StatusMeta> = {
  PENDING: { labelKey: 'myTask.statusPending', tone: 'warn' },
  ACCEPTED: { labelKey: 'myTask.statusActive', tone: 'primary' },
  SUBMITTED: { labelKey: 'myTask.statusSubmitted', tone: 'muted' },
  REVIEWED: { labelKey: 'myTask.statusReviewed', tone: 'success' },
  SETTLED: { labelKey: 'myTask.statusSettled', tone: 'success' },
}

const RESULT_STATUS_META: Record<string, StatusMeta> = {
  PENDING: { labelKey: 'myTask.resultPending', tone: 'muted' },
  APPROVED: { labelKey: 'myTask.resultApproved', tone: 'success' },
  REJECTED: { labelKey: 'myTask.resultRejected', tone: 'danger' },
  DRAFT: { labelKey: 'myTask.resultDraft', tone: 'muted' },
}

function labelOf(meta: Record<string, StatusMeta>, status?: string) {
  const hit = meta[status ?? '']
  return hit ? t(hit.labelKey) : (status ?? '')
}

function toneOf(meta: Record<string, StatusMeta>, status?: string) {
  return `status-chip--${meta[status ?? '']?.tone ?? 'muted'}`
}

function taskStatusLabel(status?: string) {
  return labelOf(TASK_STATUS_META, status)
}

function taskStatusTone(status?: string) {
  return toneOf(TASK_STATUS_META, status)
}

function resultStatusLabel(status?: string) {
  return labelOf(RESULT_STATUS_META, status)
}

function resultStatusTone(status?: string) {
  return toneOf(RESULT_STATUS_META, status)
}

/** 角标：待接收 / 进行中；计数为 0 时不挂徽标 */
function taskBadge(value?: string) {
  let count = 0
  if (value === 'PENDING')
    count = stats.value.pending ?? 0
  else if (value === 'ACCEPTED')
    count = stats.value.accepted ?? 0
  return count > 0 ? { value: count, type: 'danger' as const } : undefined
}

function amountText(item: AssignmentItem) {
  const price = item.task?.item?.config?.price ?? item.task?.template?.config?.price
  return price == null ? '' : `¥${CommonUtil.formatMoney(price)}`
}

function unitText(item: AssignmentItem) {
  const unit = item.task?.item?.config?.unit ?? item.task?.template?.config?.unit
  return unit ? `/${unit}` : ''
}

function deadlineText(item: AssignmentItem) {
  return item.task?.period ? String(item.task.period).slice(0, 10) : ''
}

function submittedTime(item: SubmissionItem) {
  return (item.reviewed_at || '').slice(0, 16)
}

async function loadStats() {
  try {
    stats.value = await MarketAPI.getMyTaskStats()
  }
  catch {
    // 角标是辅助信息：失败静默降级，保留上一次计数
  }
}

async function loadTasks(mode: LoadMode = 'first') {
  taskFailed.value = false
  if (mode === 'next')
    await taskPager.loadNext()
  else if (mode === 'refresh')
    await taskPager.refreshData()
  else
    await taskPager.toFirst()
  taskLoaded.value = true
}

async function loadResults(mode: LoadMode = 'first') {
  resultFailed.value = false
  if (mode === 'next')
    await resultPager.loadNext()
  else if (mode === 'refresh')
    await resultPager.refreshData()
  else
    await resultPager.toFirst()
  resultLoaded.value = true
}

async function switchLayer(next: Layer) {
  if (layer.value === next)
    return
  layer.value = next
  // 成果层按需加载：大多数人只看任务，不为第二层付一次请求
  if (next === 'task' && !taskLoaded.value)
    await loadTasks('first')
  if (next === 'result' && !resultLoaded.value)
    await loadResults('first')
}

async function onTaskTabChange(e: { index: number }) {
  taskStatus.value = TASK_TABS[e.index]?.value
  await loadTasks('first')
}

async function onResultTabChange(e: { index: number }) {
  resultStatus.value = RESULT_TABS[e.index]?.value
  await loadResults('first')
}

/** 驳回提示：切到成果层的「已驳回」，让「有一份要重交」立刻可见 */
async function goRejectedTab() {
  layer.value = 'result'
  resultTabIndex.value = REJECTED_TAB
  resultStatus.value = 'REJECTED'
  await loadResults('first')
}

async function handleAccept(item: AssignmentItem) {
  if (!item.id || acceptingId.value)
    return
  acceptingId.value = item.id
  try {
    await MarketAPI.acceptAssignment(item.id)
    // 接收后任务落进「进行中」，回到第一页重取，并把角标刷新
    await Promise.all([loadTasks('first'), loadStats(), loadTaskStats(true)])
  }
  catch {
    // http 层已统一提示，列表保持原样等待用户重试
  }
  finally {
    acceptingId.value = undefined
  }
}

function goSubmit(item: AssignmentItem) {
  if (!item.id)
    return
  router.push({ name: 'market-submission-form', query: { assignment_id: String(item.id) } })
}

function goResubmit(item: SubmissionItem) {
  if (!item.id || resubmittingId.value)
    return
  resubmittingId.value = item.id
  router.push({
    name: 'market-submission-form',
    query: { assignment_id: String(item.assignment_id ?? ''), submission_id: String(item.id) },
  })
  resubmittingId.value = undefined
}

function goTaskHall() {
  router.pushTab({ name: 'market-task-hall' })
}

function resultEmptyTip() {
  return resultStatus.value === 'REJECTED' ? t('myTask.emptyRejected') : t('myTask.emptyResult')
}

onLoad(() => {
  loadStats()
  loadTasks('first')
})

/** 首次 onShow 由 onLoad 负责，之后每次回到本页才刷新，避免重复请求 */
let shownOnce = false
onShow(() => {
  if (!shownOnce) {
    shownOnce = true
    return
  }
  loadStats()
  if (layer.value === 'task')
    loadTasks('first')
  else
    loadResults('first')
})

onReachBottom(() => {
  if (layer.value === 'task') {
    if (!taskLoading.value)
      loadTasks('next')
    return
  }
  if (!resultLoading.value)
    loadResults('next')
})

onPullDownRefresh(async () => {
  await Promise.all([loadStats(), layer.value === 'task' ? loadTasks('refresh') : loadResults('refresh')])
  uni.stopPullDownRefresh()
})
</script>

<template>
  <view class="tabbar-wraper my-task-page">
    <!-- 任务 / 成果两层：分段控件只负责换层，状态筛选交给下面的 Tab，避免两层筛选挤在一行 -->
    <view class="mx-3 mt-3">
      <view class="layer-switch">
        <view
          v-for="opt in LAYER_OPTIONS"
          :key="opt.value"
          class="layer-switch__item"
          :class="{ 'layer-switch__item--active': layer === opt.value }"
          hover-class="layer-switch__item--pressed"
          @click="switchLayer(opt.value)"
        >
          {{ t(opt.labelKey) }}
        </view>
      </view>
    </view>

    <!-- 驳回提示：驳回不体现在分派状态上，不给提示用户永远不知道该改哪 -->
    <view
      v-if="layer === 'task' && rejectedCount > 0"
      class="reject-hint mx-3 mt-3"
      hover-class="reject-hint--pressed"
      @click="goRejectedTab"
    >
      <wd-icon name="exclamation-circle" size="16px" color="var(--wot-danger-main)" />
      <text class="reject-hint__text">
        {{ t('myTask.rejectedCount', { count: rejectedCount }) }}
      </text>
      <text class="reject-hint__arrow">
        ›
      </text>
    </view>

    <wd-tabs
      v-if="layer === 'task'"
      v-model="taskTabIndex"
      line-theme="text"
      custom-class="mt-1"
      @change="onTaskTabChange"
    >
      <wd-tab
        v-for="opt in TASK_TABS"
        :key="opt.labelKey"
        :title="t(opt.labelKey)"
        :badge-props="taskBadge(opt.value)"
      />
    </wd-tabs>
    <wd-tabs
      v-else
      v-model="resultTabIndex"
      line-theme="text"
      custom-class="mt-1"
      @change="onResultTabChange"
    >
      <wd-tab v-for="opt in RESULT_TABS" :key="opt.labelKey" :title="t(opt.labelKey)" />
    </wd-tabs>

    <!-- 任务层 -->
    <template v-if="layer === 'task'">
      <SkeletonPage v-if="taskLoading && taskList.length === 0" :rows="4" class="mt-3" />

      <view v-else-if="taskFailed && taskList.length === 0" class="mx-3 mt-8 flex flex-col items-center gap-3">
        <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
        <wd-text :text="t('common.loadFailed')" class="wot-text-text-secondary text-3" />
        <wd-button size="small" round @click="loadTasks('first')">
          {{ t('common.retry') }}
        </wd-button>
      </view>

      <view v-else-if="taskList.length === 0" class="empty-tip mx-3 mt-8" hover-class="empty-tip--pressed" @click="goTaskHall">
        <wd-empty :tip="t('myTask.emptyTask')" />
      </view>

      <view v-else class="mx-3 mt-3 flex flex-col gap-3">
        <view v-for="item in taskList" :key="item.id" class="task-card">
          <view class="flex items-start gap-3">
            <view class="min-w-0 flex-1">
              <view class="task-card__name">
                {{ taskDisplayName(item.task) }}
              </view>
              <view class="task-card__no">
                {{ item.task?.task_no }}
              </view>
            </view>
            <text class="status-chip shrink-0" :class="taskStatusTone(item.status)">
              {{ taskStatusLabel(item.status) }}
            </text>
          </view>

          <view class="mt-2 flex flex-wrap items-center gap-1.5">
            <text v-if="deadlineText(item)" class="task-card__meta">
              {{ t('market.deadline') }} {{ deadlineText(item) }}
            </text>
          </view>

          <view class="task-card__footer">
            <view class="min-w-0 flex items-baseline gap-1">
              <text class="task-card__amount">
                {{ amountText(item) }}
              </text>
              <text v-if="unitText(item)" class="task-card__unit">
                {{ unitText(item) }}
              </text>
            </view>
            <wd-button
              v-if="item.status === 'PENDING'"
              type="primary"
              size="large"
              round
              :loading="acceptingId != null && acceptingId === item.id"
              @click.stop="handleAccept(item)"
            >
              {{ t('myTask.accept') }}
            </wd-button>
            <wd-button
              v-else-if="item.status !== 'SETTLED'"
              type="primary"
              size="large"
              round
              @click.stop="goSubmit(item)"
            >
              {{ t('myTask.submit') }}
            </wd-button>
          </view>
        </view>
      </view>

      <wd-loading v-if="taskLoading && taskList.length > 0" size="20px" class="mx-auto my-2 block" />
      <wd-text
        v-else-if="taskTotal > 0 && taskList.length >= taskTotal"
        class="wot-text-text-auxiliary my-2 block text-center text-2.5"
        :text="t('common.noMore')"
      />
    </template>

    <!-- 成果层 -->
    <template v-else>
      <SkeletonPage v-if="resultLoading && resultList.length === 0" :rows="4" class="mt-3" />

      <view v-else-if="resultFailed && resultList.length === 0" class="mx-3 mt-8 flex flex-col items-center gap-3">
        <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
        <wd-text :text="t('common.loadFailed')" class="wot-text-text-secondary text-3" />
        <wd-button size="small" round @click="loadResults('first')">
          {{ t('common.retry') }}
        </wd-button>
      </view>

      <view v-else-if="resultList.length === 0" class="mx-3 mt-8">
        <wd-empty :tip="resultEmptyTip()" />
      </view>

      <view v-else class="mx-3 mt-3 flex flex-col gap-3">
        <view v-for="item in resultList" :key="item.id" class="result-card">
          <view class="flex items-start gap-3">
            <view class="min-w-0 flex-1">
              <view class="result-card__institution">
                {{ item.subject_name || '-' }}
              </view>
              <view class="result-card__meta">
                <text>{{ t('market.period') }} {{ item.period ?? '-' }}</text>
                <text class="result-card__sep">
                  ·
                </text>
                <text>{{ t('myTask.version', { version: item.version ?? 1 }) }}</text>
                <template v-if="submittedTime(item)">
                  <text class="result-card__sep">
                    ·
                  </text>
                  <text>{{ t('myTask.submittedAt', { time: submittedTime(item) }) }}</text>
                </template>
              </view>
            </view>
            <text class="status-chip shrink-0" :class="resultStatusTone(item.status)">
              {{ resultStatusLabel(item.status) }}
            </text>
          </view>

          <view v-if="item.status === 'REJECTED'" class="reject-reason">
            <view class="reject-reason__title">
              {{ t('myTask.rejectReason') }}
            </view>
            <view class="reject-reason__text">
              {{ item.review_comment || '-' }}
            </view>
          </view>

          <view v-if="item.status === 'REJECTED'" class="result-card__footer">
            <wd-button
              type="primary"
              size="large"
              round
              :loading="resubmittingId != null && resubmittingId === item.id"
              @click="goResubmit(item)"
            >
              {{ t('myTask.resubmit') }}
            </wd-button>
          </view>
        </view>
      </view>

      <wd-loading v-if="resultLoading && resultList.length > 0" size="20px" class="mx-auto my-2 block" />
      <wd-text
        v-else-if="resultTotal > 0 && resultList.length >= resultTotal"
        class="wot-text-text-auxiliary my-2 block text-center text-2.5"
        :text="t('common.noMore')"
      />
    </template>

    <wd-gap height="40rpx" />
  </view>
</template>

<style lang="scss" scoped>
/* wd-tabs 默认 flex:1 + 大内边距：5 个中文状态标签在 375px 手机上会被截成「进…」，
   收紧字号与内边距后三字标签（待接收/进行中/已提交/已审核）可完整显示 */
.my-task-page {
  --wot-tabs-nav-item-font-size: 26rpx;
  --wot-tabs-nav-item-padding: 14rpx 8rpx;
}

/* 分层控件：灰底轨道 + 白底滑块 */
.layer-switch {
  display: flex;
  gap: 6rpx;
  padding: 6rpx;
  border-radius: 9999rpx;
  background: var(--wot-filled-content);

  &__item {
    flex: 1;
    height: 76rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 9999rpx;
    font-size: 28rpx;
    color: var(--wot-text-secondary);
    transition: background 0.15s ease;

    &--active {
      font-weight: 600;
      color: var(--wot-text-main);
      background: var(--wot-filled-oppo);
    }

    &--pressed {
      opacity: 0.72;
    }
  }
}

.reject-hint {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: var(--wot-filled-oppo);
  border: 1rpx solid var(--wot-danger-surface);

  &--pressed {
    opacity: 0.72;
  }

  &__text {
    flex: 1;
    font-size: 24rpx;
    color: var(--wot-danger-main);
  }

  &__arrow {
    font-size: 26rpx;
    color: var(--wot-text-auxiliary);
  }
}

.task-card,
.result-card {
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);
}

.task-card {
  &__name {
    font-size: 30rpx;
    font-weight: 600;
    line-height: 1.35;
    color: var(--wot-text-main);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__no {
    margin-top: 6rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__meta {
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

  &__amount {
    font-size: 32rpx;
    font-weight: 700;
    color: var(--wot-danger-main);
    font-variant-numeric: tabular-nums;
  }

  &__unit {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }
}

.result-card {
  &__institution {
    font-size: 30rpx;
    font-weight: 600;
    color: var(--wot-text-main);
  }

  &__meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6rpx;
    margin-top: 8rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__sep {
    color: var(--wot-text-disabled);
  }

  &__footer {
    margin-top: 20rpx;
    padding-top: 16rpx;
    border-top: 1rpx solid var(--wot-border-light);
  }
}

.reject-reason {
  margin-top: 16rpx;
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  background: var(--wot-danger-surface);

  &__title {
    font-size: 22rpx;
    font-weight: 600;
    color: var(--wot-danger-main);
  }

  &__text {
    margin-top: 6rpx;
    font-size: 24rpx;
    line-height: 1.6;
    color: var(--wot-text-secondary);
  }
}

/* 状态 chip：形状统一，语义靠颜色 + 文案 */
.status-chip {
  padding: 4rpx 14rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;

  &--warn {
    color: var(--wot-warning-main);
    background: var(--wot-warning-surface);
  }

  &--primary {
    color: var(--wot-primary-6);
    background: var(--wot-primary-1);
  }

  &--muted {
    color: var(--wot-text-auxiliary);
    background: var(--wot-filled-content);
  }

  &--success {
    color: var(--wot-success-main);
    background: var(--wot-success-surface);
  }

  &--danger {
    color: var(--wot-danger-main);
    background: var(--wot-danger-surface);
  }
}

.empty-tip {
  &--pressed {
    opacity: 0.72;
  }
}
</style>
