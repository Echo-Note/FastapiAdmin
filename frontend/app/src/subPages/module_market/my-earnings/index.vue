<script setup lang="ts">
import type { PayoutSettlement, PayoutSummary } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'

definePage({ name: 'market-my-earnings', style: { navigationBarTitleText: '我的收益' } })

const { t } = useI18n()

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const period = ref(currentMonth())
const payout = ref<PayoutSummary | null>(null)
const loading = ref(false)
const loadFailed = ref(false)

/** 金额统一两位小数；后端 Decimal 已量化，这里只负责空值兜底 */
function money(value?: number | null) {
  return Number(value ?? 0).toFixed(2)
}

const payableText = computed(() => money(payout.value?.payable))

/** hero 下方四项：额度 / 实发 / 期初滚存 / 期末滚存，全部是该周期的数 */
const overview = computed(() => [
  { label: t('market.payoutLimit'), value: `¥${money(payout.value?.payout_limit)}` },
  { label: t('market.paid'), value: `¥${money(payout.value?.paid)}` },
  { label: t('market.prevBalance'), value: `¥${money(payout.value?.prev_balance)}` },
  { label: t('market.balanceAfter'), value: `¥${money(payout.value?.allowance_balance)}` },
])

const settlements = computed(() => payout.value?.settlements ?? [])

/** 期末滚存 > 0 才有顺延：这部分钱被额度封住，滚到下月 */
const carryoverTipVisible = computed(() => Number(payout.value?.allowance_balance ?? 0) > 0)

/** 收益来源行的计价摘要：`{数量} × ¥{单价}/{单位}` */
function priceSummary(row: PayoutSettlement) {
  const qty = Number(row.qty ?? 0)
  if (row.price === null || row.price === undefined)
    return `${qty} ${row.unit ?? ''}`.trim()
  const unit = row.unit ? `/${row.unit}` : ''
  return `${qty} × ¥${money(row.price)}${unit}`
}

function shiftMonth(delta: number) {
  const [y, m] = period.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  period.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  loadPayout()
}

async function loadPayout() {
  loading.value = true
  loadFailed.value = false
  try {
    payout.value = await MarketAPI.getMyPayout(period.value)
  }
  catch {
    payout.value = null
    loadFailed.value = true
  }
  finally {
    loading.value = false
  }
}

onLoad(() => loadPayout())
</script>

<template>
  <view class="page-wraper">
    <view class="px-3 py-3">
      <!-- 周期切换：只换 period，其余数字都由后端按周期给出 -->
      <view class="period-switch">
        <view class="period-switch__btn" @click="shiftMonth(-1)">
          <wd-icon name="arrow-left" size="18px" />
        </view>
        <view class="period-switch__text">
          {{ period }}
        </view>
        <view class="period-switch__btn" @click="shiftMonth(1)">
          <wd-icon name="arrow-right" size="18px" />
        </view>
      </view>

      <!-- 当月概览：应发为主数字，额度/实发/滚存为辅 -->
      <view class="earn-hero">
        <wd-loading v-if="loading" class="my-4 block" color="#fff" />
        <template v-else-if="payout">
          <view class="earn-hero__label">
            {{ t('market.monthPayable') }}
          </view>
          <view class="earn-hero__value">
            ¥{{ payableText }}
          </view>
          <view class="earn-hero__divider" />
          <view class="earn-hero__grid">
            <view v-for="item in overview" :key="item.label" class="earn-hero__cell">
              <text class="earn-hero__cell-label">
                {{ item.label }}
              </text>
              <text class="earn-hero__cell-value">
                {{ item.value }}
              </text>
            </view>
          </view>
        </template>
        <template v-else>
          <view class="flex flex-col items-center py-6">
            <view class="text-3" style="color: rgba(255,255,255,0.9)">
              {{ loadFailed ? t('common.loadFailed') : t('market.monthPayable') }}
            </view>
            <wd-button v-if="loadFailed" type="primary" size="small" class="mt-4" @click="loadPayout">
              {{ t('common.retry') }}
            </wd-button>
          </view>
        </template>
      </view>

      <!-- 津贴顺延提示：超出当月发放额度的部分滚入下月 -->
      <view v-if="payout && carryoverTipVisible" class="carryover-tip">
        <wd-icon name="warn-bold" size="16px" custom-class="wot-text-warning-main" />
        <text class="carryover-tip__text">
          {{ t('market.allowanceCarryover') }}
        </text>
      </view>

      <!-- 收益来源：该周期的结算单，每行标出由哪个任务产生 -->
      <view v-if="payout && !loading && settlements.length > 0" class="items-card">
        <view class="items-card__title">
          {{ t('market.incomeSource') }}
        </view>
        <view v-for="row in settlements" :key="row.id" class="items-row">
          <view class="items-row__left">
            <view class="items-row__task">
              {{ row.task_name || row.task_no }}
            </view>
            <view class="items-row__meta">
              <text v-if="row.template_name">
                {{ row.template_name }}
              </text>
              <text v-if="row.task_no" class="items-row__meta-sep">
                {{ row.task_no }}
              </text>
              <text class="items-row__meta-sep">
                {{ priceSummary(row) }}
              </text>
            </view>
          </view>
          <view class="items-row__amounts">
            <text class="items-row__payable">
              ¥{{ money(row.payable) }}
            </text>
            <text class="items-row__paid">
              {{ t('market.paid') }} ¥{{ money(row.paid) }}
            </text>
          </view>
        </view>
      </view>

      <!-- 空态：该月没有结算单 -->
      <view v-else-if="payout && !loading" class="items-card items-card--empty">
        <text class="items-card__empty-text">
          {{ t('market.emptyEarnings') }}
        </text>
      </view>

      <wd-gap height="100rpx" safe-area-bottom />
    </view>
  </view>
</template>

<style lang="scss" scoped>
.period-switch {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32rpx;
  padding: 16rpx;
  margin-bottom: 20rpx;
  background: var(--wot-bg-filled-oppo, #fff);
  border-radius: 24rpx;
}

.period-switch__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  color: var(--wot-primary-6);
  background: var(--wot-primary-1, #f0f5ff);
}

.period-switch__text {
  min-width: 180rpx;
  font-size: 32rpx;
  font-weight: 600;
  text-align: center;
  color: var(--wot-text-main);
}

.earn-hero {
  padding: 36rpx 32rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, var(--wot-primary-6), var(--wot-primary-4));
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.16);
}

.earn-hero__label {
  font-size: 24rpx;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
}

.earn-hero__value {
  margin-top: 8rpx;
  font-size: 56rpx;
  font-weight: 700;
  line-height: 1.2;
  color: #fff;
}

.earn-hero__divider {
  height: 1rpx;
  margin: 28rpx 0;
  background: rgba(255, 255, 255, 0.25);
}

.earn-hero__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20rpx 24rpx;
}

.earn-hero__cell {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.earn-hero__cell-label {
  font-size: 22rpx;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.75);
}

.earn-hero__cell-value {
  font-size: 28rpx;
  font-weight: 600;
  line-height: 1.4;
  color: #fff;
}

.carryover-tip {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 20rpx 24rpx;
  margin-top: 20rpx;
  border-radius: 20rpx;
  background: var(--wot-warning-1, #fff7e6);
}

.carryover-tip__text {
  flex: 1;
  font-size: 24rpx;
  line-height: 1.5;
  color: var(--wot-warning-6);
}

.items-card {
  padding: 28rpx 24rpx;
  margin-top: 20rpx;
  background: var(--wot-bg-filled-oppo, #fff);
  border-radius: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
}

.items-card--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 56rpx 24rpx;
}

.items-card__title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--wot-text-main);
}

.items-card__empty-text {
  font-size: 26rpx;
  color: var(--wot-text-auxiliary);
}

.items-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--wot-border-main);
}

.items-row:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.items-row__left {
  flex: 1;
  min-width: 0;
  padding-right: 16rpx;
}

.items-row__task {
  font-size: 28rpx;
  font-weight: 500;
  line-height: 1.5;
  color: var(--wot-text-main);
}

.items-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: var(--wot-text-auxiliary);
}

.items-row__meta-sep::before {
  margin-right: 8rpx;
  content: '·';
}

.items-row__amounts {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  gap: 4rpx;
}

.items-row__payable {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--wot-text-main);
}

.items-row__paid {
  font-size: 22rpx;
  color: var(--wot-text-auxiliary);
}
</style>
