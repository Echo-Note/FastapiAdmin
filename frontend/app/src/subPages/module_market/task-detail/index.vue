<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { ASSIGNMENT_STATUS_MAP, statusMeta } from '@/constants'

definePage({ name: 'market-task-detail', style: { navigationBarTitleText: '任务详情' } })

/** 任务详情（对齐后端 TaskOutSchema：name 为 C 端显示名，config 挂模板） */
interface DetailTaskItem {
  id?: number
  task_no?: string
  name?: string
  period?: string
  assign_mode?: string
  template?: {
    id?: number
    name?: string
    config?: {
      unit?: string
      price?: number | null
      exec_standard?: string | null
    } | null
  } | null
}

/** 分派单（我的任务入口，含 task 摘要） */
interface DetailAssignmentItem {
  id?: number
  status?: string
  task?: DetailTaskItem | null
}

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

const task = ref<DetailTaskItem | null>(null)
const assignmentStatus = ref<string>()
const loading = ref(false)
const loadFailed = ref(false)
const acting = ref(false)

/** 单价（模板 config.price） */
const priceText = computed(() => {
  const price = task.value?.template?.config?.price
  return price == null ? '—' : `¥${Number(price).toFixed(2)}`
})

/** 计价单位 */
const unitText = computed(() => task.value?.template?.config?.unit ?? '-')

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
const execStandard = computed(() => task.value?.template?.config?.exec_standard ?? '-')

/** 分配方式文案 */
const assignModeLabel = computed(() => ASSIGN_MODE_LABEL[task.value?.assign_mode ?? ''] ?? task.value?.assign_mode ?? '-')

/** 分派状态展示（我的任务入口） */
const assignmentStatusInfo = computed(() => statusMeta(ASSIGNMENT_STATUS_MAP, assignmentStatus.value))

async function load() {
  loading.value = true
  loadFailed.value = false
  try {
    if (assignmentId.value != null) {
      // 我的任务入口：从我的任务列表现取分派实例（含 task 摘要 + 状态）
      const res = await MarketAPI.getMyAssignments({ page_no: 1, page_size: 100 })
      const items = (res as any).items as DetailAssignmentItem[] ?? []
      const found = items.find(i => String(i.id) === String(assignmentId.value))
      if (found) {
        task.value = (found.task as DetailTaskItem) ?? null
        assignmentStatus.value = found.status
      }
    }
    else if (taskId.value != null) {
      // 任务大厅入口：从大厅列表现取任务
      const res = await MarketAPI.getTaskHall({ page_no: 1, page_size: 100 })
      const items = (res as any).items as DetailTaskItem[] ?? []
      task.value = items.find(i => String(i.id) === String(taskId.value)) ?? null
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
      content: `${t('market.claimConfirm')}\n${task.value?.name ?? task.value?.task_no ?? ''} · ${priceText.value}`,
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
      <wd-loading v-if="loading" class="my-6 block" />

      <template v-else-if="loadFailed">
        <view class="flex flex-col items-center rounded-2 bg-white py-10">
          <wd-icon name="warn-bold" size="48px" custom-class="mb-3" />
          <wd-text class="wot-text-text-auxiliary text-3" :text="t('common.loadFailed')" />
          <wd-button type="primary" size="small" class="mt-4" @click="load">
            {{ t('common.retry') }}
          </wd-button>
        </view>
      </template>

      <template v-else-if="task">
        <!-- 任务名 + 状态 -->
        <view class="rounded-2 bg-white p-4">
          <view class="flex items-center justify-between">
            <wd-text class="wot-text-text-main text-5 font-semibold" :text="task.name ?? task.task_no ?? ''" />
            <wd-tag v-if="fromMine" :type="assignmentStatusInfo.type" plain :title="assignmentStatusInfo.label" />
            <wd-tag v-else type="primary" plain :title="assignModeLabel" />
          </view>
          <view class="mt-2 flex items-center gap-3">
            <wd-text class="wot-text-text-auxiliary text-2.5" :text="`${t('market.period')} ${task.period ?? '-'}`" />
          </view>
        </view>

        <!-- 计价与说明 -->
        <view class="mt-3 rounded-2 bg-white p-4">
          <wd-cell-group border custom-class="rounded-2! overflow-hidden">
            <wd-cell :title="t('market.unitPrice')" :value="priceText" value-class="wot-text-error-main!" />
            <wd-cell title="计价单位" :value="unitText" />
            <wd-cell :title="t('market.execStandard')" :value="execStandard" :is-link="false" />
          </wd-cell-group>
        </view>

        <!-- 动作条 -->
        <view class="mt-4">
          <wd-button v-if="canClaim" block type="primary" :loading="acting" @click="handleClaim">
            {{ t('market.claim') }}
          </wd-button>
          <wd-button v-else-if="canAccept" block type="primary" :loading="acting" @click="handleAccept">
            {{ t('market.accept') }}
          </wd-button>
          <wd-button v-else-if="canSubmit" block type="primary" @click="goSubmit">
            {{ t('market.goSubmit') }}
          </wd-button>
          <wd-text v-else class="wot-text-text-auxiliary block text-center text-2.5" :text="assignmentStatusInfo.label" />
        </view>
      </template>

      <template v-else>
        <view class="flex flex-col items-center rounded-2 bg-white py-10">
          <wd-text class="wot-text-text-auxiliary text-3" :text="t('market.emptyTaskHall')" />
          <wd-button type="primary" size="small" class="mt-4" @click="goTaskHall">
            {{ t('market.goTaskHall') }}
          </wd-button>
        </view>
      </template>

      <wd-gap height="100rpx" safe-area-bottom />
    </view>
  </view>
</template>
