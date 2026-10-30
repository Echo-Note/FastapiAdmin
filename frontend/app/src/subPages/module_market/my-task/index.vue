<script setup lang="ts">
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import type { AssignmentItem, MiniAssignmentGroup } from '@/api/module_market'
import {
  ASSIGNMENT_STAGES,
  ASSIGNMENT_STATUS_MAP,
  ASSIGNMENT_STATUS_STAGE,
  statusMeta,
  SUBMISSION_STAT_META,
  SUBMISSION_STAT_ORDER,
  taskDisplayName,
} from '@/constants'

definePage({ name: 'market-my-task', style: { navigationBarTitleText: '我的任务', enablePullDownRefresh: true } })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

/** 顶部状态筛选 Tab：与后端 AssignmentStatus 六档一致 */
const TAB_OPTIONS = [
  { label: '全部', value: undefined },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'PENDING').label, value: 'PENDING' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'ACCEPTED').label, value: 'ACCEPTED' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'SUBMITTING').label, value: 'SUBMITTING' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'SUBMITTED').label, value: 'SUBMITTED' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'REVIEWED').label, value: 'REVIEWED' },
  { label: statusMeta(ASSIGNMENT_STATUS_MAP, 'SETTLED').label, value: 'SETTLED' },
]
const activeTab = ref(0)
const activeStatus = ref<string | undefined>()

/** 分组数据（分组接口不分页，一次性拉全） */
const groups = ref<MiniAssignmentGroup[]>([])
const loading = ref(false)

/** 按项目分组拉取：首次/全部不传 status，切换 Tab 时传 status 筛选 */
async function loadGroups() {
  loading.value = true
  try {
    const params = activeStatus.value ? { status: activeStatus.value } : undefined
    const data = await MarketAPI.getMyAssignmentsGrouped(params)
    groups.value = data ?? []
  }
  catch {
    toast.error(t('common.loadFailed'))
  }
  finally {
    loading.value = false
  }
}

function statusInfo(status?: string) {
  return statusMeta(ASSIGNMENT_STATUS_MAP, status)
}

/** 状态语义色 → 进度轨道/成果角标语义色 */
const STATUS_BAR_COLOR: Record<string, string> = {
  info: 'var(--wot-grey-6)',
  primary: 'var(--wot-primary-6)',
  warning: 'var(--wot-warning-6)',
  success: 'var(--wot-success-6)',
  danger: 'var(--wot-danger-6)',
}
function barColor(status?: string) {
  return STATUS_BAR_COLOR[statusInfo(status).type] ?? 'var(--wot-grey-6)'
}

/** 成果进度聚合：assignment_id → { APPROVED/PENDING/REJECTED/DRAFT: 数量 } */
const submissionStatMap = ref<Record<number, Record<string, number>>>({})

/**
 * 拉取当前用户全部成果（后端单页上限 100，循环翻页），按分派单聚合各状态数量。
 * 失败静默处理：角标缺失不影响任务主列表展示。
 */
async function loadSubmissionStats() {
  const PAGE_SIZE = 100
  const map: Record<number, Record<string, number>> = {}
  try {
    let page = 1
    for (;;) {
      const res = await MarketAPI.getMySubmissions({ page_no: page, page_size: PAGE_SIZE })
      const items = res?.items ?? []
      for (const s of items) {
        if (s.assignment_id == null)
          continue
        const bucket = (map[s.assignment_id] ??= {})
        const key = s.status ?? 'DRAFT'
        bucket[key] = (bucket[key] ?? 0) + 1
      }
      const total = res?.total ?? 0
      if (items.length < PAGE_SIZE || page * PAGE_SIZE >= total)
        break
      page += 1
    }
  }
  catch {
    // 聚合失败不阻塞列表
  }
  submissionStatMap.value = map
}

/** 某任务已提交成果的进度角标项（仅统计通过/待审/驳回，草稿不计入） */
function statItems(assignmentId?: number) {
  const bucket = assignmentId != null ? submissionStatMap.value[assignmentId] : undefined
  if (!bucket)
    return []
  return SUBMISSION_STAT_ORDER
    .map(key => ({
      key,
      label: SUBMISSION_STAT_META[key].label,
      type: SUBMISSION_STAT_META[key].type,
      count: bucket[key] ?? 0,
    }))
    .filter(s => s.count > 0)
}

/** 分派状态 → 阶段序号（进度轨道高亮到当前阶段） */
function stageIndex(status?: string) {
  return ASSIGNMENT_STATUS_STAGE[status ?? ''] ?? 0
}

/** 分组头唯一 key：优先项目 id，回退项目名，最后回退索引 */
function groupKey(group: MiniAssignmentGroup, index: number) {
  return group.project_id ?? group.project_name ?? `group-${index}`
}

/** 归属路径：一级分类名 · 二级模板名（空段跳过） */
function pathText(item: AssignmentItem) {
  const category = item.task?.template?.category?.name
  const template = item.task?.template?.name
  return [category, template].filter(Boolean).join(' · ')
}

/** 执行要求（后端已扁平透出，空值不展示） */
function executorRequirement(item: AssignmentItem) {
  return item.task?.executor_requirement?.trim() || ''
}

function handleTabChange(e: { index: number }) {
  activeStatus.value = TAB_OPTIONS[e.index]?.value
  loadGroups()
}

/** 卡片点击：已接收 / 进行中 → 提交成果页；其余（待接收/已提交/已审核/已结算）→ 详情页 */
function goDetail(item: AssignmentItem) {
  // 用 path 而非 name 跳转：@wot-ui/router 的 resolve 在 name 分支误把 to.params 当 query，
  // 导致 query 丢失；传 path 走 resolvePath 分支才能正确带上 query。
  const canFill = item.status === 'ACCEPTED' || item.status === 'SUBMITTING'
  const path = canFill
    ? '/subPages/module_market/submission-form/index'
    : '/subPages/module_market/task-detail/index'
  router.push({
    path,
    query: { assignment_id: String(item.id) },
  })
}

onPullDownRefresh(async () => {
  try {
    await Promise.all([loadGroups(), loadSubmissionStats()])
  }
  finally {
    uni.stopPullDownRefresh()
  }
})
// 每次显示都刷新：从详情接收返回后状态已变，需重新拉取列表与成果统计
onShow(() => {
  loadGroups()
  loadSubmissionStats()
})
</script>

<template>
  <view class="page-wraper">
    <wd-tabs v-model="activeTab" line-theme="text" sticky :offset-top="0" @change="handleTabChange">
      <wd-tab v-for="opt in TAB_OPTIONS" :key="opt.label" :title="opt.label" />
    </wd-tabs>

    <SkeletonPage v-if="loading && groups.length === 0" :rows="5" search />
    <template v-else>
      <view class="px-3 pt-3">
        <wd-empty v-if="!loading && groups.length === 0" :tip="t('market.emptyMyTask')" />
        <template v-for="(group, gi) in groups" :key="groupKey(group, gi)">
          <!-- 分组头：项目名主文本 + 周期弱文本 -->
          <view class="group-head">
            <view class="group-head__name">
              {{ group.project_name || '-' }}
            </view>
            <view v-if="group.period" class="group-head__period">
              {{ group.period }}
            </view>
          </view>
          <view
            v-for="item in group.assignments ?? []"
            :key="item.id"
            class="my-card"
            hover-class="my-card--active"
            @click="goDetail(item)"
          >
            <view class="flex items-center justify-between gap-2">
              <view class="my-card__title">
                {{ taskDisplayName(item.task) || '-' }}
              </view>
              <wd-tag :type="statusInfo(item.status).type" plain round :icon="statusInfo(item.status).icon">
                {{ statusInfo(item.status).label }}
              </wd-tag>
            </view>
            <!-- 归属链路：一级分类名 · 二级模板名 -->
            <view v-if="pathText(item)" class="my-card__path">
              {{ pathText(item) }}
            </view>
            <view class="mt-2 flex flex-wrap items-center justify-between gap-2">
              <view class="my-card__meta">
                {{ t('market.period') }} {{ item.task?.period ?? '-' }}
              </view>
              <view v-if="statItems(item.id).length" class="sub-stat">
                <text
                  v-for="s in statItems(item.id)"
                  :key="s.key"
                  class="sub-stat__item"
                >
                  <text class="sub-stat__dot" :style="{ background: STATUS_BAR_COLOR[s.type] }" />
                  <text class="sub-stat__num">{{ s.count }}</text>
                  <text class="sub-stat__label">{{ s.label }}</text>
                </text>
              </view>
            </view>
            <!-- 执行要求（有值才展示） -->
            <view v-if="executorRequirement(item)" class="my-card__requirement">
              <text class="my-card__requirement-label">执行要求</text>
              <text>{{ executorRequirement(item) }}</text>
            </view>
            <view class="stage-track mt-3" :style="{ '--track-color': barColor(item.status) }">
              <view
                v-for="(stage, i) in ASSIGNMENT_STAGES"
                :key="stage.label"
                class="stage-col"
              >
                <view class="stage-col__row">
                  <view class="stage-col__line stage-col__line--l" :class="{ on: i > 0 && i <= stageIndex(item.status) }" />
                  <view class="stage-col__dot" :class="{ on: i <= stageIndex(item.status) }" />
                  <view class="stage-col__line stage-col__line--r" :class="{ on: i < stageIndex(item.status) }" />
                </view>
                <text class="stage-col__label" :class="{ on: i <= stageIndex(item.status) }">{{ stage.label }}</text>
              </view>
            </view>
          </view>
        </template>
      </view>
      <wd-gap height="100rpx" safe-area-bottom />
    </template>
  </view>
</template>

<style lang="scss" scoped>
/* 分组头：项目名 + 周期 */
.group-head {
  display: flex;
  align-items: baseline;
  gap: 12rpx;
  margin: 8rpx 4rpx 16rpx;
}
.group-head__name {
  min-width: 0;
  overflow: hidden;
  font-size: 28rpx;
  font-weight: 600;
  line-height: 1.4;
  color: var(--wot-text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.group-head__period {
  flex-shrink: 0;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-auxiliary);
}

.my-card {
  padding: 24rpx;
  margin-bottom: 20rpx;
  background: var(--wot-bg-filled-oppo, #fff);
  border-radius: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
  transition: transform 0.15s ease;
}

.my-card--active {
  transform: scale(0.98);
}

.my-card__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 32rpx;
  font-weight: 600;
  line-height: 1.35;
  color: var(--wot-text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-card__path {
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-auxiliary);
}

.my-card__meta {
  padding: 4rpx 14rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content, #f2f3f5);
  border-radius: 8rpx;
}

.my-card__requirement {
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: var(--wot-text-secondary);
}
.my-card__requirement-label {
  margin-right: 8rpx;
  font-size: 20rpx;
  color: var(--wot-primary-6);
}

/* 成果进度角标：通过 / 待审 / 驳回 分组计数 */
.sub-stat {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16rpx;
}
.sub-stat__item {
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  font-size: 22rpx;
  line-height: 1.4;
}
.sub-stat__dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  flex-shrink: 0;
}
.sub-stat__num {
  font-weight: 600;
  color: var(--wot-text-main);
}
.sub-stat__label {
  color: var(--wot-text-secondary);
}

/* 四阶段进度轨道：接收 → 提交 → 审核 → 结算 */
.stage-track {
  display: flex;
}
.stage-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
}
.stage-col:first-child .stage-col__line--l,
.stage-col:last-child .stage-col__line--r {
  opacity: 0;
}
.stage-col__row {
  display: flex;
  align-items: center;
  width: 100%;
}
.stage-col__line {
  flex: 1;
  height: 4rpx;
  border-radius: 2rpx;
  background: var(--wot-grey-4, #e5e6eb);
}
.stage-col__line.on {
  background: var(--track-color, var(--wot-primary-6));
}
.stage-col__dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: var(--wot-grey-4, #e5e6eb);
  flex-shrink: 0;
  transition: background 0.2s ease;
}
.stage-col__dot.on {
  background: var(--track-color, var(--wot-primary-6));
}
.stage-col__label {
  margin-top: 8rpx;
  font-size: 20rpx;
  line-height: 1;
  color: var(--wot-text-auxiliary);
}
.stage-col__label.on {
  color: var(--track-color, var(--wot-primary-6));
}
</style>
