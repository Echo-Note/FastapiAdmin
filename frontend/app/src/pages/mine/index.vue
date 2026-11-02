<script setup lang="ts">
import type { PayoutSummary } from '@/api/module_market'
import type { PasswordChangeForm } from '@/api/module_system/user'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import UserAPI from '@/api/module_system/user'
import { useAccess } from '@/composables/useAccess'
import { useGlobalDialog } from '@/composables/useGlobalDialog'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { MINE_ENTRIES, NAV_TONE_STYLE } from '@/constants/nav'
import { useUserStore } from '@/store/userStore'

definePage({
  name: 'mine',
  layout: 'tabbar',
  style: { navigationBarTitleText: '我的' },
})
useI18nNavTitle('mine.navTitle')

const { t } = useI18n()
const router = useRouter()
const toast = useToast()

const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo)

useShare(() => ({
  title: t('mine.shareTitle', { name: userInfo.value?.name || t('common.admin') }),
  path: '/pages/market/task-hall/index',
}))

const { isSuperuser, visibleEntries } = useAccess()
const entries = computed(() => visibleEntries(MINE_ENTRIES))
const serviceEntries = computed(() => entries.value.filter(entry => entry.section === 'service'))
const accountEntries = computed(() => entries.value.filter(entry => entry.section !== 'service'))

function navigateTo(name: string) {
  router.push({ name })
}

/** 手机号脱敏：中间四位隐去，未绑定时展示明确文案 */
const mobileText = computed(() => {
  const mobile = (userInfo.value?.mobile || '').trim()
  if (!mobile)
    return t('mine.mobileUnbound')
  return mobile.length >= 7 ? `${mobile.slice(0, 3)}****${mobile.slice(-4)}` : mobile
})

/** 收益汇总：本月应发 / 津贴余额 / 发放额度（同一个 mini/payout 接口，避免为卡片单独开接口） */
const summary = ref<PayoutSummary | null>(null)
const earningsLoading = ref(false)
const earningsFailed = ref(false)

const monthPayableText = computed(() => Number(summary.value?.payable ?? 0).toFixed(2))
const allowanceText = computed(() => Number(summary.value?.allowance_balance ?? 0).toFixed(2))
const payoutLimitText = computed(() => Number(summary.value?.payout_limit ?? 0).toFixed(2))
const periodText = computed(() => summary.value?.period || '')

/** 额度进度：本月应发 / 发放额度；额度为 0 时不画进度（避免除零与假进度） */
const quotaPercent = computed(() => {
  const limit = Number(summary.value?.payout_limit ?? 0)
  if (limit <= 0)
    return 0
  return Math.min(100, Math.round((Number(summary.value?.payable ?? 0) / limit) * 100))
})

/** 收益卡展示当月：后端 payout 需要显式周期，缺省用本机当月 */
function currentPeriod() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

async function loadSummary() {
  earningsLoading.value = true
  earningsFailed.value = false
  try {
    summary.value = await MarketAPI.getMyPayout(currentPeriod())
  }
  catch {
    summary.value = null
    earningsFailed.value = true
  }
  finally {
    earningsLoading.value = false
  }
}

useTabbarActive('pages/mine/index', 'mine', loadSummary)

/** 收益卡整卡可点：失败态点击即重试，正常态进入收益明细 */
function handleEarningsTap() {
  if (earningsLoading.value)
    return
  if (earningsFailed.value) {
    loadSummary()
    return
  }
  router.push({ name: 'market-my-earnings' })
}

const globalDialog = useGlobalDialog()

function handleLogout() {
  globalDialog.confirm({
    title: t('common.title'),
    msg: t('mine.logoutMsg'),
    confirmButtonText: t('mine.logoutConfirm'),
    success: (res) => {
      if (res.action === 'confirm')
        userStore.logout()
    },
  })
}

/** 修改密码弹窗（内嵌于「我的」页，免跳转） */
const showPasswordDialog = ref(false)
const submitting = ref(false)
const passwordForm = reactive<PasswordChangeForm>({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function openPasswordDialog() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  showPasswordDialog.value = true
}

/** 提交修改密码：字段级校验 + 调用后端接口 */
async function handleSubmitPassword() {
  if (!passwordForm.old_password) {
    toast.warning(t('account.oldRequired'))
    return
  }
  if (!passwordForm.new_password) {
    toast.warning(t('common.form.newPasswordRequired'))
    return
  }
  if (passwordForm.new_password.length < 6) {
    toast.warning(t('account.newLength'))
    return
  }
  if (!passwordForm.confirm_password) {
    toast.warning(t('common.form.confirmNewRequired'))
    return
  }
  if (passwordForm.confirm_password !== passwordForm.new_password) {
    toast.warning(t('common.form.mismatch'))
    return
  }

  submitting.value = true
  try {
    await UserAPI.changeCurrentUserPassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
      confirm_password: passwordForm.confirm_password,
    })
    toast.success(t('account.success'))
    showPasswordDialog.value = false
  }
  catch {
    // http 层已统一错误提示
  }
  finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="tabbar-wraper py-3">
    <!-- 身份行：头像 / 昵称 / 脱敏手机号 + 设置入口，不再用整块渐变 -->
    <view class="identity mx-3 mt-3">
      <wd-avatar
        size="52px"
        round
        :src="userInfo?.avatar || ''"
        icon="user"
      />
      <view class="min-w-0 flex-1">
        <view class="identity__name">
          {{ userInfo?.name || t('common.admin') }}
        </view>
        <view class="identity__sub">
          {{ mobileText }} · {{ t('mine.executor') }}
        </view>
      </view>
      <view class="identity__action" hover-class="identity__action--pressed" @click="navigateTo('setting')">
        <wd-icon name="settings" size="20px" color="var(--wot-text-auxiliary)" />
      </view>
    </view>

    <!-- 收益卡：白底 + 大数字 + 额度进度条，整卡进收益明细，失败态点击重试 -->
    <view class="earn mx-3 mt-3" hover-class="earn--pressed" @click="handleEarningsTap">
      <view v-if="earningsLoading" class="flex items-center justify-center py-6">
        <wd-loading />
      </view>

      <view v-else-if="earningsFailed" class="flex flex-col items-center gap-2 py-4">
        <wd-icon name="exclamation-circle" size="24px" color="var(--wot-warning-main)" />
        <text class="earn__failed">
          {{ t('mine.earningsFailed') }}
        </text>
      </view>

      <template v-else>
        <view class="flex items-end justify-between gap-3">
          <view class="min-w-0">
            <view class="earn__label">
              {{ t('mine.monthPayable') }}
              <text v-if="periodText" class="earn__period">
                {{ periodText }}
              </text>
            </view>
            <view class="earn__amount">
              ¥{{ monthPayableText }}
            </view>
          </view>
          <text class="earn__link">
            {{ t('mine.earningsDetail') }} ›
          </text>
        </view>

        <view class="earn__track">
          <view class="earn__fill" :style="{ width: `${quotaPercent}%` }" />
        </view>
        <view class="earn__cap">
          <text>{{ t('mine.payoutLimit') }} ¥{{ payoutLimitText }}</text>
          <text>{{ t('mine.allowanceBalance') }} ¥{{ allowanceText }}</text>
        </view>
      </template>
    </view>

    <!-- 我的服务 -->
    <view v-if="serviceEntries.length > 0" class="mx-3 mt-4">
      <view class="sect">
        {{ t('mine.services') }}
      </view>
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell
          v-for="entry in serviceEntries"
          :key="entry.name"
          center
          is-link
          @click="navigateTo(entry.name)"
        >
          <template #title>
            <view class="flex items-center gap-2.5">
              <view class="h-8 w-8 flex shrink-0 items-center justify-center rounded-lg" :class="NAV_TONE_STYLE[entry.tone].soft">
                <wd-icon :name="entry.icon" size="16px" :color="NAV_TONE_STYLE[entry.tone].color" />
              </view>
              <text>{{ t(entry.titleKey) }}</text>
            </view>
          </template>
        </wd-cell>
      </wd-cell-group>
    </view>

    <!-- 账号 -->
    <view class="mx-3 mt-4">
      <view class="sect">
        {{ t('mine.accountSection') }}
      </view>
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell
          v-for="entry in accountEntries"
          :key="entry.name"
          center
          is-link
          @click="entry.dialog === 'password' ? openPasswordDialog() : navigateTo(entry.name)"
        >
          <template #title>
            <view class="flex items-center gap-2.5">
              <view class="h-8 w-8 flex shrink-0 items-center justify-center rounded-lg" :class="NAV_TONE_STYLE[entry.tone].soft">
                <wd-icon :name="entry.icon" size="16px" :color="NAV_TONE_STYLE[entry.tone].color" />
              </view>
              <text>{{ t(entry.titleKey) }}</text>
            </view>
          </template>
        </wd-cell>
        <!-- 仅超管：全部功能（运营 / 开发） -->
        <wd-cell
          v-if="isSuperuser"
          center
          is-link
          :title="t('mine.allFeatures')"
          :label="t('mine.allFeaturesTip')"
          @click="navigateTo('work')"
        />
      </wd-cell-group>
    </view>

    <!-- 退出登录：弱化为文字行，不做成红色大按钮 -->
    <view class="mx-3 mt-4">
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell center custom-class="justify-center" @click="handleLogout">
          <template #title>
            <view class="logout">
              {{ t('mine.logout') }}
            </view>
          </template>
        </wd-cell>
      </wd-cell-group>
    </view>

    <!-- 修改密码弹窗 -->
    <wd-popup
      v-model="showPasswordDialog"
      position="bottom"
      round
      :z-index="1100"
      custom-style="padding-bottom: env(safe-area-inset-bottom);"
    >
      <view class="px-4 pb-4 pt-4">
        <view class="wot-text-text-main mb-4 text-center text-4 font-bold">
          {{ t('account.password') }}
        </view>
        <wd-input
          v-model="passwordForm.old_password"
          :label="t('account.oldPassword')"
          show-password
          clearable
          :placeholder="t('account.oldPlaceholder')"
        />
        <view class="h-3" />
        <wd-input
          v-model="passwordForm.new_password"
          :label="t('account.newPassword')"
          show-password
          clearable
          :placeholder="t('common.form.newPasswordPlaceholder')"
        />
        <view class="h-3" />
        <wd-input
          v-model="passwordForm.confirm_password"
          :label="t('account.confirmPassword')"
          show-password
          clearable
          :placeholder="t('common.form.confirmNewPlaceholder')"
        />
        <view class="mt-5">
          <wd-button type="primary" size="large" round block :loading="submitting" @click="handleSubmitPassword">
            {{ t('account.submit') }}
          </wd-button>
        </view>
      </view>
      <wd-gap :height="20" />
    </wd-popup>
  </view>
</template>

<style lang="scss" scoped>
/* 身份行：一行搞定，不再用整块渐变卡 */
.identity {
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 8rpx 4rpx 12rpx;

  &__name {
    font-size: 32rpx;
    font-weight: 600;
    color: var(--wot-text-main);
  }

  &__sub {
    margin-top: 6rpx;
    font-size: 24rpx;
    color: var(--wot-text-auxiliary);
    font-variant-numeric: tabular-nums;
  }

  &__action {
    width: 72rpx;
    height: 72rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 9999rpx;
    transition: opacity 0.15s ease;

    &--pressed {
      opacity: 0.7;
    }
  }
}

/* 收益卡：白底 + 大数字 + 额度进度，钱是主视觉但不是唯一元素 */
.earn {
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.8;
  }

  &__failed {
    font-size: 24rpx;
    color: var(--wot-text-secondary);
  }

  &__label {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__period {
    margin-left: 8rpx;
    font-variant-numeric: tabular-nums;
  }

  &__amount {
    margin-top: 6rpx;
    font-size: 56rpx;
    font-weight: 700;
    line-height: 1.1;
    color: var(--wot-danger-main);
    font-variant-numeric: tabular-nums;
  }

  &__link {
    flex-shrink: 0;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__track {
    height: 8rpx;
    margin-top: 22rpx;
    border-radius: 9999rpx;
    background: var(--wot-filled-content);
    overflow: hidden;
  }

  &__fill {
    height: 100%;
    border-radius: 9999rpx;
    background: var(--wot-primary-6);
  }

  &__cap {
    display: flex;
    justify-content: space-between;
    margin-top: 10rpx;
    font-size: 20rpx;
    color: var(--wot-text-auxiliary);
    font-variant-numeric: tabular-nums;
  }
}

/* 分组标题 */
.sect {
  margin: 0 8rpx 12rpx;
  font-size: 24rpx;
  color: var(--wot-text-auxiliary);
}

/* 退出登录：文字行，不用红色大按钮抢视觉 */
.logout {
  width: 100%;
  text-align: center;
  font-size: 28rpx;
  color: var(--wot-text-secondary);
}
</style>
