<script setup lang="ts">
import type { PayoutSummary } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'

definePage({ name: 'market-my-earnings', style: { navigationBarTitleText: '我的发放' } })

const { t } = useI18n()
const toast = useToast()

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const period = ref(currentMonth())
const payout = ref<PayoutSummary | null>(null)
const loading = ref(false)

const payoutLimitText = computed(() => {
  if (payout.value?.payout_limit === null || payout.value?.payout_limit === undefined)
    return t('market.noLimit')
  return `¥${Number(payout.value.payout_limit).toFixed(2)}`
})

const allowanceBalance = computed(() => Number(payout.value?.allowance_balance ?? 0))

function allowanceStatusText(status?: string) {
  return status === 'PAID' ? '已发放' : '待发放'
}

function shiftMonth(delta: number) {
  const [y, m] = period.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  period.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  loadPayout()
}

async function loadPayout() {
  loading.value = true
  try {
    payout.value = await MarketAPI.getMyPayout(period.value)
  }
  catch {
    payout.value = null
    toast.error(t('common.loadFailed'))
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
      <view class="flex items-center justify-center gap-4 rounded-2 bg-white p-3">
        <view class="px-2 py-1" @click="shiftMonth(-1)">
          <wd-icon name="arrow-left" size="18px" />
        </view>
        <wd-text class="text-4 font-medium" :text="period" />
        <view class="px-2 py-1" @click="shiftMonth(1)">
          <wd-icon name="arrow-right" size="18px" />
        </view>
      </view>

      <!-- 发放概览 -->
      <view class="mt-3 rounded-2 bg-white p-4">
        <wd-loading v-if="loading" class="my-4 block" />
        <template v-else-if="payout">
          <view class="flex items-baseline justify-between">
            <wd-text class="wot-text-text-auxiliary text-3" :text="t('market.payoutLimit')" />
            <wd-text class="wot-text-text-main text-5 font-semibold" :text="payoutLimitText" />
          </view>
          <wd-cell-group border custom-class="mt-2!">
            <wd-cell :title="t('market.allowanceBalance')" :value="`¥${allowanceBalance.toFixed(2)}`" :value-class="allowanceBalance > 0 ? 'wot-text-error-main!' : ''" />
          </wd-cell-group>
        </template>
        <wd-empty v-else :tip="t('common.loadFailed')" />
      </view>

      <!-- 津贴明细 -->
      <view v-if="payout && (payout.allowance_items ?? []).length > 0" class="mt-3 rounded-2 bg-white p-4">
        <wd-text class="wot-text-text-main text-4 font-medium" :text="t('market.allowanceItems')" />
        <wd-cell-group border custom-class="mt-2!">
          <wd-cell
            v-for="item in payout.allowance_items"
            :key="item.id"
            :title="item.from_period ?? '-'"
            :value="`¥${Number(item.amount ?? 0).toFixed(2)}`"
            :label="allowanceStatusText(item.status)"
          />
        </wd-cell-group>
      </view>

      <wd-gap height="100rpx" safe-area-bottom />
    </view>
  </view>
</template>
