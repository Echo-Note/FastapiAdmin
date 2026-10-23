<!-- 归集结算单：列表 + 详情（含结算明细） -->
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
      <FaTableHeader v-model:columns="columnChecks" v-model:showSearchBar="showSearchBar" :loading="loading" @refresh="refreshData" />

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

    <ElDialog v-model="detailVisible" title="结算单详情" width="800px">
      <FaDescriptions :column="4" :data="detailData" :items="detailItems">
        <template #userName="{ row }">{{ resolveUserName(row) }}</template>
      </FaDescriptions>
      <ElDivider content-position="left">结算明细</ElDivider>
      <ElTable :data="detailData.items ?? []" size="small" border max-height="360px">
        <ElTableColumn type="index" label="#" width="48" />
        <ElTableColumn prop="service_type" label="服务类型" min-width="110" />
        <ElTableColumn prop="service_item" label="服务项目" min-width="110" />
        <ElTableColumn prop="service_task" label="服务任务" min-width="140" />
        <ElTableColumn prop="unit" label="单位" width="90" />
        <ElTableColumn prop="price" label="单价" width="90" align="right" />
        <ElTableColumn prop="qty" label="数量" width="80" align="right" />
        <ElTableColumn prop="amount" label="金额" width="100" align="right" />
      </ElTable>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import SettlementAPI, { type SettlementTable } from "@/api/module_market/settlement";
import TaskAPI from "@/api/module_market/task";
import UserAPI from "@/api/module_system/user";
import { SETTLEMENT_STATUS_MAP } from "@/api/module_market/constants";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketSettlement", inheritAttrs: false });

const route = useRoute();

const searchForm = ref<{ task_id?: number; user_id?: number; status?: string }>({ task_id: undefined, user_id: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const taskOptions = ref<OptionType[]>([]);
const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});
const statusOptions = computed<OptionType[]>(() => Object.entries(SETTLEMENT_STATUS_MAP).map(([value, v]) => ({ value, label: v.text })));

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "任务", key: "task_id", type: "select", props: { placeholder: "请选择任务", options: taskOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 8 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);

const opCtx = {
  onDetail: (id: number) => void openDetail(id),
};

function buildRowActions(row: SettlementTable): TableOperationAction[] {
  return [{ key: "detail", label: "详情", artType: "view", perm: "module_market:settlement:query", run: () => opCtx.onDetail(row.id!) }];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData } =
  useTable({
    core: {
      apiFn: SettlementAPI.listSettlement,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<SettlementTable>(() => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "task_id", label: "任务ID", width: 90 },
        { prop: "user_id", label: "结算对象", minWidth: 130, formatter: (row: SettlementTable) => userMap.value[row.user_id!] ?? `#${row.user_id}` },
        { prop: "qty", label: "结算数量", width: 90, align: "right" },
        { prop: "payable_amount", label: "应付金额", width: 110, align: "right" },
        { prop: "paid_amount", label: "已付金额", width: 110, align: "right" },
        { prop: "pay_status", label: "支付状态", width: 100, formatter: (row: SettlementTable) => row.pay_status ?? "—" },
        { prop: "status", label: "状态", width: 92, status: SETTLEMENT_STATUS_MAP },
        { prop: "created_time", label: "创建时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 90, fixed: "right", align: "center", formatter: (row: SettlementTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailVisible = ref(false);
const detailData = ref<Partial<SettlementTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "任务ID", prop: "task_id" },
  { label: "结算对象", prop: "user_id", slot: "userName" },
  { label: "结算数量", prop: "qty" },
  { label: "状态", prop: "status", tag: { map: SETTLEMENT_STATUS_MAP } },
  { label: "应付金额", prop: "payable_amount" },
  { label: "已付金额", prop: "paid_amount" },
  { label: "支付状态", prop: "pay_status" },
  { label: "创建时间", prop: "created_time" },
];

async function openDetail(id: number) {
  const res = await SettlementAPI.detailSettlement(id);
  detailData.value = res.data.data;
  detailVisible.value = true;
}

function resolveUserName(row: Record<string, unknown> | null): string {
  const uid = row?.user_id as number | undefined;
  return uid ? (userMap.value[uid] ?? `#${uid}`) : "—";
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

onMounted(() => {
  loadOptions();
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
  searchForm.value = { task_id: undefined, user_id: undefined, status: undefined };
  await resetSearchParams();
}
</script>
