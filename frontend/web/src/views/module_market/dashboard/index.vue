<template>
  <div class="flex flex-col gap-5">
    <!-- 加载态 -->
    <div v-if="loading" class="fa-card h-64 flex items-center justify-center">
      <ElSkeleton :rows="3" animated class="w-full px-8" />
    </div>

    <template v-else>
      <!-- 核心指标 -->
      <ElRow :gutter="20">
        <ElCol v-for="card in coreCards" :key="card.title" :xs="24" :sm="12" :md="6" class="mb-5">
          <FaStatsCard
            :icon="card.icon"
            :icon-style="card.iconStyle"
            :box-style="card.boxStyle"
            :title="card.title"
            :description="card.description"
            :count="card.count"
            :decimals="card.decimals"
            :text-color="card.textColor"
            :show-arrow="false"
          />
        </ElCol>
      </ElRow>

      <!-- 任务状态细分 -->
      <ElRow :gutter="20">
        <ElCol v-for="card in taskCards" :key="card.title" :xs="24" :sm="8" :md="8" class="mb-5">
          <FaStatsCard
            :icon="card.icon"
            :icon-style="card.iconStyle"
            :box-style="card.boxStyle"
            :title="card.title"
            :description="card.description"
            :count="card.count"
            :text-color="card.textColor"
            :show-arrow="false"
          />
        </ElCol>
      </ElRow>

      <!-- 基础数据 -->
      <ElCard shadow="never" class="fa-card overflow-hidden">
        <template #header>
          <span class="text-base font-semibold" style="color: var(--el-text-color-primary)">
            基础数据
          </span>
        </template>
        <ElRow :gutter="20">
          <ElCol v-for="card in baseCards" :key="card.title" :xs="12" :sm="8" :md="8" class="mb-5">
            <FaStatsCard
              :icon="card.icon"
              :icon-style="card.iconStyle"
              :box-style="card.boxStyle"
              :title="card.title"
              :description="card.description"
              :count="card.count"
              :text-color="card.textColor"
              :show-arrow="false"
            />
          </ElCol>
        </ElRow>
      </ElCard>
    </template>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "MarketDashboard", inheritAttrs: false });

import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import DashboardAPI from "@/api/module_market/dashboard";
import type { DashboardOverview } from "@/api/module_market/dashboard";

const loading = ref(true);
const overview = ref<DashboardOverview>({
  task: { total: 0, in_progress: 0, completed: 0, settled: 0 },
  submission: { total: 0, pending: 0, approved: 0, rejected: 0 },
  settlement: { total: 0, payable_amount: 0 },
  project_count: 0,
  company_count: 0,
  institution_count: 0,
  category_count: 0,
  template_count: 0,
});

async function loadOverview() {
  loading.value = true;
  try {
    const res = await DashboardAPI.getOverview();
    if (res.data?.data) overview.value = res.data.data;
  } catch (error) {
    ElMessage.error("加载运营工作台数据失败");
  } finally {
    loading.value = false;
  }
}

interface StatCard {
  title: string;
  description: string;
  count: number;
  icon: string;
  iconStyle: string;
  boxStyle: string;
  textColor: string;
  decimals?: number;
}

const coreCards = computed<StatCard[]>(() => [
  {
    title: "任务总数",
    description: "全部任务",
    count: overview.value.task.total,
    icon: "ri:list-check-3",
    iconStyle: "bg-[var(--el-color-primary)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "成果总数",
    description: "全部成果提交",
    count: overview.value.submission.total,
    icon: "ri:file-list-3-line",
    iconStyle: "bg-[var(--el-color-success)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "待审核成果",
    description: "等待运营审核",
    count: overview.value.submission.pending,
    icon: "ri:time-line",
    iconStyle: "bg-[var(--el-color-warning)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "应发金额",
    description: "结算应发合计（元）",
    count: overview.value.settlement.payable_amount,
    icon: "ri:money-cny-circle-line",
    iconStyle: "bg-[var(--el-color-danger)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
    decimals: 2,
  },
]);

const taskCards = computed<StatCard[]>(() => [
  {
    title: "进行中任务",
    description: "已发布执行中",
    count: overview.value.task.in_progress,
    icon: "ri:play-circle-line",
    iconStyle: "bg-[var(--el-color-primary)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "已完成任务",
    description: "运营已判定完成",
    count: overview.value.task.completed,
    icon: "ri:checkbox-circle-line",
    iconStyle: "bg-[var(--el-color-success)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "已结算任务",
    description: "已归集结算",
    count: overview.value.task.settled,
    icon: "ri:bank-card-line",
    iconStyle: "bg-[var(--el-color-warning)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
]);

const baseCards = computed<StatCard[]>(() => [
  {
    title: "项目",
    description: "在库项目数",
    count: overview.value.project_count,
    icon: "ri:folder-3-line",
    iconStyle: "bg-[var(--el-color-primary)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "医药公司",
    description: "在库公司数",
    count: overview.value.company_count,
    icon: "ri:building-2-line",
    iconStyle: "bg-[var(--el-color-success)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "机构",
    description: "在库机构数",
    count: overview.value.institution_count,
    icon: "ri:hospital-line",
    iconStyle: "bg-[var(--el-color-warning)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "一级分类",
    description: "任务一级分类数",
    count: overview.value.category_count,
    icon: "ri:price-tag-3-line",
    iconStyle: "bg-[var(--el-color-danger)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
  {
    title: "二级模板",
    description: "任务二级模板数",
    count: overview.value.template_count,
    icon: "ri:briefcase-line",
    iconStyle: "bg-[var(--el-color-info)]",
    boxStyle: "",
    textColor: "var(--el-text-color-primary)",
  },
]);

onMounted(loadOverview);
</script>
