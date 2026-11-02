<script setup lang="ts">
import type { FormSchema, TaskItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useRouteIntent } from '@/composables/useRouteIntent'
import { useShare } from '@/composables/useShare'
import { ASSIGNMENT_STATUS_MAP, statusMeta, taskDisplayName } from '@/constants'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'market-task-detail',
  style: { navigationBarTitleText: '任务详情', enablePullDownRefresh: true },
})

const { t } = useI18n()
const router = useRouter()
const toast = useToast()
const { take, set: setRouteIntent } = useRouteIntent()

const taskId = ref<number>()
/** 从「工作台」点进来时带的分派 id：用已有分派详情接口取任务，不再单开页面 */
const assignmentId = ref<number>()
const assignmentStatus = ref<string>()
const task = ref<TaskItem | null>(null)
const loading = ref(true)
const failed = ref(false)
const claiming = ref(false)

useShare(() => ({
  title: task.value ? `${taskDisplayName(task.value)} · ${t('taskDetail.title')}` : t('taskDetail.title'),
}))

/** 采集字段：三级任务自带分节优先，叶子模板回退模板分节 */
const formSchema = computed<FormSchema>(() => task.value?.item?.config?.form_schema ?? task.value?.template?.config?.form_schema ?? [])

const fieldCount = computed(() =>
  formSchema.value.reduce((sum, section) => sum + Object.keys(section.fields ?? {}).length, 0),
)

const unit = computed(() => task.value?.item?.config?.unit ?? task.value?.template?.config?.unit ?? '')
const price = computed(() => Number(task.value?.item?.config?.price ?? task.value?.template?.config?.price ?? 0))

/** 归属链路：项目 → 分类 → 模板 */
const pathText = computed(() =>
  [task.value?.project?.name, task.value?.template?.category?.name, task.value?.template?.name].filter(Boolean).join(' · '),
)

/** 截止时间：`period` 即截止日期；这里只做展示与是否已过期判断 */
const deadlineText = computed(() => (task.value?.period ? String(task.value.period).slice(0, 10) : ''))
const expired = computed(() => {
  if (!task.value?.period)
    return false
  const end = new Date(String(task.value.period).replace(/-/g, '/')).getTime()
  return Number.isFinite(end) && end < Date.now()
})

/** 定向分派任务不能在大厅接单（C 端只能从「我的任务」接收） */
const directOnly = computed(() => task.value?.assign_mode === 'direct')
const claimable = computed(() => !!task.value && !directOnly.value && !expired.value)

/** 我的分派：待接收可接收，其余可提交成果；已结算只读 */
const assignmentInfo = computed(() => (assignmentStatus.value ? statusMeta(ASSIGNMENT_STATUS_MAP, assignmentStatus.value) : null))
const canAcceptAssignment = computed(() => assignmentStatus.value === 'PENDING')
const canSubmitAssignment = computed(() =>
  ['ACCEPTED', 'SUBMITTED', 'REVIEWED'].includes(assignmentStatus.value ?? ''),
)

/** 我的任务入口进来的：接单区改成「接收 / 提交成果」 */
function handleAssignmentAction() {
  if (canAcceptAssignment.value && assignmentId.value) {
    router.pushTab({ name: 'market-work-desk' })
  }
  else if (canSubmitAssignment.value && assignmentId.value) {
    setRouteIntent('market-submission-form', { assignment_id: String(assignmentId.value) })
    router.push({ name: 'market-submission-form' })
  }
}

async function loadTask() {
  if (!taskId.value && !assignmentId.value)
    return
  loading.value = true
  failed.value = false
  try {
    if (assignmentId.value) {
      // 我的任务：分派详情里已含任务上下文，定向任务也能看
      const detail = await MarketAPI.getAssignmentDetail(assignmentId.value)
      assignmentStatus.value = detail.status
      task.value = detail.task ?? null
      if (!task.value)
        failed.value = true
    }
    else if (taskId.value) {
      task.value = await MarketAPI.getTaskDetail(taskId.value)
    }
  }
  catch {
    failed.value = true
    task.value = null
  }
  finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

async function handleClaim() {
  if (!task.value?.id || !claimable.value || claiming.value)
    return
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: t('taskDetail.claimTitle'),
      content: t('taskDetail.claimConfirm', { name: taskDisplayName(task.value!) }),
      confirmText: t('taskDetail.claimNow'),
      success: res => resolve(res.confirm),
      fail: () => resolve(false),
    })
  })
  if (!confirmed)
    return

  claiming.value = true
  try {
    await MarketAPI.claimTask(task.value.id)
    toast.success(t('market.claimSuccess'))
    // 接单后去「我的任务」继续提交成果，避免详情页留在栈里
    setTimeout(() => router.pushTab({ name: 'market-work-desk' }), 600)
  }
  catch {
    // http 层已统一提示（如名额已满 / 已接过）
    loadTask()
  }
  finally {
    claiming.value = false
  }
}

onLoad((query) => {
  // 优先取一次性意图（列表点击），URL 上的 ?id 作为兜底（分享 / 深链）
  const intent = take('market-task-detail')
  const intentId = intent?.id
  const intentAssignment = intent?.assignment_id
  assignmentId.value = intentAssignment ? Number(intentAssignment) : undefined
  const id = intentId ? Number(intentId) : Number(query?.id)
  taskId.value = Number.isFinite(id) && id > 0 ? id : undefined
  if (!taskId.value && !assignmentId.value) {
    failed.value = true
    loading.value = false
    return
  }
  loadTask()
})

onPullDownRefresh(() => {
  loadTask()
})
</script>

<template>
  <view class="page-wraper">
    <SkeletonPage v-if="loading" :rows="5" class="pt-3" />

    <view v-else-if="failed || !task" class="mt-12 flex flex-col items-center gap-3">
      <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
      <wd-text :text="taskId ? t('taskDetail.notFound') : t('common.loadFailed')" class="wot-text-text-secondary text-3" />
      <wd-button v-if="taskId" size="small" round @click="loadTask">
        {{ t('common.retry') }}
      </wd-button>
    </view>

    <template v-else>
      <view class="detail-body">
        <!-- 头部：任务名 + 金额是主信息，归属链路是辅助 -->
        <view class="detail-hero">
          <view class="detail-hero__name">
            {{ taskDisplayName(task) }}
          </view>
          <view v-if="pathText" class="detail-hero__no">
            {{ pathText }}
          </view>
          <view class="detail-hero__price-row">
            <text class="detail-hero__price">
              {{ price > 0 ? `¥${CommonUtil.formatMoney(price)}` : t('taskDetail.priceTbd') }}
            </text>
            <text v-if="unit" class="detail-hero__unit">
              / {{ unit }}
            </text>
          </view>
          <view class="mt-2 flex flex-wrap items-center gap-1.5">
            <text v-if="assignmentInfo" class="detail-chip detail-chip--mine">
              {{ t('taskDetail.myTaskTag') }} · {{ assignmentInfo.label }}
            </text>
            <text v-if="deadlineText" class="detail-chip" :class="expired ? 'detail-chip--muted' : 'detail-chip--urgent'">
              {{ t('market.deadline') }} {{ deadlineText }}
            </text>
            <text class="detail-chip detail-chip--muted">
              {{ task.task_no }}
            </text>
            <text v-if="(task.assignment_count ?? 0) > 0" class="detail-chip detail-chip--calm">
              {{ t('hall.joined', { count: task.assignment_count }) }}
            </text>
          </view>
        </view>

        <!-- 执行标准 / 执行要求在接单前必须可见，这是加详情页的核心理由 -->
        <view class="detail-section">
          <view class="detail-section__title">
            {{ t('taskDetail.execStandard') }}
          </view>
          <view class="detail-section__text">
            {{ task.exec_standard || t('taskDetail.execStandardEmpty') }}
          </view>
        </view>

        <view v-if="task.executor_requirement" class="detail-section">
          <view class="detail-section__title">
            {{ t('taskDetail.execRequirement') }}
          </view>
          <view class="detail-section__text">
            {{ task.executor_requirement }}
          </view>
        </view>

        <view class="detail-section">
          <view class="detail-section__title">
            {{ fieldCount > 0 ? t('taskDetail.formFields', { count: fieldCount }) : t('taskDetail.formFieldsEmpty') }}
          </view>
          <view v-for="section in formSchema" :key="section.code" class="mt-2">
            <view class="detail-section__sub">
              {{ section.name }}
            </view>
            <view class="mt-1 flex flex-wrap gap-1.5">
              <text v-for="(field, key) in section.fields" :key="key" class="detail-field">
                {{ field.label || key }}
              </text>
            </view>
          </view>
        </view>
      </view>

      <!-- 底部固定操作条：内容区已预留等高内边距，避免被遮住 -->
      <view class="detail-cta">
        <view class="flex-1">
          <view v-if="directOnly && !assignmentId" class="detail-cta__label">
            {{ t('taskDetail.directOnly') }}
          </view>
          <template v-else>
            <view class="detail-cta__label">
              {{ t('taskDetail.unitLabel') }}
            </view>
            <view class="detail-cta__amount">
              {{ price > 0 ? `¥${CommonUtil.formatMoney(price, 2)}` : t('taskDetail.priceTbd') }}
              <text v-if="unit" class="detail-cta__unit">
                / {{ unit }}
              </text>
            </view>
          </template>
        </view>
        <wd-button
          v-if="assignmentId"
          type="primary"
          round
          :disabled="!canAcceptAssignment && !canSubmitAssignment"
          custom-class="detail-cta__button"
          @click="handleAssignmentAction"
        >
          {{ canSubmitAssignment ? t('myTask.submit') : (canAcceptAssignment ? t('myTask.accept') : assignmentInfo?.label) }}
        </wd-button>
        <wd-button
          v-else
          type="primary"
          round
          :disabled="!claimable"
          :loading="claiming"
          custom-class="detail-cta__button"
          @click="handleClaim"
        >
          {{ expired ? t('hall.deadlinePassed') : t('taskDetail.claimNow') }}
        </wd-button>
      </view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
$cta-height: 128rpx;

.detail-body {
  padding: 24rpx 24rpx calc(#{$cta-height} + 48rpx);
}

.detail-hero {
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &__name {
    font-size: 36rpx;
    font-weight: 600;
    line-height: 1.35;
    color: var(--wot-text-main);
  }

  &__no {
    margin-top: 6rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__price-row {
    display: flex;
    align-items: baseline;
    gap: 8rpx;
    margin-top: 18rpx;
  }

  &__price {
    font-size: 52rpx;
    font-weight: 700;
    line-height: 1.1;
    color: var(--wot-danger-main);
    font-variant-numeric: tabular-nums;
  }

  &__unit {
    font-size: 24rpx;
    color: var(--wot-text-auxiliary);
  }
}

.detail-section {
  margin-top: 24rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &__title {
    font-size: 28rpx;
    font-weight: 600;
    color: var(--wot-text-main);
  }

  &__sub {
    font-size: 24rpx;
    font-weight: 500;
    color: var(--wot-text-secondary);
  }

  &__text {
    margin-top: 10rpx;
    font-size: 26rpx;
    line-height: 1.7;
    color: var(--wot-text-secondary);
  }
}

.detail-chip {
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

  &--muted {
    color: var(--wot-text-auxiliary);
    background: var(--wot-filled-content);
  }

  /* 我的任务：与大厅进入区分开，一眼知道这是已经接过的单 */
  &--mine {
    color: var(--wot-primary-6);
    background: var(--wot-primary-1);
    font-weight: 600;
  }
}

.detail-field {
  padding: 6rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content);
}

.detail-cta {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 24rpx;
  height: $cta-height;
  padding: 0 24rpx;
  padding-bottom: env(safe-area-inset-bottom);
  border-top: 1rpx solid var(--wot-border-light);
  background: var(--wot-filled-oppo);

  &__label {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__amount {
    font-size: 36rpx;
    font-weight: 700;
    line-height: 1.2;
    color: var(--wot-danger-main);
    font-variant-numeric: tabular-nums;
  }

  &__unit {
    font-size: 22rpx;
    font-weight: 400;
    color: var(--wot-text-auxiliary);
  }

  &__button {
    min-width: 220rpx;
  }
}
</style>
