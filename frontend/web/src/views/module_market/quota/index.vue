<!-- 限额配置：列表 + 配置限额（upsert）+ 用量查询 -->
<template>
  <div class="fa-full-height">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="searchItems"
      :is-expand="false"
      :show-expand="true"
      :show-reset="true"
      :show-search="true"
      @search="handleSearch"
      @reset="onResetSearch"
    />

    <ElCard class="fa-table-card" :style="{ 'margin-top': showSearchBar ? '12px' : '0' }">
      <FaTableHeader v-model:columns="columnChecks" v-model:showSearchBar="showSearchBar" :loading="loading" @refresh="refreshData">
        <template #left>
          <FaTableHeaderLeft :perm-create="['module_market:quota:edit']" create-text="配置限额" @add="openSaveDialog" />
        </template>
      </FaTableHeader>

      <FaTable
        ref="faTableRef"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>

    <!-- 配置限额对话框 -->
    <ElDialog v-model="saveVisible" :title="saveTitle" width="520px" :close-on-click-modal="false" @closed="resetSaveForm">
      <FaForm
        ref="saveFormRef"
        v-model="saveForm"
        :items="saveFormItems"
        :rules="saveRules"
        label-suffix=":"
        :label-width="110"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="saveVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="saveSubmitting" @click="handleSaveSubmit">保存</ElButton>
      </template>
    </ElDialog>

    <!-- 用量查询对话框 -->
    <ElDialog v-model="usageVisible" title="限额用量详情" width="640px">
      <FaDescriptions :column="4" :data="usageData" :items="usageItems">
        <template #userName="{ row }">{{ resolveUserName(row) }}</template>
      </FaDescriptions>
      <ElDivider content-position="left">结转明细</ElDivider>
      <ElTable :data="usageData.carryover_items ?? []" size="small" border max-height="260px">
        <ElTableColumn type="index" label="#" width="48" />
        <ElTableColumn prop="from_period" label="来源周期" width="110" />
        <ElTableColumn prop="to_period" label="结转周期" width="110" />
        <ElTableColumn prop="amount" label="结转金额" align="right" />
        <ElTableColumn prop="status" label="状态" width="100" />
      </ElTable>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import QuotaAPI, { type QuotaConfigTable, type QuotaUsageDetail } from "@/api/module_market/quota";
import UserAPI from "@/api/module_system/user";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketQuota", inheritAttrs: false });

const searchForm = ref<{ user_id?: number; period?: string }>({ user_id: undefined, period: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "周期", key: "period", type: "input", placeholder: "如 2026-10", clearable: true, span: 8 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);

const opCtx = {
  onUsage: (row: QuotaConfigTable) => void openUsage(row),
  onEdit: (row: QuotaConfigTable) => void openSaveDialog(row),
};

function buildRowActions(row: QuotaConfigTable): TableOperationAction[] {
  return [
    { key: "usage", label: "用量", artType: "view", perm: "module_market:quota:query", run: () => opCtx.onUsage(row) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:quota:edit", run: () => opCtx.onEdit(row) },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData } =
  useTable({
    core: {
      apiFn: QuotaAPI.listQuota,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<QuotaConfigTable>(() => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "user_id", label: "用户", minWidth: 140, formatter: (row: QuotaConfigTable) => userMap.value[row.user_id!] ?? `#${row.user_id}` },
        { prop: "period", label: "周期", width: 100 },
        { prop: "quota_amount", label: "限额金额", width: 110, align: "right" },
        { prop: "enabled", label: "启用", width: 80, align: "center", formatter: (row: QuotaConfigTable) => (row.enabled ? "是" : "否") },
        { prop: "created_time", label: "配置时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 140, fixed: "right", align: "center", formatter: (row: QuotaConfigTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

// ── 配置限额 ──
const saveVisible = ref(false);
const saveSubmitting = ref(false);
const saveFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const saveForm = ref<{ user_id?: number; period?: string; quota_amount?: number; enabled: boolean }>({ user_id: undefined, period: undefined, quota_amount: undefined, enabled: true });

const saveTitle = computed(() => (saveForm.value.user_id ? "修改限额配置" : "新增限额配置"));

const saveFormItems = computed<FormItem[]>(() => [
  { label: "用户", key: "user_id", type: "select", span: 24, props: { placeholder: "请选择 C 端用户", options: userOptions.value, filterable: true } },
  { label: "周期", key: "period", type: "input", span: 24, props: { placeholder: "自然月，如 2026-10", maxlength: 16 } },
  { label: "限额金额", key: "quota_amount", type: "number", span: 24, props: { min: 0, precision: 2, controlsPosition: "right" } },
  { label: "是否启用", key: "enabled", type: "switch", span: 24 },
]);

const saveRules = reactive({
  user_id: [{ required: true, message: "请选择用户", trigger: "change" }],
  period: [{ required: true, message: "请输入周期", trigger: "blur" }],
  quota_amount: [{ required: true, message: "请输入限额金额", trigger: "blur" }],
});

function openSaveDialog(row?: QuotaConfigTable) {
  if (row) {
    saveForm.value = { user_id: row.user_id, period: row.period, quota_amount: row.quota_amount, enabled: row.enabled ?? true };
  } else {
    saveForm.value = { user_id: undefined, period: undefined, quota_amount: undefined, enabled: true };
  }
  saveVisible.value = true;
}

function resetSaveForm() {
  saveForm.value = { user_id: undefined, period: undefined, quota_amount: undefined, enabled: true };
}

async function handleSaveSubmit() {
  if (!saveFormRef.value) return;
  try {
    await saveFormRef.value.validate();
  } catch {
    return;
  }
  if (!saveForm.value.user_id || !saveForm.value.period || saveForm.value.quota_amount === undefined) return;
  saveSubmitting.value = true;
  try {
    await QuotaAPI.saveQuota({ user_id: saveForm.value.user_id, period: saveForm.value.period, quota_amount: saveForm.value.quota_amount, enabled: saveForm.value.enabled });
    saveVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    saveSubmitting.value = false;
  }
}

// ── 用量查询 ──
const usageVisible = ref(false);
const usageData = ref<Partial<QuotaUsageDetail>>({});
const usageItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "用户", prop: "user_id", slot: "userName" },
  { label: "周期", prop: "period" },
  { label: "限额金额", prop: "quota_amount" },
  { label: "已接收金额", prop: "received_amount" },
  { label: "应付金额", prop: "payable_amount" },
  { label: "超额金额", prop: "over_amount" },
];

async function openUsage(row: QuotaConfigTable) {
  const res = await QuotaAPI.usageQuota({ user_id: row.user_id!, period: row.period! });
  usageData.value = res.data.data;
  usageVisible.value = true;
}

function resolveUserName(row: Record<string, unknown> | null): string {
  const uid = row?.user_id as number | undefined;
  return uid ? (userMap.value[uid] ?? `#${uid}`) : "—";
}

async function loadOptions() {
  const userRes = await UserAPI.listUser({ page_no: 1, page_size: 100 });
  userOptions.value = userRes.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}` }));
  userMap.value = Object.fromEntries(userRes.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
}

onMounted(loadOptions);

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { user_id: undefined, period: undefined };
  await resetSearchParams();
}
</script>
