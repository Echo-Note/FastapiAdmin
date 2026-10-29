<script setup lang="ts">
import type { AssignmentItem, TaskItem } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { ASSIGNMENT_STATUS_MAP, statusMeta } from '@/constants'

definePage({ name: 'market-task-detail', style: { navigationBarTitleText: '任务详情' } })

/** 分配方式本地映射 */
const ASSIGN_MODE_LABEL: Record<string, string> = {
  direct: '定向分派',
  open: '公开大厅',
}

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

/** 页面入口：来源 my-task（带 assignment_id）或 task-hall（仅 task_id） */
const assignmentId = ref<number>()
const taskId = ref<number>()

const task = ref<TaskItem | null>(null)
const assignmentStatus = ref<string>()
const loading = ref(false)
const loadFailed = ref(false)
const acting = ref(false)

/** 单价（模板 config.price，仅数字） */
const amountText = computed(() => {
  const price = task.value?.template?.config?.price
  return price == null ? '' : Number(price).toFixed(2)
})

/** 计价单位 */
const unitText = computed(() => task.value?.template?.config?.unit ?? '')

/** 是否为「我的任务」入口（有分派实例） */
const fromMine = computed(() => assignmentId.value != null)

/** 可提交：已接收 / 进行中 / 已提交（驳回可重提）/ 已审核 */
const canSubmit = computed(() => {
  const s = assignmentStatus.value
  return s === 'ACCEPTED' || s === 'SUBMITTING' || s === 'SUBMITTED' || s === 'REVIEWED'
})

/** 待接收：定向分派未接收 */
const canAccept = computed(() => assignmentStatus.value === 'PENDING')

/** 大厅任务可接单（无分派实例） */
const canClaim = computed(() => !fromMine.value && task.value != null)

/** 执行标准（取自模板 config.exec_standard） */
const execStandard = computed(() => task.value?.template?.config?.exec_standard || '-')

/** 分配方式文案 */
const assignModeLabel = computed(() => ASSIGN_MODE_LABEL[task.value?.assign_mode ?? ''] ?? task.value?.assign_mode ?? '-')

/** 分派状态展示（我的任务入口） */
const assignmentStatusInfo = computed(() => statusMeta(ASSIGNMENT_STATUS_MAP, assignmentStatus.value))

async function load() {
  loading.value = true
  loadFailed.value = false
  try {
    if (assignmentId.value != null) {
      // 我的任务入口：直接取分派单详情（含内嵌 task + 状态）
      const detail: AssignmentItem = await MarketAPI.getAssignmentDetail(assignmentId.value)
      assignmentStatus.value = detail.status
      task.value = detail.task ?? null
    }
    else if (taskId.value != null) {
      // 任务大厅入口：直接取任务详情
      task.value = await MarketAPI.getTaskDetail(taskId.value)
    }
    if (!task.value)
      loadFailed.value = true
  }
  catch {
    loadFailed.value = true
  }
  finally {
    loading.value = false
  }
}

/** 接收定向分派任务 */
async function handleAccept() {
  if (!assignmentId.value)
    return
  acting.value = true
  try {
    await MarketAPI.acceptAssignment(assignmentId.value)
    assignmentStatus.value = 'ACCEPTED'
    toast.success(t('market.receiveSuccess'))
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    acting.value = false
  }
}

/** 大厅接单（先到先得） */
async function handleClaim() {
  if (!task.value?.id)
    return
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: t('common.title'),
      content: `${t('market.claimConfirm')}\n${task.value?.name ?? task.value?.task_no ?? ''} · ¥${amountText.value || '—'}`,
      success: res => resolve(res.confirm),
      fail: () => resolve(false),
    })
  })
  if (!confirmed)
    return
  acting.value = true
  try {
    const assigned = await MarketAPI.claimTask(task.value.id)
    assignmentId.value = assigned.id
    assignmentStatus.value = assigned.status
    toast.success(t('market.claimSuccess'))
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    acting.value = false
  }
}

/** 去提交成果 */
function goSubmit() {
  router.push({
    name: 'market-submission-form',
    query: { assignment_id: String(assignmentId.value) },
  })
}

/** 回任务大厅接单（空/失败态 CTA） */
function goTaskHall() {
  router.replace({ name: 'market-task-hall' })
}

onLoad((query) => {
  assignmentId.value = query?.assignment_id ? Number(query.assignment_id) : undefined
  taskId.value = query?.task_id ? Number(query.task_id) : undefined
  load()
})
</script>

<template>
  <view class="page-wraper">
    <view class="px-3 py-3">
      <!-- 骨架屏 -->
      <view v-if="loading" class="space-y-3">
        <view class="bg-skeleton h-44 rounded-3" />
        <view class="bg-skeleton h-40 rounded-3" />
      </view>

      <!-- 加载失败 -->
      <view v-else-if="loadFailed" class="wot-bg-filled-oppo flex flex-col items-center rounded-3 py-12">
        <wd-icon name="warn-bold" size="48px" custom-class="mb-3" />
        <view class="wot-text-text-auxiliary text-3">
          {{ t('common.loadFailed') }}
        </view>
        <wd-button type="primary" size="small" class="mt-5" @click="load">
          {{ t('common.retry') }}
        </wd-button>
      </view>

      <!-- 空态 -->
      <view v-else-if="!task" class="wot-bg-filled-oppo flex flex-col items-center rounded-3 py-12">
        <view class="wot-text-text-auxiliary text-3">
          {{ t('market.emptyTaskHall') }}
        </view>
        <wd-button type="primary" size="small" class="mt-5" @click="goTaskHall">
          {{ t('market.goTaskHall') }}
        </wd-button>
      </view>

      <!-- 任务详情 -->
      <template v-else>
        <!-- 头部品牌渐变卡 -->
        <view class="hero-card relative overflow-hidden rounded-3 px-5 py-6 text-white">
          <view class="flex items-center justify-between">
            <view
              class="rounded-full px-3 py-1 text-2.5 font-medium"
              style="background: rgba(255,255,255,0.22);"
            >
              {{ fromMine ? assignmentStatusInfo.label : assignModeLabel }}
            </view>
          </view>
          <view class="mt-4 text-5 font-bold leading-snug">
            {{ task.name ?? task.task_no ?? '' }}
          </view>
          <view class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-3" style="opacity: 0.9">
            <view>{{ t('market.period') }} {{ task.period ?? '-' }}</view>
            <view v-if="task.task_no">
              编号 {{ task.task_no }}
            </view>
          </view>
        </view>

        <!-- 计价与执行标准 -->
        <view class="wot-bg-filled-oppo mt-3 rounded-3 px-5 py-5">
          <view class="wot-text-text-auxiliary text-2.5">
            {{ t('market.unitPrice') }}
          </view>
          <view class="mt-2 flex items-baseline gap-1">
            <text class="wot-text-primary-6 text-3 font-semibold">
              ¥
            </text>
            <text class="wot-text-primary-6 text-7 font-bold">
              {{ amountText || '—' }}
            </text>
            <text v-if="unitText" class="wot-text-text-auxiliary ml-1 text-2.5">
              / {{ unitText }}
            </text>
          </view>
          <view class="wot-border-border-main mt-4 border-t pt-4">
            <view class="wot-text-text-auxiliary text-2.5">
              {{ t('market.execStandard') }}
            </view>
            <view class="wot-text-text-main mt-1.5 text-3 leading-relaxed">
              {{ execStandard }}
            </view>
          </view>
        </view>

        <!-- 动作条 -->
        <view class="mt-6">
          <wd-button v-if="canClaim" block type="primary" size="large" :loading="acting" @click="handleClaim">
            {{ t('market.claim') }}
          </wd-button>
          <wd-button v-else-if="canAccept" block type="primary" size="large" :loading="acting" @click="handleAccept">
            {{ t('market.accept') }}
          </wd-button>
          <wd-button v-else-if="canSubmit" block type="primary" size="large" @click="goSubmit">
            {{ t('market.goSubmit') }}
          </wd-button>
          <view v-else class="wot-text-text-auxiliary py-2 text-center text-3">
            {{ assignmentStatusInfo.label }}
          </view>
        </view>
      </template>

      <wd-gap height="120rpx" safe-area-bottom />
    </view>
  </view>
</template>

<style lang="scss" scoped>
.hero-card {
  background: linear-gradient(135deg, var(--wot-primary-6), var(--wot-primary-4));
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.16);
}

.bg-skeleton {
  background: linear-gradient(
    90deg,
    var(--wot-filled-content, #f2f3f5) 25%,
    var(--wot-filled-oppo, #f7f8fa) 37%,
    var(--wot-filled-content, #f2f3f5) 63%
  );
  background-size: 400% 100%;
  animation: skeleton-loading 1.4s ease infinite;
}

@keyframes skeleton-loading {
  0% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0 50%;
  }
}
</style>
