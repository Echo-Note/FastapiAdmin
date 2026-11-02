<script setup lang="ts">
import type { TaskItem } from '@/api/module_market'
import type { NoticeItem } from '@/api/module_system/notice'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { NoticeAPI } from '@/api/module_system/notice'
import { useShare } from '@/composables/useShare'
import { useTabbarActive } from '@/composables/useTabbarActive'
import { taskDisplayName } from '@/constants'
import { CommonUtil } from '@/utils/common'

definePage({
  name: 'market-task-hall',
  type: 'home',
  layout: 'tabbar',
  style: {
    navigationStyle: 'custom',
    navigationBarTitleText: '任务大厅',
    enablePullDownRefresh: true,
  },
})

const { t } = useI18n()
const router = useRouter()

useShare(() => ({ title: t('hall.shareTitle'), path: '/pages/market/task-hall/index' }))
useTabbarActive('pages/market/task-hall/index', 'market-task-hall')

/** 大厅容量：后端 page_size 上限 100，公开任务量级很小，一次取全再本地筛选 */
const HALL_PAGE_SIZE = 100

const tasks = ref<TaskItem[]>([])
const total = ref(0)
const loading = ref(false)
const failed = ref(false)
const keyword = ref('')
const projectFilter = ref('')
const notice = ref<NoticeItem | null>(null)

/** 项目筛选选项：直接由已加载的任务派生，避免为筛选项再发一次请求 */
const projectOptions = computed(() => {
  const names = new Set<string>()
  for (const task of tasks.value) {
    if (task.project?.name)
      names.add(task.project.name)
  }
  return [{ value: '', label: t('hall.filterAll') }, ...[...names].map(name => ({ value: name, label: name }))]
})

/** 本地筛选：任务名/编号/项目名命中，项目筛选为硬过滤 */
const filteredTasks = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return tasks.value.filter((task) => {
    if (projectFilter.value && task.project?.name !== projectFilter.value)
      return false
    if (!kw)
      return true
    const haystack = [taskDisplayName(task), task.task_no, task.project?.name, task.template?.name]
    return haystack.some(text => (text ?? '').toLowerCase().includes(kw))
  })
})

/** 有任务但被筛空：空态要说清是「没任务」还是「没搜到」 */
const isFilteredOut = computed(() => tasks.value.length > 0 && filteredTasks.value.length === 0)

/** 归属链路：项目 → 分类 → 模板，让用户知道这条任务来自哪一单业务 */
function pathText(task: TaskItem) {
  return [task.project?.name, task.template?.category?.name, task.template?.name].filter(Boolean).join(' · ')
}

/** 金额与单位取自三级任务配置，缺失时回退模板配置 */
function priceOf(task: TaskItem) {
  return task.item?.config?.price ?? task.template?.config?.price ?? null
}

function unitOf(task: TaskItem) {
  return task.item?.config?.unit ?? task.template?.config?.unit ?? ''
}

function priceText(task: TaskItem) {
  const price = priceOf(task)
  return price == null ? '面议' : `¥${CommonUtil.formatMoney(price)}`
}

function unitText(task: TaskItem) {
  const unit = unitOf(task)
  return unit ? `/${unit}` : ''
}

/** 截止语义：`task.period` 是截止日期，换算成剩余天数；无日期则不假造倒计时 */
function deadlineInfo(task: TaskItem) {
  if (!task.period)
    return null
  const end = new Date(String(task.period).replace(/-/g, '/')).getTime()
  if (Number.isNaN(end))
    return null
  const days = Math.ceil((end - Date.now()) / 86_400_000)
  if (days < 0)
    return { days, text: t('hall.deadlinePassed'), urgent: true }
  if (days === 0)
    return { days, text: t('hall.deadlineToday'), urgent: true }
  return { days, text: t('hall.deadlineDays', { days }), urgent: days <= 3 }
}

async function loadNotices() {
  try {
    const list = await NoticeAPI.getAvailable(1)
    notice.value = list?.[0] ?? null
  }
  catch {
    // 公告失败不影响接单主流程，静默降级
    notice.value = null
  }
}

async function loadTasks() {
  loading.value = true
  failed.value = false
  try {
    const res = await MarketAPI.getTaskHall({ page_no: 1, page_size: HALL_PAGE_SIZE })
    tasks.value = res.items ?? []
    total.value = res.total ?? 0
  }
  catch {
    failed.value = true
  }
  finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

function goDetail(task: TaskItem) {
  if (!task.id)
    return
  router.push({ name: 'market-task-detail', query: { id: String(task.id) } })
}

function goNotices() {
  router.push({ name: 'work-notices' })
}

onLoad(() => {
  loadTasks()
  loadNotices()
})

onPullDownRefresh(() => {
  loadTasks()
  loadNotices()
})
</script>

<template>
  <view class="tabbar-wraper custom-nav">
    <!-- 平台公告：C 端唯一的运营触达渠道，只展示最新一条 -->
    <view v-if="notice" class="mx-3 mt-3" @click="goNotices">
      <wd-notice-bar
        :text="notice.notice_title || ''"
        prefix="notification"
        type="info"
        closable
        custom-class="hall-notice"
      />
    </view>

    <!-- 搜索 + 项目筛选 -->
    <view class="mx-3 mt-3">
      <wd-search
        v-model="keyword"
        :placeholder="t('hall.searchPlaceholder')"
        variant="light"
        hide-cancel
        custom-class="hall-search"
      />
      <scroll-view scroll-x class="mt-2 whitespace-nowrap" :show-scrollbar="false">
        <view class="flex items-center gap-2">
          <view
            v-for="item in projectOptions"
            :key="item.value"
            class="hall-filter"
            :class="{ 'hall-filter--active': projectFilter === item.value }"
            @click="projectFilter = item.value"
          >
            {{ item.label }}
          </view>
          <text class="wot-text-text-auxiliary ml-1 text-2.5">
            {{ t('hall.count', { count: filteredTasks.length }) }}
          </text>
        </view>
      </scroll-view>
    </view>

    <SkeletonPage v-if="loading && tasks.length === 0" :rows="4" class="mt-3" />

    <!-- 失败态：明确说清是「加载失败」并给重试，不能退化成「暂无任务」 -->
    <view v-else-if="failed" class="mx-3 mt-8 flex flex-col items-center gap-3">
      <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
      <wd-text :text="t('common.loadFailed')" class="wot-text-text-secondary text-3" />
      <wd-button size="small" round @click="loadTasks">
        {{ t('common.retry') }}
      </wd-button>
    </view>

    <view v-else-if="tasks.length === 0" class="mx-3 mt-8">
      <wd-empty :tip="t('market.emptyTaskHall')" />
    </view>

    <view v-else-if="isFilteredOut" class="mx-3 mt-8">
      <wd-empty :tip="t('hall.emptySearch')" />
    </view>

    <view v-else class="mx-3 mt-3 flex flex-col gap-3">
      <view
        v-for="task in filteredTasks"
        :key="task.id"
        class="task-card"
        hover-class="task-card--pressed"
        @click="goDetail(task)"
      >
        <view class="flex items-start gap-3">
          <view class="min-w-0 flex-1">
            <view class="task-card__name">
              {{ taskDisplayName(task) }}
            </view>
            <view v-if="pathText(task)" class="task-card__no">
              {{ pathText(task) }}
            </view>
          </view>
          <view class="shrink-0 text-right">
            <view class="task-card__price">
              {{ priceText(task) }}
            </view>
            <view v-if="unitText(task)" class="task-card__unit">
              {{ unitText(task) }}
            </view>
          </view>
        </view>

        <view class="task-card__footer">
          <view class="min-w-0 flex items-center gap-1.5">
            <text
              v-if="deadlineInfo(task)"
              class="hall-chip"
              :class="deadlineInfo(task)?.urgent ? 'hall-chip--urgent' : 'hall-chip--calm'"
            >
              {{ deadlineInfo(task)?.text }}
            </text>
            <text v-if="(task.assignment_count ?? 0) > 0" class="hall-chip hall-chip--calm">
              {{ t('hall.joined', { count: task.assignment_count }) }}
            </text>
          </view>
          <text class="task-card__link">
            {{ t('hall.view') }} ›
          </text>
        </view>
      </view>
    </view>

    <view v-if="!loading && !failed && total > tasks.length" class="mx-3 my-3">
      <wd-text
        :text="t('hall.truncated', { count: tasks.length })"
        class="wot-text-text-auxiliary block text-center text-2.5"
      />
    </view>

    <wd-gap height="40rpx" />
  </view>
</template>

<style lang="scss" scoped>
/* 列表卡片：单一表面 + 内部细线分层，不用描边卡片堆叠 */
.task-card {
  padding: 28rpx 28rpx 20rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.72;
  }

  &__name {
    font-size: 32rpx;
    font-weight: 600;
    line-height: 1.35;
    color: var(--wot-text-main);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__no {
    margin-top: 6rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__price {
    font-size: 38rpx;
    font-weight: 700;
    line-height: 1.2;
    color: var(--wot-danger-main);
    /* 金额按位数对齐，多条任务纵向比较时不跳动 */
    font-variant-numeric: tabular-nums;
  }

  &__unit {
    margin-top: 4rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
  }

  &__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16rpx;
    margin-top: 20rpx;
    padding-top: 16rpx;
    border-top: 1rpx solid var(--wot-border-light);
  }

  &__link {
    flex-shrink: 0;
    font-size: 24rpx;
    font-weight: 500;
    color: var(--wot-primary-6);
  }
}

/* wd-search 的 light 变体自带整块浅底（宽屏下会变成一条白色横带），
   这里把它还原成透明容器 + 白色胶囊，让头部只留一个视觉块 */
:deep(.hall-search) {
  padding: 0;
  background: transparent;
}

:deep(.hall-search .wd-search__block) {
  background: var(--wot-filled-oppo);
  box-shadow: 0 4rpx 16rpx rgba(28, 100, 253, 0.08);
}

/* 项目筛选 chip：横向滚动，项目多时不挤压 */
.hall-filter {
  display: inline-block;
  padding: 10rpx 26rpx;
  border-radius: 9999rpx;
  font-size: 24rpx;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-oppo);
  border: 1rpx solid var(--wot-border-light);

  &--active {
    color: #fff;
    font-weight: 600;
    background: var(--wot-primary-6);
    border-color: var(--wot-primary-6);
  }
}

/* 状态标签：文案本身写明语义，颜色只是强调 */
.hall-chip {
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
}
</style>
