<script setup lang="ts">
import type { AssignmentItem, SubmissionItem, TaskStats } from '@/api/module_market'
import { onLoad, onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useMarketListPage } from '@/composables/useMarketListPage'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { useTaskStats } from '@/composables/useTaskStats'
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

/** 拉取分派时用于回查 form_schema 的页大小（后端 page_size 上限 100） */
const LOOKUP_PAGE_SIZE = 100

type Layer = 'task' | 'result'
type LoadMode = 'first' | 'refresh' | 'next'

/** 成果列表比 SubmissionItem 多一个通用审计字段 created_time（提交时间的主要来源） */
type SubmissionRow = SubmissionItem & { created_time?: string }

/** 两层：任务（要动手做的事）与成果（已经交上去的东西），状态机互不相干，各自分页 */
const layer = ref<Layer>('task')
const LAYER_OPTIONS: { value: Layer, labelKey: string }[] = [
  { value: 'task', labelKey: 'myTask.tabTask' },
  { value: 'result', labelKey: 'myTask.tabResult' },
]

const TASK_TABS: { value?: string, labelKey: string }[] = [
  { value: undefined, labelKey: 'myTask.statusAll' },
  { value: 'PENDING', labelKey: 'myTask.statusPending' },
  { value: 'ACTIVE', labelKey: 'myTask.statusActive' },
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

const taskTabIndex = ref(DEFAULT_TASK_TAB)
const taskStatus = ref<string | undefined>('ACTIVE')
const resultTabIndex = ref(0)
const resultStatus = ref<string | undefined>()

const stats = ref<TaskStats>({})
const rejectedCount = computed(() => stats.value.rejected_submissions ?? 0)

const taskFailed = ref(false)
const taskLoaded = ref(false)
const resultFailed = ref(false)
const resultLoaded = ref(false)
/** 正在接收的分派 ID：卡片按钮用它展示 loading，同时防重复点击 */
const acceptingId = ref<number>()
/** 正在准备重提的成果 ID（需先回查任务的 form_schema） */
const resubmittingId = ref<number>()

const taskPager = useMarketListPage<AssignmentItem>({
  fetcher: p => MarketAPI.getMyAssignments({ ...p, status: taskStatus.value }),
  onError: () => { taskFailed.value = true },
})
const { list: taskList, total: taskTotal, loading: taskLoading } = taskPager

const resultPager = useMarketListPage<SubmissionRow>({
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
  // ACCEPTED（已接收待填）与 SUBMITTING（已存草稿）对 C 端是同一件事：还没交
  ACCEPTED: { labelKey: 'myTask.statusActive', tone: 'primary' },
  SUBMITTING: { labelKey: 'myTask.statusActive', tone: 'primary' },
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

/** 「进行中」角标 = 已接收 + 已存草稿，与后端 ACTIVE 合成桶口径一致 */
function activeCount() {
  return (stats.value.accepted ?? 0) + (stats.value.submitting ?? 0)
}

function taskBadge(value?: string) {
  let count = 0
  if (value === 'PENDING')
    count = stats.value.pending ?? 0
  else if (value === 'ACTIVE')
    count = activeCount()
  // 计数为 0 时不挂徽标（wd-badge 默认也不显示 0，这里少一层包裹节点）
  return count > 0 ? { value: count, type: 'danger' as const } : undefined
}

function assignmentName(item: AssignmentItem) {
  return item.task?.task_type?.name || item.task?.task_no || ''
}

function amountText(item: AssignmentItem) {
  return `¥${CommonUtil.formatMoney(item.task?.unit_price)}`
}

function unitText(item: AssignmentItem) {
  const unit = item.task?.task_type?.unit
  return unit ? `/${unit}` : ''
}

function deadlineText(item: AssignmentItem) {
  const end = item.task?.exec_time_end
  return end ? end.slice(0, 10) : ''
}

function submittedTime(item: SubmissionRow) {
  const time = item.created_time || item.reviewed_at || ''
  return time.slice(0, 16)
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

async function refreshTabbarBadge() {
  try {
    await loadTaskStats(true)
  }
  catch {
    // 底部角标非关键路径
  }
}

async function handleAccept(item: AssignmentItem) {
  if (!item.id || acceptingId.value)
    return
  acceptingId.value = item.id
  try {
    await MarketAPI.acceptAssignment(item.id)
    // 接收后任务落进「进行中」，回来这一页必须能直接看到，所以整页回到第一页重取
    await Promise.all([loadTasks('first'), loadStats(), refreshTabbarBadge()])
  }
  catch {
    // http 层已统一提示（如任务已被撤回），列表保持原样等待用户重试
  }
  finally {
    acceptingId.value = undefined
  }
}

function goSubmit(item: AssignmentItem) {
  if (!item.id)
    return
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

/**
 * 成果列表里没有任务的表单定义，而驳回重提必须带上 form_schema 才能渲染出原表单。
 * 先查已加载的分派列表，未命中再单独回查一次（已驳回的分派通常不在当前 Tab 里）。
 */
async function findAssignmentTask(assignmentId?: number) {
  if (!assignmentId)
    return undefined
  const cached = taskList.value.find(item => item.id === assignmentId)
  if (cached)
    return cached.task ?? undefined
  try {
    const res = await MarketAPI.getMyAssignments({ page_no: 1, page_size: LOOKUP_PAGE_SIZE })
    return res.items?.find(item => item.id === assignmentId)?.task ?? undefined
  }
  catch {
    return undefined
  }
}

async function handleResubmit(item: SubmissionRow) {
  if (!item.id || resubmittingId.value)
    return
  resubmittingId.value = item.id
  try {
    const task = await findAssignmentTask(item.assignment_id)
    router.push({
      name: 'market-submission-form',
      query: {
        submission_id: String(item.id),
        assignment_id: String(item.assignment_id ?? ''),
        task_no: task?.task_no ?? '',
        form_schema: encodeURIComponent(JSON.stringify(task?.task_type?.form_schema ?? [])),
      },
    })
  }
  finally {
    resubmittingId.value = undefined
  }
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

/** 首次 onShow 由 onLoad 负责，之后的每次回到本页才刷新，避免重复请求 */
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

    <!-- 驳回提示：驳回不体现在任务分派状态上，不给提示用户永远不知道该改哪 -->
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
        <view
          v-for="item in taskList"
          :key="item.id"
          class="task-card"
        >
          <view class="flex items-start gap-3">
            <view class="min-w-0 flex-1">
              <view class="task-card__name">
                {{ assignmentName(item) }}
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
              <text class="task-card__price">
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
                {{ item.institution?.name || '-' }}
              </view>
              <view class="result-card__meta">
                <text>{{ t('myTask.submittedAt', { time: submittedTime(item) }) }}</text>
                <text class="result-card__sep">
                  ·
                </text>
                <text>{{ t('myTask.version', { version: item.version ?? 1 }) }}</text>
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
              @click="handleResubmit(item)"
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

/* 分层控件：灰底轨道 + 白底滑块，和任务大厅的胶囊筛选同一套圆角语言，但层级更高（整页切换） */
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

/* 驳回提示条：卡面白底承载警示文案，红色只用在文案/图标上（间距走 8rpx 节奏） */
.reject-hint {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: var(--wot-filled-oppo);

  &__text {
    flex: 1;
    min-width: 0;
    font-size: 24rpx;
    line-height: 1.5;
    color: var(--wot-danger-main);
  }

  &__arrow {
    flex-shrink: 0;
    font-size: 28rpx;
    color: var(--wot-danger-main);
  }

  &--pressed {
    opacity: 0.72;
  }
}

/* 状态标签：形状统一，颜色只做语义分级（文案本身已写明状态，不依赖颜色传达） */
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
    background: var(--wot-filled-content);
  }

  &--muted {
    color: var(--wot-text-secondary);
    background: var(--wot-filled-content);
  }

  &--success {
    color: var(--wot-success-main);
    background: var(--wot-success-surface);
  }

  &--danger {
    color: var(--wot-danger-main);
    background: var(--wot-filled-content);
  }
}

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
    /* 长任务名最多两行，避免把状态标签挤到卡片外 */
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

  &__meta {
    font-size: 22rpx;
    line-height: 1.5;
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

  &__price {
    font-size: 38rpx;
    font-weight: 700;
    line-height: 1.2;
    color: var(--wot-danger-main);
    /* 金额按位数对齐，纵向比较多张卡片时不会跳动 */
    font-variant-numeric: tabular-nums;
  }

  &__unit {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }
}

.result-card {
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &__institution {
    font-size: 32rpx;
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
    flex-wrap: wrap;
    align-items: center;
    gap: 8rpx;
    margin-top: 8rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__sep {
    color: var(--wot-text-auxiliary);
  }

  &__footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 20rpx;
    padding-top: 16rpx;
    border-top: 1rpx solid var(--wot-border-light);
  }
}

/* 任务空态本身写着「去任务大厅看看」，整块可点，给一个按压缩放反馈 */
.empty-tip {
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.72;
  }
}

/* 驳回原因：整段可长可短，独立成块以便与状态标签区分开 */
.reject-reason {
  margin-top: 20rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: var(--wot-filled-content);

  &__title {
    font-size: 22rpx;
    font-weight: 600;
    color: var(--wot-danger-main);
  }

  &__text {
    margin-top: 8rpx;
    font-size: 26rpx;
    line-height: 1.6;
    color: var(--wot-text-secondary);
  }
}
</style>
