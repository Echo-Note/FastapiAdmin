<script setup lang="ts">
import type { QuotaSummary } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'

definePage({ name: 'market-my-earnings', style: { navigationBarTitleText: '我的额度' } })

const { t } = useI18n()
const toast = useToast()

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const period = ref(currentMonth())
const quota = ref<QuotaSummary | null>(null)
const loading = ref(false)

const quotaAmountText = computed(() => {
  if (quota.value?.quota_amount === null || quota.value?.quota_amount === undefined)
    return t('market.noLimit')
  return `¥${Number(quota.value.quota_amount).toFixed(2)}`
})

const overAmount = computed(() => Number(quota.value?.over_amount ?? 0))

function shiftMonth(delta: number) {
  const [y, m] = period.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  period.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  loadQuota()
}

async function loadQuota() {
  loading.value = true
  try {
    quota.value = await MarketAPI.getMyQuota(period.value)
  }
  catch {
    quota.value = null
    toast.error(t('common.loadFailed'))
  }
  finally {
    loading.value = false
  }
}

onLoad(() => loadQuota())
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

      <!-- 额度概览 -->
      <view class="mt-3 rounded-2 bg-white p-4">
        <wd-loading v-if="loading" class="my-4 block" />
        <template v-else-if="quota">
          <view class="flex items-baseline justify-between">
            <wd-text class="wot-text-text-auxiliary text-3" :text="t('market.quotaAmount')" />
            <wd-text class="wot-text-text-main text-5 font-semibold" :text="quotaAmountText" />
          </view>
          <wd-cell-group border custom-class="mt-2!">
            <wd-cell :title="t('market.receivedAmount')" :value="`¥${Number(quota.received_amount ?? 0).toFixed(2)}`" />
            <wd-cell :title="t('market.payableAmount')" :value="`¥${Number(quota.payable_amount ?? 0).toFixed(2)}`" />
            <wd-cell :title="t('market.overAmount')" :value="`¥${overAmount.toFixed(2)}`" :value-class="overAmount > 0 ? 'wot-text-error-main!' : ''" />
          </wd-cell-group>
        </template>
        <wd-empty v-else :tip="t('common.loadFailed')" />
      </view>

      <!-- 顺延明细 -->
      <view v-if="quota && (quota.carryover_items ?? []).length > 0" class="mt-3 rounded-2 bg-white p-4">
        <wd-text class="wot-text-text-main text-4 font-medium" :text="t('market.carryover')" />
        <wd-cell-group border custom-class="mt-2!">
          <wd-cell
            v-for="item in quota.carryover_items"
            :key="item.id"
            :title="`${item.from_period ?? '-'} → ${item.to_period ?? '-'}`"
            :value="`¥${Number(item.amount ?? 0).toFixed(2)}`"
          />
        </wd-cell-group>
      </view>

      <wd-gap height="100rpx" safe-area-bottom />
    </view>
  </view>
</template>
