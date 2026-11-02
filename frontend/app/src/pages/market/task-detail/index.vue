<script setup lang="ts">
import type { FormSchemaField, TaskItem } from '@/api/module_market'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { useShare } from '@/composables/useShare'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'market-task-detail',
  style: { navigationBarTitleText: '任务详情', enablePullDownRefresh: true },
})

const { t } = useI18n()
const router = useRouter()
const toast = useToast()

const taskId = ref<number>()
const task = ref<TaskItem | null>(null)
const loading = ref(true)
const failed = ref(false)
const claiming = ref(false)

useShare(() => ({ title: task.value ? `${taskTypeName(task.value)} · ${t('taskDetail.title')}` : t('taskDetail.title') }))

const formFields = computed<FormSchemaField[]>(() => task.value?.task_type?.form_schema ?? [])
const unit = computed(() => task.value?.task_type?.unit ?? '')
const price = computed(() => Number(task.value?.unit_price ?? 0))
const qty = computed(() => Number(task.value?.exec_qty ?? 0))
const maxEarn = computed(() => CommonUtil.formatMoney(price.value * qty.value, 2))

/** 定额任务的剩余份数：接满即不可再接；周期性任务不限总份额 */
const remain = computed(() => {
  if (task.value?.task_kind !== 'quota' || task.value?.exec_qty == null)
    return null
  return qty.value - Number(task.value?.claimed_count ?? 0)
})
const soldOut = computed(() => remain.value !== null && remain.value <= 0)

/** 截止时间：只有定额任务有结束时间，周期性任务不假造倒计时 */
const deadline = computed(() => {
  const end = task.value?.exec_time_end
  if (!end)
    return ''
  return end.slice(0, 16)
})

function taskTypeName(item: TaskItem) {
  return item.task_type?.name || item.task_no || t('hall.unnamed')
}

function fieldLabel(field: FormSchemaField) {
  return field.label || field.name
}

async function loadTask() {
  if (!taskId.value)
    return
  loading.value = true
  failed.value = false
  try {
    task.value = await MarketAPI.getTaskDetail(taskId.value)
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
  if (!task.value?.id || soldOut.value || claiming.value)
    return
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: t('taskDetail.claimTitle'),
      content: t('taskDetail.claimConfirm', { name: taskTypeName(task.value!) }),
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
    // 接单后去「我的任务」继续提交成果：这里用 switchTab，避免详情页留在栈里
    setTimeout(() => router.pushTab({ name: 'market-my-task' }), 600)
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
  const id = Number(query?.id)
  taskId.value = Number.isFinite(id) && id > 0 ? id : undefined
  if (!taskId.value) {
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
        <!-- 头部：任务名 + 金额是这张卡的主信息，编号降级为辅助 -->
        <view class="detail-hero">
          <view class="detail-hero__name">
            {{ taskTypeName(task) }}
          </view>
          <view class="detail-hero__no">
            {{ task.task_no }}
          </view>
          <view class="detail-hero__price-row">
            <text class="detail-hero__price">
              ¥{{ CommonUtil.formatMoney(price) }}
            </text>
            <text v-if="unit" class="detail-hero__unit">
              / {{ unit }}
            </text>
          </view>
          <view class="mt-2 flex flex-wrap items-center gap-1.5">
            <text v-if="deadline" class="detail-chip detail-chip--urgent">
              {{ t('market.deadline') }} {{ deadline }}
            </text>
            <text v-if="remain !== null" class="detail-chip" :class="soldOut ? 'detail-chip--muted' : 'detail-chip--calm'">
              {{ soldOut ? t('market.claimedFull') : t('hall.remain', { count: remain }) }}
            </text>
            <text v-if="task.period" class="detail-chip detail-chip--muted">
              {{ t('market.period') }} {{ task.period }}
            </text>
          </view>
        </view>

        <!-- 执行标准：接单前必须让用户知道要干什么，这是加详情页的核心理由 -->
        <view class="detail-section">
          <view class="detail-section__title">
            {{ t('taskDetail.execStandard') }}
          </view>
          <view class="detail-section__text">
            {{ task.task_type?.exec_standard || t('taskDetail.execStandardEmpty') }}
          </view>
        </view>

        <view class="detail-section">
          <view class="detail-section__title">
            {{ formFields.length > 0 ? t('taskDetail.formFields', { count: formFields.length }) : t('taskDetail.formFieldsEmpty') }}
          </view>
          <view v-if="formFields.length > 0" class="mt-1 flex flex-wrap gap-1.5">
            <text v-for="field in formFields" :key="field.name" class="detail-field">
              {{ fieldLabel(field) }}{{ field.required ? ' *' : '' }}
            </text>
          </view>
        </view>

        <view class="detail-section">
          <view class="detail-section__title">
            {{ t('taskDetail.priceRule') }}
          </view>
          <wd-cell-group border custom-class="mt-1! rounded-2! overflow-hidden">
            <wd-cell :title="t('taskDetail.unitLabel')" :value="unit || '-'" />
            <wd-cell :title="t('market.unitPrice')" :value="`¥${CommonUtil.formatMoney(price, 2)}`" />
            <wd-cell :title="t('market.execQty')" :value="String(qty)" />
          </wd-cell-group>
        </view>
      </view>

      <!-- 底部固定操作条：内容区已预留等高内边距，避免被遮住 -->
      <view class="detail-cta">
        <view class="flex-1">
          <view class="detail-cta__label">
            {{ t('taskDetail.maxEarn') }}
          </view>
          <view class="detail-cta__amount">
            ¥{{ maxEarn }}
          </view>
        </view>
        <wd-button type="primary" round :disabled="soldOut" :loading="claiming" custom-class="detail-cta__button" @click="handleClaim">
          {{ soldOut ? t('market.claimedFull') : t('taskDetail.claimNow') }}
        </wd-button>
      </view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
/* 底部固定条高度 + 安全区，内容区据此留出等量空间，避免最后一段被遮住 */
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

  &__button {
    min-width: 220rpx;
  }
}
</style>
