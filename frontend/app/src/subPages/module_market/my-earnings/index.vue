<script setup lang="ts">
import type { PayoutSummary } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { ALLOWANCE_STATUS_MAP, statusMeta } from '@/constants'

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

const payoutLimitText = computed(() => {
  if (payout.value?.payout_limit === null || payout.value?.payout_limit === undefined)
    return t('market.noLimit')
  return `¥${Number(payout.value.payout_limit).toFixed(2)}`
})

const allowanceBalance = computed(() => Number(payout.value?.allowance_balance ?? 0))

function allowanceStatusInfo(status?: string) {
  return statusMeta(ALLOWANCE_STATUS_MAP, status)
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
      <!-- 周期切换 -->
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

      <!-- 发放概览：品牌渐变卡 -->
      <view class="earn-hero">
        <wd-loading v-if="loading" class="my-4 block" color="#fff" />
        <template v-else-if="payout">
          <view class="earn-hero__label">
            {{ t('market.payoutLimit') }}
          </view>
          <view class="earn-hero__value">
            {{ payoutLimitText }}
          </view>
          <view class="earn-hero__divider" />
          <view class="flex items-center justify-between">
            <text class="earn-hero__label">
              {{ t('market.allowanceBalance') }}
            </text>
            <text class="earn-hero__balance">
              ¥{{ allowanceBalance.toFixed(2) }}
            </text>
          </view>
        </template>
        <template v-else>
          <view class="flex flex-col items-center py-6">
            <view class="text-3" style="color: rgba(255,255,255,0.9)">
              {{ loadFailed ? t('common.loadFailed') : t('market.allowanceBalance') }}
            </view>
            <wd-button v-if="loadFailed" type="primary" size="small" class="mt-4" @click="loadPayout">
              {{ t('common.retry') }}
            </wd-button>
          </view>
        </template>
      </view>

      <!-- 津贴顺延提示 -->
      <view v-if="payout && allowanceBalance > 0" class="carryover-tip">
        <wd-icon name="warn-bold" size="16px" custom-class="wot-text-warning-main" />
        <text class="carryover-tip__text">
          {{ t('market.allowanceCarryover') }}
        </text>
      </view>

      <!-- 津贴明细 -->
      <view v-if="payout && (payout.allowance_items ?? []).length > 0" class="items-card">
        <view class="items-card__title">
          {{ t('market.allowanceItems') }}
        </view>
        <view v-for="item in payout.allowance_items" :key="item.id" class="items-row">
          <view class="items-row__left">
            <view class="items-row__period">
              {{ item.from_period ?? '-' }}
            </view>
            <view class="items-row__status">
              {{ allowanceStatusInfo(item.status).label }}
            </view>
          </view>
          <view
            class="items-row__amount"
            :style="{ color: item.status === 'PAID' ? 'var(--wot-success-6)' : 'var(--wot-warning-6)' }"
          >
            ¥{{ Number(item.amount ?? 0).toFixed(2) }}
          </view>
        </view>
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

.earn-hero__balance {
  font-size: 30rpx;
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

.items-card__title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--wot-text-main);
}

.items-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--wot-border-main);
}

.items-row:last-child {
  border-bottom: none;
}

.items-row__left {
  flex: 1;
  min-width: 0;
}

.items-row__period {
  font-size: 28rpx;
  font-weight: 500;
  color: var(--wot-text-main);
}

.items-row__status {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: var(--wot-text-auxiliary);
}

.items-row__amount {
  flex-shrink: 0;
  margin-left: 16rpx;
  font-size: 30rpx;
  font-weight: 600;
}
</style>
