<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAccess } from '@/composables/useAccess'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useShare } from '@/composables/useShare'
import { ALL_FEATURES_GROUPS, NAV_TONE_STYLE } from '@/constants/nav'
import { useUserStore } from '@/store/userStore'

const { t } = useI18n()

useShare({
  title: t('work.shareTitle'),
  path: '/pages/work/index',
})

definePage({
  name: 'work',
  layout: 'default',
  style: { navigationBarTitleText: '全部功能' },
})
useI18nNavTitle('work.navTitle')

const router = useRouter()
const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo)
const { visibleGroups } = useAccess()

function navigateTo(name: string) {
  router.push({ name })
}

/** 分组与条目全部来自 constants/nav 真值表，按权限过滤后渲染 */
const groups = computed(() => visibleGroups(ALL_FEATURES_GROUPS))

/** 搜索关键词，本地过滤功能标题（分组被筛空则整组隐藏） */
const keyword = ref('')
const filteredGroups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw)
    return groups.value
  return groups.value
    .map(group => ({ ...group, items: group.items.filter(item => t(item.titleKey).toLowerCase().includes(kw)) }))
    .filter(group => group.items.length > 0)
})
</script>

<template>
  <view class="page-wraper py-3">
    <!-- 用户信息卡（品牌渐变 + 极光装饰圆环） -->
    <view class="user-info-card mx-3 mb-4 flex items-center gap-4 rounded-3 px-5 py-6">
      <wd-avatar
        size="64px"
        round
        :src="userInfo?.avatar || ''"
        icon="user"
      />
      <view class="min-w-0 flex-1">
        <view class="text-4 text-white font-bold">
          {{ userInfo?.name || t('work.nameFallback') }}
        </view>
        <view class="mt-1 truncate text-3" style="color: rgba(255, 255, 255, 0.75);">
          {{ userInfo?.roles?.map(r => r.name).join(', ') || t('work.roleFallback') }}
        </view>
      </view>
    </view>

    <!-- 功能搜索 + 可见范围说明 -->
    <view class="mx-3 mb-4">
      <wd-search v-model="keyword" :placeholder="t('work.searchPlaceholder')" variant="light" hide-cancel />
      <view class="wot-text-text-auxiliary mt-2 px-1 text-2.5">
        {{ t('work.superuserOnly') }}
      </view>
    </view>

    <!-- 功能分组（数据驱动，入口可见性由真值表决定） -->
    <view v-for="group in filteredGroups" :key="group.titleKey" class="mb-4">
      <view class="mb-2 mt-1 flex items-center gap-2 px-3">
        <view class="h-3.5 w-1 rounded-full" :style="{ backgroundColor: NAV_TONE_STYLE[group.tone].color }" />
        <wd-text class="wot-text-text-main text-3.5" :text="t(group.titleKey)" bold />
        <wd-text class="wot-text-text-auxiliary text-2.5" :text="group.items.length" />
      </view>
      <wd-cell-group border custom-class="mx-3 rounded-2! overflow-hidden">
        <wd-cell
          v-for="item in group.items"
          :key="item.name"
          center
          is-link
          @click="navigateTo(item.name)"
        >
          <template #title>
            <view class="flex items-center gap-2.5">
              <view
                class="h-8 w-8 flex shrink-0 items-center justify-center rounded-lg"
                :class="NAV_TONE_STYLE[item.tone].soft"
              >
                <wd-icon :name="item.icon" size="16px" :color="NAV_TONE_STYLE[item.tone].color" />
              </view>
              <text>
                {{ t(item.titleKey) }}
              </text>
            </view>
          </template>
        </wd-cell>
      </wd-cell-group>
    </view>

    <!-- 搜索无结果 -->
    <wd-empty v-if="filteredGroups.length === 0" :tip="t('work.emptyTip')" />
  </view>
</template>
