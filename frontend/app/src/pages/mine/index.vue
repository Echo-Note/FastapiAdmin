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
    <!-- 用户卡：头像 / 昵称 / 脱敏手机号，右侧设置入口 -->
    <view class="user-info-card mx-3 mb-3 flex items-center gap-4 rounded-3 px-5 py-6">
      <wd-avatar
        size="64px"
        round
        :src="userInfo?.avatar || ''"
        icon="user"
      />
      <view class="min-w-0 flex-1">
        <view class="truncate text-4 text-white font-bold">
          {{ userInfo?.name || t('common.admin') }}
        </view>
        <view class="mine-mobile">
          {{ mobileText }}
        </view>
      </view>
      <view
        class="mine-setting"
        hover-class="mine-setting--pressed"
        @click="navigateTo('setting')"
      >
        <wd-icon name="settings" size="20px" color="rgba(255, 255, 255, 0.9)" />
      </view>
    </view>

    <!-- 收益卡：整卡进收益明细，失败态点击重试 -->
    <view
      class="earnings-card user-info-card mx-3 mb-3"
      hover-class="earnings-card--pressed"
      @click="handleEarningsTap"
    >
      <view v-if="earningsLoading" class="flex items-center justify-center py-6">
        <wd-loading color="rgba(255, 255, 255, 0.9)" />
      </view>

      <view v-else-if="earningsFailed" class="flex flex-col items-center gap-2 py-4">
        <wd-icon name="exclamation-circle" size="24px" color="rgba(255, 255, 255, 0.9)" />
        <text class="earnings-card__failed">
          {{ t('mine.earningsFailed') }}
        </text>
      </view>

      <template v-else>
        <view class="flex items-start justify-between gap-3">
          <view class="min-w-0">
            <view class="earnings-card__label">
              {{ t('mine.monthPayable') }}
            </view>
            <view class="earnings-card__amount">
              ¥{{ monthPayableText }}
            </view>
          </view>
          <text class="earnings-card__link">
            {{ t('mine.earningsDetail') }} ›
          </text>
        </view>

        <view class="earnings-card__footer">
          <text>
            {{ t('mine.allowanceBalance') }}
            <text class="earnings-card__value">
              ¥{{ allowanceText }}
            </text>
          </text>
          <text>
            {{ periodText ? `${periodText} ` : '' }}{{ t('mine.payoutLimit') }}
            <text class="earnings-card__value">
              ¥{{ payoutLimitText }}
            </text>
          </text>
        </view>
      </template>
    </view>

    <!-- 功能列表：可见性统一由 nav 真值表 + useAccess 决定 -->
    <view class="mx-3 mb-3">
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell
          v-for="entry in entries"
          :key="entry.name"
          center
          is-link
          @click="entry.dialog === 'password' ? openPasswordDialog() : navigateTo(entry.name)"
        >
          <template #title>
            <view class="flex items-center gap-2.5">
              <view
                class="h-8 w-8 flex shrink-0 items-center justify-center rounded-lg"
                :class="NAV_TONE_STYLE[entry.tone].soft"
              >
                <wd-icon :name="entry.icon" size="16px" :color="NAV_TONE_STYLE[entry.tone].color" />
              </view>
              <text>{{ t(entry.titleKey) }}</text>
            </view>
          </template>
        </wd-cell>
      </wd-cell-group>
    </view>

    <!-- 超管专属：全部功能 -->
    <view v-if="isSuperuser" class="mx-3 mb-3">
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell
          :title="t('mine.allFeatures')"
          :label="t('mine.allFeaturesTip')"
          is-link
          @click="navigateTo('work')"
        />
      </wd-cell-group>
    </view>

    <!-- 退出登录 -->
    <view class="mx-3">
      <wd-button type="danger" size="large" plain round block @click="handleLogout">
        {{ t('mine.logout') }}
      </wd-button>
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
.mine-mobile {
  margin-top: 8rpx;
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.75);
  font-variant-numeric: tabular-nums;
}

.mine-setting {
  position: relative;
  z-index: 10;
  width: 72rpx;
  height: 72rpx;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 9999rpx;
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.7;
  }
}

/* 收益卡：复用 user-info-card 的品牌渐变，金额作为主视觉 */
.earnings-card {
  padding: 32rpx;
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.8;
  }

  &__failed {
    font-size: 26rpx;
    color: rgba(255, 255, 255, 0.85);
  }

  &__label {
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.8);
  }

  &__amount {
    margin-top: 8rpx;
    font-size: 60rpx;
    font-weight: 700;
    line-height: 1.1;
    color: rgba(255, 255, 255, 1);
    /* 金额按位数对齐，切换周期时不跳动 */
    font-variant-numeric: tabular-nums;
  }

  &__link {
    flex-shrink: 0;
    font-size: 24rpx;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
  }

  &__footer {
    display: flex;
    flex-wrap: wrap;
    gap: 8rpx 24rpx;
    margin-top: 24rpx;
    padding-top: 20rpx;
    border-top: 1rpx solid rgba(255, 255, 255, 0.2);
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.85);
  }

  &__value {
    font-weight: 600;
    color: rgba(255, 255, 255, 1);
    font-variant-numeric: tabular-nums;
  }
}
</style>
