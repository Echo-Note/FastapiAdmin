<!-- 运营工作台 · 工作台概览：待处理 / 业务流转 / 资料库 三段式 -->
<template>
  <div class="ops-dash">
    <!-- 页面级工具行：面包屑已经标明页名，这里只保留统计口径、更新时间和刷新 -->
    <div class="ops-dash__util">
      <span class="ops-dash__meta">
        全库数据（不含已删除）<template v-if="updatedAt">，更新于 {{ updatedAt }}</template>
      </span>
      <ElButton size="small" text bg :loading="loading" @click="refreshAll">刷新</ElButton>
    </div>

    <!-- 首屏骨架：高度对齐三段真实版式，避免加载完成后的跳动 -->
    <ElSkeleton v-if="!hasLoaded && !loadError" :loading="true" animated>
      <template #template>
        <div class="ops-skeleton">
          <div class="ops-skeleton__band">
            <ElSkeletonItem variant="text" style="width: 64px" />
            <ElSkeletonItem variant="rect" style="height: 98px; margin-top: 10px" />
          </div>
          <div class="ops-skeleton__band">
            <ElSkeletonItem variant="text" style="width: 64px" />
            <ElSkeletonItem variant="rect" style="height: 226px; margin-top: 10px" />
          </div>
          <div class="ops-skeleton__band">
            <ElSkeletonItem variant="text" style="width: 64px" />
            <ElSkeletonItem variant="rect" style="height: 74px; margin-top: 10px" />
          </div>
        </div>
      </template>
    </ElSkeleton>

    <!-- 首屏失败：明确说明失败 + 重试，绝不把失败渲染成一堆 0（统计口径为零与请求失败必须可区分） -->
    <div v-else-if="loadError && !hasLoaded" class="ops-card ops-error">
      <p class="ops-error__title">工作台数据没能加载</p>
      <p class="ops-error__desc">
        统计接口没有返回数据，可能是网络中断或服务未就绪。请重试一次；如果一直失败，请确认后端服务是否正常。
      </p>
      <ElButton type="primary" :loading="loading" @click="refreshAll">重试</ElButton>
    </div>

    <template v-else>
      <!-- ① 待处理：运营真正要动手的事，点进去就是处理页 -->
      <section class="ops-band">
        <h3 class="ops-band__label">待处理</h3>
        <div class="ops-card">
          <div class="ops-todo">
            <component
              :is="item.allowed ? RouterLink : 'div'"
              v-for="item in todoItems"
              :key="item.label"
              class="ops-todo__item"
              :class="{ 'is-link': item.allowed, 'is-empty': item.count === 0 }"
              :to="item.allowed ? item.to : undefined"
            >
              <div class="ops-todo__top">
                <span class="ops-todo__num">{{ formatCount(item.count) }}</span>
                <span class="ops-todo__label">{{ item.label }}</span>
              </div>
              <p class="ops-todo__desc">{{ item.desc }}</p>
              <span v-if="item.allowed" class="ops-todo__go">{{ item.action }}</span>
            </component>
          </div>

          <!-- 待办队列：数字下面直接给「哪几条在等我」，没有成果审核权限就不请求也不渲染 -->
          <div v-if="canReview" class="ops-queue">
            <div class="ops-queue__head">
              <span class="ops-queue__title">待审核成果</span>
              <span class="ops-queue__note">
                共 {{ formatCount(data.submission.pending) }} 条<template v-if="queue.length"
                  >，显示最新 {{ queue.length }} 条</template
                >
              </span>
            </div>

            <p v-if="insightsError" class="ops-queue__state">
              队列加载失败，
              <button type="button" class="ops-inline-link" @click="loadInsights">重试</button>
            </p>
            <p v-else-if="!insightsLoaded" class="ops-queue__state">正在加载…</p>
            <p v-else-if="queue.length === 0" class="ops-queue__state">暂无待审核成果</p>
            <ul v-else class="ops-queue__list">
              <li v-for="row in queue" :key="row.id">
                <RouterLink class="ops-queue__row" :to="reviewLink">
                  <span class="ops-queue__subject">{{ row.subject }}</span>
                  <span class="ops-queue__task">{{ row.task_name }}</span>
                  <span class="ops-queue__period">{{ row.period }}</span>
                  <span class="ops-queue__time">{{ formatSubmittedAt(row.created_at) }}</span>
                </RouterLink>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ② 业务流转：任务 → 成果 → 结算；把原先 7 个孤立数字还原成阶段内的状态分布 -->
      <section class="ops-band">
        <h3 class="ops-band__label">业务流转</h3>
        <div class="ops-card">
          <div class="ops-flow__head">
            <h4>任务到结算</h4>
            <p>百分比为该阶段内部占比</p>
          </div>
          <div class="ops-flow">
            <div v-for="stage in flowStages" :key="stage.key" class="ops-stage">
              <p class="ops-stage__name">{{ stage.name }}</p>

              <template v-if="stage.key === 'settlement'">
                <p class="ops-money"><span class="ops-money__cur">¥</span>{{ payableText }}</p>
                <p class="ops-money__note">共 {{ formatCount(data.settlement.total) }} 单</p>
                <p class="ops-money__rule">全部结算单应发合计，不区分状态</p>
              </template>

              <template v-else>
                <p class="ops-stage__total">
                  {{ stage.totalText }}<span class="ops-stage__unit">{{ stage.unit }}</span>
                </p>
                <p v-if="stage.segments.length === 0" class="ops-stage__empty">暂无数据</p>
                <template v-else>
                  <div class="ops-bar" role="img" :aria-label="ariaOf(stage)">
                    <i
                      v-for="seg in stage.segments"
                      :key="seg.key"
                      class="ops-bar__seg"
                      :class="`is-${seg.tone}`"
                      :style="{ flex: `${seg.value} 1 0` }"
                    ></i>
                  </div>
                  <div class="ops-legend">
                    <div v-for="seg in stage.segments" :key="seg.key" class="ops-legend__row">
                      <span class="ops-legend__dot" :class="`is-${seg.tone}`"></span>
                      <span class="ops-legend__name">{{ seg.name }}</span>
                      <span class="ops-legend__val">{{ formatCount(seg.value) }}</span>
                      <span class="ops-legend__pct">{{ seg.percent }}%</span>
                    </div>
                  </div>
                </template>
              </template>
            </div>
          </div>

          <!-- 趋势图：与上面的「当前状态分布」互补，回答「这两天提交量在变好还是变差」 -->
          <div class="ops-trend">
            <div class="ops-trend__head">
              <h5>成果提交量 · 近 14 天</h5>
              <p v-if="insightsLoaded && trendTotal > 0">
                峰值 {{ formatCount(trendPeak) }} 条，合计 {{ formatCount(trendTotal) }} 条
              </p>
              <div class="ops-trend__key">
                <span><i class="is-warning"></i>待审核</span>
                <span><i class="is-success"></i>已通过</span>
                <span><i class="is-danger"></i>已驳回</span>
              </div>
            </div>

            <p v-if="insightsError" class="ops-trend__state">
              趋势加载失败，
              <button type="button" class="ops-inline-link" @click="loadInsights">重试</button>
            </p>
            <div v-else class="ops-trend__plot">
              <div class="ops-trend__grid" aria-hidden="true"><i></i><i></i><i></i></div>
              <p v-if="!insightsLoaded" class="ops-trend__empty">正在加载…</p>
              <p v-else-if="trendTotal === 0" class="ops-trend__empty">近 14 天没有成果提交</p>
              <div class="ops-trend__cols">
                <div
                  v-for="point in trend"
                  :key="point.date"
                  class="ops-trend__col"
                  role="img"
                  :aria-label="trendLabel(point)"
                  :title="trendLabel(point)"
                >
                  <div class="ops-trend__stack" :style="{ height: stackHeight(point) }">
                    <i class="is-success" :style="{ flex: point.approved }"></i>
                    <i class="is-warning" :style="{ flex: point.pending }"></i>
                    <i class="is-danger" :style="{ flex: point.rejected }"></i>
                  </div>
                  <span class="ops-trend__date">{{ dayLabel(point.date) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ③ 资料库：等权小数字降为一条可点目录，不再与业务指标争视觉权重 -->
      <section class="ops-band">
        <h3 class="ops-band__label">资料库</h3>
        <div class="ops-card">
          <div class="ops-catalog">
            <component
              :is="item.allowed ? RouterLink : 'div'"
              v-for="item in catalogItems"
              :key="item.name"
              class="ops-catalog__item"
              :class="{ 'is-link': item.allowed }"
              :to="item.allowed ? item.to : undefined"
            >
              <span class="ops-catalog__name">{{ item.name }}</span>
              <span class="ops-catalog__num">
                {{ formatCount(item.count) }}<small>{{ item.unit }}</small>
              </span>
            </component>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "MarketDashboard", inheritAttrs: false });

import { computed, onActivated, onMounted, ref } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import { ElMessage } from "element-plus";
import DashboardAPI from "@/api/module_market/dashboard";
import type {
  DashboardInsights,
  DashboardOverview,
  SubmissionTrendPoint,
} from "@/api/module_market/dashboard";
import { useAuth } from "@/hooks/core/useAuth";

const { hasAuth } = useAuth();

/** 冷启动可用的空结构：只在渲染兜底时使用，绝不作为「加载失败」的展示值 */
const EMPTY_OVERVIEW: DashboardOverview = {
  task: { total: 0, in_progress: 0, completed: 0, settled: 0 },
  submission: { total: 0, pending: 0, approved: 0, rejected: 0 },
  settlement: { total: 0, payable_amount: 0 },
  project_count: 0,
  company_count: 0,
  institution_count: 0,
  category_count: 0,
  template_count: 0,
};

/** 数据超过该时长后，从其它页签切回时静默刷新（页面被 KeepAlive 缓存，不会自动重挂载） */
const STALE_AFTER_MS = 5 * 60 * 1000;

const overview = ref<DashboardOverview | null>(null);
const loading = ref(false);
const hasLoaded = ref(false);
const loadError = ref(false);
const updatedAt = ref("");
const loadedAt = ref(0);

const data = computed<DashboardOverview>(() => overview.value ?? EMPTY_OVERVIEW);

const countFormatter = new Intl.NumberFormat("zh-CN");
const moneyFormatter = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const submittedAtFormatter = new Intl.DateTimeFormat("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function formatCount(value: number): string {
  return countFormatter.format(value ?? 0);
}

function formatMoney(value: number): string {
  return moneyFormatter.format(value ?? 0);
}

const payableText = computed(() => formatMoney(data.value.settlement.payable_amount));

/**
 * 加载概览。
 * 首次失败 → 展示错误块 + 重试；已有数据时刷新失败 → 保留旧数据并提示，页面不清空。
 */
async function loadOverview() {
  loading.value = true;
  try {
    const res = await DashboardAPI.getOverview();
    const payload = res.data?.data;
    if (!payload) throw new Error("empty payload");
    overview.value = payload;
    updatedAt.value = timeFormatter.format(new Date());
    loadedAt.value = Date.now();
    loadError.value = false;
    hasLoaded.value = true;
  } catch {
    if (hasLoaded.value) {
      ElMessage.error("刷新失败，当前显示上次加载的数据");
    } else {
      loadError.value = true;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(refreshAll);

// KeepAlive 缓存下切回页面不重挂载：数据过期才补一次，避免首页长期显示旧数字
onActivated(() => {
  if (!hasLoaded.value) {
    // 上次首屏失败：切回时自动再试一次，不逼用户自己找按钮
    if (loadError.value) refreshAll();
    return;
  }
  if (Date.now() - loadedAt.value > STALE_AFTER_MS) refreshAll();
});

/* ---------- 趋势与队列（详情接口） ---------- */

const insights = ref<DashboardInsights | null>(null);
const insightsLoaded = ref(false);
const insightsError = ref(false);

const canReview = computed(() => hasAuth("module_market:submission:query"));

/** 队列行跳审核页并带上「只看待审核」筛选（审核页读 route.query.status 初始化） */
const reviewLink: RouteLocationRaw = {
  path: "/market/task/submission",
  query: { status: "PENDING" },
};

const queue = computed(() => insights.value?.pending_submissions ?? []);

interface TrendColumn extends SubmissionTrendPoint {
  total: number;
}

const trend = computed<TrendColumn[]>(() =>
  (insights.value?.submission_trend ?? []).map((point) => ({
    ...point,
    total: point.pending + point.approved + point.rejected,
  }))
);

const trendTotal = computed(() => trend.value.reduce((sum, point) => sum + point.total, 0));
const trendPeak = computed(() => trend.value.reduce((max, point) => Math.max(max, point.total), 0));

/** 柱高按全局峰值归一，空数据时给 0 而不是 NaN */
function stackHeight(point: TrendColumn): string {
  const peak = trendPeak.value;
  if (peak <= 0) return "0%";
  return `${(point.total / peak) * 100}%`;
}

function dayLabel(date: string): string {
  return date.slice(5).replace("-", "/");
}

function trendLabel(point: TrendColumn): string {
  return `${point.date} 提交 ${point.total} 条：待审核 ${point.pending}，已通过 ${point.approved}，已驳回 ${point.rejected}`;
}

function formatSubmittedAt(iso: string): string {
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? "—" : submittedAtFormatter.format(at);
}

/**
 * 加载趋势与队列。
 * 首次失败 → 两块各自显示重试；已有数据时刷新失败 → 保留旧数据并提示。
 */
async function loadInsights() {
  try {
    const res = await DashboardAPI.getInsights();
    const payload = res.data?.data;
    if (!payload) throw new Error("empty payload");
    insights.value = payload;
    insightsLoaded.value = true;
    insightsError.value = false;
  } catch {
    if (!insightsLoaded.value) {
      insightsError.value = true;
    } else {
      ElMessage.error("趋势与队列刷新失败，当前显示上次加载的数据");
    }
  }
}

/** 页面级刷新：概览与详情并行，互不阻塞（任一失败不拖另一块） */
async function refreshAll() {
  await Promise.all([loadOverview(), loadInsights()]);
}

/* ---------- ① 待处理 ---------- */

interface TodoItem {
  label: string;
  count: number;
  desc: string;
  action: string;
  to: RouteLocationRaw;
  allowed: boolean;
}

const todoItems = computed<TodoItem[]>(() => {
  const d = data.value;
  const defs = [
    {
      label: "待审核成果",
      count: d.submission.pending,
      desc: "成果已提交，等运营判定通过或驳回",
      action: "去审核",
      to: "/market/task/submission",
      perm: "module_market:submission:query",
    },
    {
      label: "进行中任务",
      count: d.task.in_progress,
      desc: "已发布执行中，完成后需推进状态",
      action: "去跟进任务",
      to: "/market/task/task",
      perm: "module_market:task:query",
    },
    {
      label: "结算单",
      count: d.settlement.total,
      desc: "结算归集后，在此确认金额并发起发放",
      action: "去结算",
      to: "/market/payout/settlement",
      perm: "module_market:settlement:query",
    },
  ];
  return defs.map(({ perm, ...item }) => ({ ...item, allowed: hasAuth(perm) }));
});

/* ---------- ② 业务流转 ---------- */

type Tone = "primary" | "success" | "warning" | "danger" | "muted";

interface SegmentDef {
  key: string;
  name: string;
  value: number;
  tone: Tone;
}

interface Segment extends SegmentDef {
  percent: number;
}

interface FlowStage {
  key: "task" | "submission" | "settlement";
  name: string;
  unit: string;
  total: number;
  totalText: string;
  segments: Segment[];
}

/**
 * 计算阶段内状态分布。占比按阶段总数算，因此「其他」也要算进分母。
 * 0 值状态不进入图例：既有数据里 0 条待审核并不需要占一行。
 */
function buildSegments(total: number, defs: SegmentDef[]): Segment[] {
  if (total <= 0) return [];
  return defs
    .filter((def) => def.value > 0)
    .map((def) => ({ ...def, percent: Math.round((def.value / total) * 100) }));
}

const taskSegments = computed<Segment[]>(() => {
  const t = data.value.task;
  const rest = Math.max(t.total - t.in_progress - t.completed - t.settled, 0);
  return buildSegments(t.total, [
    { key: "in_progress", name: "进行中", value: t.in_progress, tone: "warning" },
    { key: "completed", name: "已完成", value: t.completed, tone: "primary" },
    { key: "settled", name: "已结算", value: t.settled, tone: "success" },
    { key: "other", name: "草稿 / 已发布 / 归档", value: rest, tone: "muted" },
  ]);
});

const submissionSegments = computed<Segment[]>(() => {
  const s = data.value.submission;
  const rest = Math.max(s.total - s.pending - s.approved - s.rejected, 0);
  return buildSegments(s.total, [
    { key: "pending", name: "待审核", value: s.pending, tone: "warning" },
    { key: "approved", name: "已通过", value: s.approved, tone: "success" },
    { key: "rejected", name: "已驳回", value: s.rejected, tone: "danger" },
    { key: "other", name: "草稿 / 其他", value: rest, tone: "muted" },
  ]);
});

const flowStages = computed<FlowStage[]>(() => [
  {
    key: "task",
    name: "任务",
    unit: "个",
    total: data.value.task.total,
    totalText: formatCount(data.value.task.total),
    segments: taskSegments.value,
  },
  {
    key: "submission",
    name: "成果",
    unit: "条",
    total: data.value.submission.total,
    totalText: formatCount(data.value.submission.total),
    segments: submissionSegments.value,
  },
  {
    key: "settlement",
    name: "结算",
    unit: "",
    total: data.value.settlement.total,
    totalText: formatCount(data.value.settlement.total),
    segments: [],
  },
]);

/** 色块不是唯一信息载体：图例与 aria-label 都给出文字与数值 */
function ariaOf(stage: FlowStage): string {
  const parts = stage.segments.map((seg) => `${seg.name} ${seg.value} ${stage.unit}`);
  return `${stage.name}状态分布：${parts.join("，")}`;
}

/* ---------- ③ 资料库 ---------- */

interface CatalogItem {
  name: string;
  unit: string;
  count: number;
  to: RouteLocationRaw;
  allowed: boolean;
}

const catalogItems = computed<CatalogItem[]>(() => {
  const d = data.value;
  const defs = [
    {
      name: "项目",
      unit: "个",
      count: d.project_count,
      to: "/market/project/project",
      perm: "module_market:project:query",
    },
    {
      name: "医药公司",
      unit: "家",
      count: d.company_count,
      to: "/market/project/company",
      perm: "module_market:company:query",
    },
    {
      name: "机构",
      unit: "家",
      count: d.institution_count,
      to: "/market/institution/institution",
      perm: "module_market:institution:query",
    },
    {
      name: "一级分类",
      unit: "类",
      count: d.category_count,
      to: "/market/task/task-catalog",
      perm: "module_market:task_category:query",
    },
    {
      name: "二级模板",
      unit: "个",
      count: d.template_count,
      to: "/market/task/task-catalog",
      perm: "module_market:task_category:query",
    },
  ];
  return defs.map(({ perm, ...item }) => ({ ...item, allowed: hasAuth(perm) }));
});
</script>

<style scoped>
/*
 * 版式约束（对齐 design-system/default/MASTER.md）：
 * - 只有一处用重笔：业务流转的分布条 + 阶段箭头；其余保持无阴影、无渐变、无装饰图标。
 * - 颜色只承载状态语义（进行中/待审核=warning，已完成=primary，已结算/已通过=success，
 *   已驳回=danger），不再用「彩色图标块」给每个数字随机上色。
 * - 数字统一 font-variant-numeric: tabular-nums，跨列对齐。
 */
.ops-dash {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ops-dash__util {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: -8px;
}

.ops-dash__meta {
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.ops-skeleton {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ops-band {
  display: flex;
  flex-direction: column;
}

.ops-band__label {
  margin: 0 0 10px 2px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.ops-card {
  overflow: hidden;
  background: var(--default-box-color);
  border: 1px solid var(--fa-card-border);
  border-radius: calc(var(--custom-radius) + 4px);
}

/* ① 待处理 */
.ops-todo {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.ops-todo__item {
  display: block;
  padding: 20px 22px;
  color: inherit;
  text-decoration: none;
  transition: background-color 0.15s ease;
}

.ops-todo__item + .ops-todo__item {
  border-left: 1px solid var(--fa-card-border);
}

.ops-todo__item.is-link:hover {
  background: var(--fa-hover-color);
}

.ops-todo__item.is-link:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: -2px;
}

.ops-todo__top {
  display: flex;
  gap: 10px;
  align-items: baseline;
}

.ops-todo__num {
  font-size: 34px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  line-height: 1.05;
  color: var(--el-text-color-primary);
  letter-spacing: -0.5px;
}

.ops-todo__label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.ops-todo__desc {
  margin: 8px 0 14px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.ops-todo__go {
  padding-bottom: 1px;
  font-size: 13px;
  color: var(--el-color-primary);
  border-bottom: 1px solid transparent;
}

.ops-todo__item.is-link:hover .ops-todo__go {
  border-bottom-color: currentcolor;
}

.ops-todo__item.is-empty .ops-todo__num {
  color: var(--el-text-color-placeholder);
}

.ops-todo__item.is-empty .ops-todo__go {
  color: var(--el-text-color-secondary);
}

/* ② 业务流转 */
.ops-flow__head {
  display: flex;
  gap: 12px;
  align-items: baseline;
  padding: 15px 22px;
  border-bottom: 1px solid var(--fa-card-border);
}

.ops-flow__head h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.ops-flow__head p {
  margin: 0 0 0 auto;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.ops-flow {
  display: grid;
  grid-template-columns: 1.12fr 1.12fr 0.86fr;
}

.ops-stage {
  position: relative;
  padding: 18px 22px 20px;
}

.ops-stage + .ops-stage {
  border-left: 1px solid var(--fa-card-border);
}

/* 阶段之间是真实顺序（任务 → 成果 → 结算），箭头标的是流转方向，不是装饰 */
.ops-stage + .ops-stage::before,
.ops-stage + .ops-stage::after {
  position: absolute;
  content: "";
}

.ops-stage + .ops-stage::before {
  top: 24px;
  left: -20px;
  width: 20px;
  height: 20px;
  background: var(--default-box-color);
  border: 1px solid var(--fa-card-border);
  border-radius: 50%;
}

.ops-stage + .ops-stage::after {
  top: 31px;
  left: -14px;
  width: 6px;
  height: 6px;
  border-top: 1.5px solid var(--el-text-color-secondary);
  border-right: 1.5px solid var(--el-text-color-secondary);
  transform: rotate(45deg);
}

.ops-stage__name {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.ops-stage__total {
  margin: 6px 0 0;
  font-size: 26px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  color: var(--el-text-color-primary);
  letter-spacing: -0.3px;
}

.ops-stage__unit {
  margin-left: 4px;
  font-size: 12.5px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
  letter-spacing: 0;
}

.ops-stage__empty {
  margin: 14px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-placeholder);
}

.ops-money {
  margin: 6px 0 0;
  font-size: 24px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-primary);
  letter-spacing: -0.3px;
}

.ops-money__cur {
  margin-right: 2px;
  font-size: 15px;
  color: var(--el-text-color-regular);
}

.ops-money__note {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.ops-money__rule {
  padding-top: 14px;
  margin: 16px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
  text-wrap: pretty;
  border-top: 1px dashed var(--default-border);
}

.ops-bar {
  display: flex;
  gap: 2px;
  height: 8px;
  margin: 14px 0 16px;
}

.ops-bar__seg {
  min-width: 0;
  border-radius: 2px;
}

.ops-bar__seg:first-child {
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
}

.ops-bar__seg:last-child {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.ops-legend {
  display: grid;
  gap: 7px;
}

.ops-legend__row {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.ops-legend__dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 2px;
}

.ops-legend__name {
  white-space: nowrap;
}

.ops-legend__val {
  margin-left: auto;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-regular);
}

.ops-legend__pct {
  width: 38px;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-secondary);
  text-align: right;
}

.is-primary {
  background: var(--el-color-primary);
}

.is-success {
  background: var(--el-color-success);
}

.is-warning {
  background: var(--el-color-warning);
}

.is-danger {
  background: var(--el-color-danger);
}

.is-muted {
  background: var(--fa-gray-400);
}

/* ③ 资料库 */
.ops-catalog {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.ops-catalog__item {
  display: block;
  padding: 14px 22px;
  color: inherit;
  text-decoration: none;
  transition: background-color 0.15s ease;
}

.ops-catalog__item + .ops-catalog__item {
  border-left: 1px solid var(--fa-card-border);
}

.ops-catalog__item.is-link:hover {
  background: var(--fa-hover-color);
}

.ops-catalog__item.is-link:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: -2px;
}

.ops-catalog__name {
  display: block;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.ops-catalog__num {
  display: flex;
  gap: 6px;
  align-items: baseline;
  margin-top: 4px;
  font-size: 20px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-primary);
}

.ops-catalog__num small {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

/* ① 待处理：队列 */
.ops-queue {
  padding: 14px 22px 16px;
  border-top: 1px solid var(--fa-card-border);
}

.ops-queue__head {
  display: flex;
  gap: 12px;
  align-items: baseline;
  margin-bottom: 6px;
}

.ops-queue__title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.ops-queue__note {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.ops-queue__state {
  margin: 8px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-placeholder);
}

.ops-queue__list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.ops-queue__row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.6fr) 84px 92px;
  gap: 12px;
  align-items: baseline;
  padding: 7px 10px;
  margin: 0 -10px;
  font-size: 13px;
  color: inherit;
  text-decoration: none;
  border-radius: 6px;
  transition: background-color 0.15s ease;
}

.ops-queue__row:hover {
  background: var(--fa-hover-color);
}

.ops-queue__row:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: -2px;
}

.ops-queue__subject,
.ops-queue__task {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ops-queue__subject {
  color: var(--el-text-color-primary);
}

.ops-queue__task {
  color: var(--el-text-color-regular);
}

.ops-queue__period,
.ops-queue__time {
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-secondary);
}

.ops-queue__time {
  text-align: right;
}

.ops-inline-link {
  padding: 0;
  font: inherit;
  color: var(--el-color-primary);
  cursor: pointer;
  background: none;
  border: 0;
  border-bottom: 1px solid transparent;
}

.ops-inline-link:hover {
  border-bottom-color: currentcolor;
}

.ops-inline-link:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

/* ② 业务流转：14 天趋势（自绘堆叠柱，空数据也保留基线与网格） */
.ops-trend {
  padding: 15px 22px 20px;
  border-top: 1px solid var(--fa-card-border);
}

.ops-trend__head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: baseline;
}

.ops-trend__head h5 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.ops-trend__head p {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.ops-trend__key {
  display: flex;
  gap: 14px;
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.ops-trend__key span {
  display: inline-flex;
  gap: 6px;
  align-items: center;
}

.ops-trend__key i {
  width: 7px;
  height: 7px;
  border-radius: 2px;
}

.ops-trend__state {
  margin: 12px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-placeholder);
}

.ops-trend__plot {
  position: relative;
  padding-bottom: 18px;
  margin-top: 16px;
}

.ops-trend__grid {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 104px;
  pointer-events: none;
}

.ops-trend__grid i {
  position: absolute;
  right: 0;
  left: 0;
  height: 1px;
  background: var(--default-border);
}

.ops-trend__grid i:nth-child(1) {
  top: 25%;
}

.ops-trend__grid i:nth-child(2) {
  top: 50%;
}

.ops-trend__grid i:nth-child(3) {
  top: 75%;
}

.ops-trend__empty {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 104px;
  margin: 0;
  font-size: 12.5px;
  color: var(--el-text-color-placeholder);
}

.ops-trend__cols {
  position: relative;
  display: flex;
  gap: 4px;
  align-items: flex-end;
  height: 104px;
  border-bottom: 1px solid var(--default-border);
}

.ops-trend__col {
  position: relative;
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
  height: 100%;
}

.ops-trend__stack {
  display: flex;
  flex-direction: column-reverse;
  width: 100%;
  max-width: 26px;
  overflow: hidden;
  border-radius: 2px;
}

.ops-trend__stack i {
  display: block;
  min-height: 0;
}

.ops-trend__date {
  position: absolute;
  bottom: -18px;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

/* 失败态 */
.ops-error {
  padding: 28px 22px;
}

.ops-error__title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.ops-error__desc {
  max-width: 46em;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

@media (width <= 1180px) {
  .ops-flow {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ops-stage:nth-child(3) {
    grid-column: 1 / -1;
    border-top: 1px solid var(--fa-card-border);
    border-left: 0;
  }

  .ops-stage:nth-child(3)::before,
  .ops-stage:nth-child(3)::after {
    display: none;
  }

  .ops-catalog {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    row-gap: 1px;
  }

  .ops-catalog__item:nth-child(4) {
    border-left: 0;
  }
}

@media (width <= 900px) {
  .ops-todo {
    grid-template-columns: 1fr;
  }

  .ops-todo__item + .ops-todo__item {
    border-top: 1px solid var(--fa-card-border);
    border-left: 0;
  }

  /* 队列让出「所属月份」一列，把宽度留给对象名与任务名 */
  .ops-queue__row {
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.6fr) 92px;
  }

  .ops-queue__period {
    display: none;
  }
}

@media (width <= 760px) {
  .ops-dash {
    gap: 20px;
  }

  .ops-flow {
    grid-template-columns: 1fr;
  }

  .ops-stage + .ops-stage {
    border-top: 1px solid var(--fa-card-border);
    border-left: 0;
  }

  .ops-stage + .ops-stage::before,
  .ops-stage + .ops-stage::after {
    display: none;
  }

  .ops-catalog {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ops-catalog__item:nth-child(3),
  .ops-catalog__item:nth-child(5) {
    border-left: 0;
  }

  /* 窄屏队列改为两行：对象名 + 时间，任务名换行占满整行 */
  .ops-queue {
    padding: 12px 16px 14px;
  }

  .ops-queue__row {
    display: grid;
    grid-template-areas:
      "subject time"
      "task task";
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 2px 10px;
  }

  .ops-queue__subject {
    grid-area: subject;
  }

  .ops-queue__task {
    grid-area: task;
    font-size: 12.5px;
  }

  .ops-queue__time {
    grid-area: time;
  }

  .ops-trend {
    padding: 14px 16px 18px;
  }

  .ops-trend__key {
    margin-left: 0;
  }

  /* 14 个日期标签在窄屏会挤在一起，隔一个显示 */
  .ops-trend__col:nth-child(even) .ops-trend__date {
    visibility: hidden;
  }
}
</style>
