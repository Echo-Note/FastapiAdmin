<!-- 归集结算单：列表 + 详情（含结算明细）+ 归集结算 + 确认结算 -->
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
          <FaTableHeaderLeft :perm-create="['module_market:settlement:run']" create-text="归集结算" @add="openSettleDialog" />
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

    <!-- 结算单详情 -->
    <ElDialog v-model="detailVisible" title="结算单详情" width="840px">
      <FaDescriptions :column="4" :data="detailData" :items="detailItems">
        <template #userName="{ row }">{{ resolveUserName(row) }}</template>
        <template #payStatus="{ row }">{{ payStatusText(row?.pay_status as string | null | undefined) }}</template>
      </FaDescriptions>
      <ElDivider content-position="left">结算明细</ElDivider>
      <ElTable :data="detailData.items ?? []" size="small" border max-height="360px">
        <ElTableColumn type="index" label="#" width="48" />
        <ElTableColumn prop="category_name" label="一级分类" min-width="120" />
        <ElTableColumn prop="template_name" label="二级任务" min-width="150" />
        <ElTableColumn prop="unit" label="单位" width="90" />
        <ElTableColumn prop="price" label="单价" width="90" align="right" />
        <ElTableColumn prop="qty" label="数量" width="80" align="right" />
        <ElTableColumn prop="amount" label="金额" width="110" align="right" />
      </ElTable>
    </ElDialog>

    <!-- 归集结算对话框 -->
    <ElDialog v-model="settleVisible" title="归集结算" width="480px" :close-on-click-modal="false">
      <FaForm
        ref="settleFormRef"
        v-model="settleForm"
        :items="settleFormItems"
        :rules="settleRules"
        label-suffix=":"
        :label-width="100"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="settleVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="settleSubmitting" @click="handleSettleSubmit">归集结算</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import SettlementAPI, { type SettlementTable } from "@/api/module_market/settlement";
import TaskAPI from "@/api/module_market/task";
import UserAPI from "@/api/module_system/user";
import { useDictStore } from "@stores";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";
import { useFormDraft } from "@/hooks/core/useFormDraft";

defineOptions({ name: "MarketSettlement", inheritAttrs: false });

const route = useRoute();
const dictStore = useDictStore();

// ── 字典：结算单状态 ──
const settlementStatusMap = computed<Record<string, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_settlement_status"] ?? []).map((d) => [
      d.dict_value!,
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);
const statusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_settlement_status") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);

/** 支付状态目前只可能是 SCHEDULED（归集已算实发、等二期打款） */
const PAY_STATUS_TEXT: Record<string, string> = { SCHEDULED: "待打款", PAID: "已打款" };
const payStatusText = (value?: string | null) => (value ? (PAY_STATUS_TEXT[value] ?? value) : "—");

const searchForm = ref<{ task_id?: number; user_id?: number; period?: string; status?: string }>({ task_id: undefined, user_id: undefined, period: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const taskOptions = ref<OptionType[]>([]);
const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "任务", key: "task_id", type: "select", props: { placeholder: "请选择任务", options: taskOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "结算月份", key: "period", type: "input", placeholder: "如 2026-03", clearable: true, span: 8 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 8 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);

const opCtx = {
  onDetail: (id: number) => void openDetail(id),
  onConfirm: (row: SettlementTable) => void confirmRow(row),
};

function buildRowActions(row: SettlementTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:settlement:query", run: () => opCtx.onDetail(row.id!) },
  ];
  if (row.status === "PENDING" || row.status === "CALCULATED") {
    actions.push({ key: "confirm", label: "确认结算", artType: "edit", perm: "module_market:settlement:confirm", run: () => opCtx.onConfirm(row) });
  }
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData } =
  useTable({
    core: {
      apiFn: SettlementAPI.listSettlement,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<SettlementTable>(() => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "task_id", label: "任务ID", width: 90 },
        { prop: "user_name", label: "结算对象", minWidth: 140, formatter: (row: SettlementTable) => userLabel(row) },
        { prop: "user.mobile", label: "手机号", width: 130, formatter: (row: SettlementTable) => row.user?.mobile ?? "—" },
        { prop: "period", label: "结算月份", width: 100 },
        { prop: "qty", label: "结算数量", width: 90, align: "right" },
        { prop: "payable_amount", label: "应付金额", width: 110, align: "right" },
        { prop: "paid_amount", label: "实发金额", width: 110, align: "right", formatter: (row: SettlementTable) => row.paid_amount ?? "—" },
        { prop: "pay_status", label: "支付状态", width: 100, formatter: (row: SettlementTable) => payStatusText(row.pay_status) },
        { prop: "status", label: "状态", width: 92, status: settlementStatusMap.value },
        { prop: "created_time", label: "创建时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 150, fixed: "right", align: "center", formatter: (row: SettlementTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailVisible = ref(false);
const detailData = ref<Partial<SettlementTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "任务ID", prop: "task_id" },
  { label: "结算对象", prop: "user_id", slot: "userName" },
  { label: "手机号", prop: "user.mobile" },
  { label: "结算月份", prop: "period" },
  { label: "状态", prop: "status", tag: { map: settlementStatusMap.value } },
  { label: "结算数量", prop: "qty" },
  { label: "应付金额", prop: "payable_amount" },
  { label: "实发金额", prop: "paid_amount" },
  { label: "支付状态", prop: "pay_status", slot: "payStatus" },
  { label: "创建时间", prop: "created_time" },
];

async function openDetail(id: number) {
  const res = await SettlementAPI.detailSettlement(id);
  detailData.value = res.data.data;
  detailVisible.value = true;
}

function resolveUserName(row: Record<string, unknown> | null): string {
  return userLabel(row as SettlementTable);
}

/** 结算对象：优先用后端带回的昵称，拿不到才回退到 ID（不再靠前端反查用户表） */
function userLabel(row: SettlementTable): string {
  return row.user?.name || (row.user_id ? `#${row.user_id}` : "—");
}

async function confirmRow(row: SettlementTable) {
  try {
    await ElMessageBox.confirm(`确定确认结算单（任务 #${row.task_id} / 结算月份 ${row.period}）吗？`, "确认结算", { type: "warning" });
    await SettlementAPI.confirmSettlement(row.id!);
    await refreshData();
  } catch {
    // 用户取消
  }
}

// ── 归集结算 ──
const settleVisible = ref(false);
const settleSubmitting = ref(false);
const settleFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const settleForm = ref<{ task_id?: number; period?: string }>({ task_id: undefined, period: undefined });

const settleFormItems = computed<FormItem[]>(() => [
  { label: "任务", key: "task_id", type: "select", span: 24, props: { placeholder: "请选择已完成的任务", options: taskOptions.value, filterable: true } },
  { label: "结算月份", key: "period", type: "input", span: 24, props: { placeholder: "如 2026-03", maxlength: 16 } },
]);

const settleRules = reactive({
  task_id: [{ required: true, message: "请选择任务", trigger: "change" }],
  period: [{ required: true, message: "请输入结算月份", trigger: "blur" }],
});

const settleDraft = useFormDraft({
  key: "settlement",
  dialogVisible: settleVisible,
  form: settleForm,
  blank: () => ({ task_id: undefined, period: undefined }),
});

function openSettleDialog() {
  settleDraft.openCreate();
}

async function handleSettleSubmit() {
  if (!settleFormRef.value) return;
  try {
    await settleFormRef.value.validate();
  } catch {
    return;
  }
  if (!settleForm.value.task_id || !settleForm.value.period) return;
  settleSubmitting.value = true;
  try {
    await SettlementAPI.settle({ task_id: settleForm.value.task_id, period: settleForm.value.period });
    settleDraft.done();
    settleVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    settleSubmitting.value = false;
  }
}

async function loadOptions() {
  const [taskRes, userRes] = await Promise.all([
    TaskAPI.listTask({ page_no: 1, page_size: 100 }),
    UserAPI.listUser({ page_no: 1, page_size: 100 }),
  ]);
  taskOptions.value = taskRes.data.data.items.map((t) => ({ value: t.id!, label: t.task_no ?? String(t.id) }));
  userOptions.value = userRes.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}` }));
  userMap.value = Object.fromEntries(userRes.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
}

onMounted(async () => {
  await dictStore.getDict(["market_settlement_status"]);
  await loadOptions();
  // 从任务页跳转而来：透传 task_id 预填筛选
  const taskId = route.query.task_id;
  if (taskId) {
    searchForm.value.task_id = Number(taskId);
    replaceSearchParams(cleanEmptyArrayParams({ ...searchForm.value }) as Record<string, unknown>);
    getData();
  }
});

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { task_id: undefined, user_id: undefined, period: undefined, status: undefined };
  await resetSearchParams();
}
</script>
