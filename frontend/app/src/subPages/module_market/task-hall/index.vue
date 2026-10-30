<script setup lang="ts">
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MiniTaskGroup, TaskItem } from '@/api/module_market'
import { MarketAPI } from '@/api/module_market'
import { taskDisplayName } from '@/constants'

definePage({ name: 'market-task-hall', style: { navigationBarTitleText: '任务大厅', enablePullDownRefresh: true } })

/** 分配方式本地映射（direct 定向分派 / open 公开大厅） */
const ASSIGN_MODE_LABEL: Record<string, string> = {
  direct: '定向分派',
  open: '公开大厅',
}

/** 执行要求行前缀文案（C 端固定中文，未新增 i18n key，避免改动语言包文件） */
const EXECUTOR_REQUIREMENT_LABEL = '执行要求'

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

/** 按项目分组的任务组（分组接口不分页，一次性返回全部可见任务） */
const groups = ref<MiniTaskGroup[]>([])
const loading = ref(false)

/** 是否存在可见任务：后端按项目分组，正常情况下空组不会下发，此处兜底判断组内任务 */
const isEmpty = computed(() => groups.value.every(g => (g.tasks?.length ?? 0) === 0))

/** 拉取任务大厅分组数据；错误统一 toast，结束态复位下拉刷新 */
async function loadGroups() {
  loading.value = true
  try {
    groups.value = await MarketAPI.getTaskHallGrouped()
  }
  catch {
    toast.error(t('common.loadFailed'))
  }
  finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

/** 分组唯一 key：优先项目 id，缺省回退下标（防自增 id 缺失导致 key 撞车） */
function groupKey(group: MiniTaskGroup, index: number) {
  return group.project_id != null ? `p-${group.project_id}` : `g-${index}`
}

/** 分组头项目名：分组字段优先，回退组内首个任务的项目摘要名 */
function groupName(group: MiniTaskGroup) {
  return group.project_name?.trim() || group.tasks?.[0]?.project?.name?.trim() || '-'
}

/** 任务显示名：优先三级任务名，叶子模板任务回退模板名 */
function titleText(item: TaskItem) {
  return taskDisplayName(item)
}

/** 归属链路标签：一级分类名 · 二级模板名（有值才展示） */
function pathText(item: TaskItem) {
  const category = item.template?.category?.name?.trim()
  const template = item.template?.name?.trim()
  if (category && template)
    return `${category} · ${template}`
  return category || template || ''
}

/** 执行要求（后端已扁平透出，去空白后展示） */
function execRequirementText(item: TaskItem) {
  return item.executor_requirement?.trim() ?? ''
}

/** 单价（优先三级任务 config.price，回退模板 config.price，仅数字） */
function amountText(item: TaskItem) {
  const price = item.item?.config?.price ?? item.template?.config?.price
  return price == null ? '' : Number(price).toFixed(2)
}

/** 计价单位（优先三级任务 config.unit，回退模板 config.unit） */
function unitText(item: TaskItem) {
  return item.item?.config?.unit ?? item.template?.config?.unit ?? ''
}

/** 分配方式文案 */
function assignModeText(item: TaskItem) {
  return ASSIGN_MODE_LABEL[item.assign_mode ?? ''] ?? item.assign_mode ?? '—'
}

/** 卡片点击统一跳任务详情页（详情页内完成接单） */
function goDetail(item: TaskItem) {
  // 用 path 而非 name 跳转：@wot-ui/router 的 resolve 在 name 分支误把 to.params 当 query，
  // 导致 query 丢失；传 path 走 resolvePath 分支才能正确带上 query。
  router.push({
    path: '/subPages/module_market/task-detail/index',
    query: { task_id: String(item.id) },
  })
}

onPullDownRefresh(async () => {
  await loadGroups()
})
// 每次显示都刷新：从任务详情领取返回后，任务已下架，需重新拉取大厅列表
onShow(() => loadGroups())
</script>

<template>
  <view class="page-wraper">
    <SkeletonPage v-if="loading && groups.length === 0" :rows="5" search />
    <template v-else>
      <view class="px-3 pt-3">
        <wd-empty v-if="!loading && isEmpty" :tip="t('market.emptyTaskHall')" />
        <view
          v-for="(group, index) in groups"
          :key="groupKey(group, index)"
          class="hall-group"
        >
          <view class="hall-group__head">
            <view class="hall-group__title">
              <view class="hall-group__dot" />
              <view class="hall-group__name">
                {{ groupName(group) }}
              </view>
            </view>
            <view v-if="group.period" class="hall-group__period">
              {{ t('market.period') }} {{ group.period }}
            </view>
          </view>
          <view
            v-for="(task, taskIndex) in group.tasks ?? []"
            :key="task.id ?? taskIndex"
            class="hall-card"
            hover-class="hall-card--active"
            @click="goDetail(task)"
          >
            <view class="hall-card__bar" />
            <view class="hall-card__body">
              <view class="hall-card__title">
                {{ titleText(task) }}
              </view>
              <view v-if="pathText(task)" class="hall-card__path">
                {{ pathText(task) }}
              </view>
              <view class="mt-2 flex flex-wrap items-center gap-2">
                <view class="hall-card__meta">
                  {{ t('market.period') }} {{ task.period ?? '-' }}
                </view>
                <view class="hall-card__meta">
                  {{ assignModeText(task) }}
                </view>
              </view>
              <view v-if="execRequirementText(task)" class="hall-card__requirement">
                <text class="hall-card__requirement-label">
                  {{ EXECUTOR_REQUIREMENT_LABEL }}
                </text>
                <text>{{ execRequirementText(task) }}</text>
              </view>
            </view>
            <view class="hall-card__price">
              <view class="hall-card__amount">
                <text class="text-3">
                  ¥
                </text>{{ amountText(task) || '—' }}
              </view>
              <view v-if="unitText(task)" class="hall-card__unit">
                / {{ unitText(task) }}
              </view>
            </view>
          </view>
        </view>
      </view>
      <wd-gap height="100rpx" safe-area-bottom />
    </template>
  </view>
</template>

<style lang="scss" scoped>
/* 项目分组头：品牌蓝圆点 + 项目名主文本 + 周期弱文本，保持清晰信息层级 */
.hall-group {
  margin-bottom: 8rpx;
}

.hall-group__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 4rpx 4rpx 16rpx;
}

.hall-group__title {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
}

.hall-group__dot {
  width: 12rpx;
  height: 12rpx;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--wot-primary-6);
}

.hall-group__name {
  min-width: 0;
  overflow: hidden;
  font-size: 30rpx;
  font-weight: 600;
  line-height: 1.3;
  color: var(--wot-text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hall-group__period {
  flex-shrink: 0;
  font-size: 22rpx;
  line-height: 1.4;
  color: var(--wot-text-secondary);
}

.hall-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 28rpx 24rpx 28rpx 20rpx;
  margin-bottom: 20rpx;
  background: var(--wot-bg-filled-oppo, #fff);
  border-radius: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
  transition: transform 0.15s ease;
}

.hall-card--active {
  transform: scale(0.98);
}

.hall-card__bar {
  width: 8rpx;
  height: 72rpx;
  flex-shrink: 0;
  border-radius: 8rpx;
  background: linear-gradient(180deg, var(--wot-primary-6), var(--wot-primary-4));
}

.hall-card__body {
  flex: 1;
  min-width: 0;
}

.hall-card__title {
  overflow: hidden;
  font-size: 32rpx;
  font-weight: 600;
  line-height: 1.35;
  color: var(--wot-text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 归属链路：一级分类 · 二级模板，弱文本小号 */
.hall-card__path {
  margin-top: 6rpx;
  overflow: hidden;
  font-size: 22rpx;
  line-height: 1.4;
  color: var(--wot-text-auxiliary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hall-card__meta {
  padding: 4rpx 14rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content, #f2f3f5);
  border-radius: 8rpx;
}

/* 执行要求：浅色信息条，标签主文本 + 内容弱文本 */
.hall-card__requirement {
  margin-top: 12rpx;
  padding: 12rpx 16rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content, #f2f3f5);
  border-radius: 12rpx;
}

.hall-card__requirement-label {
  margin-right: 8rpx;
  font-weight: 600;
  color: var(--wot-text-main);
}

.hall-card__price {
  flex-shrink: 0;
  text-align: right;
}

.hall-card__amount {
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1.1;
  color: var(--wot-primary-6);
  white-space: nowrap;
}

.hall-card__unit {
  margin-top: 4rpx;
  font-size: 22rpx;
  line-height: 1.4;
  color: var(--wot-text-auxiliary);
}
</style>
