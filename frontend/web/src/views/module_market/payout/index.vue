<!-- 发放管理：发放额度配置 CRUD + 发放结果（应发/实发/滚存）+ 津贴账户/明细查询 -->
<template>
  <div class="fa-full-height">
    <ElTabs v-model="activeTab">
      <ElTabPane label="发放额度配置" name="config">
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
              <FaTableHeaderLeft
                :remove-ids="selectedIds"
                :perm-create="['module_market:payout:create']"
                :perm-delete="['module_market:payout:delete']"
                :delete-loading="batchDeleting"
                @add="handleAdd"
                @delete="handleBatchDelete"
              />
              <ElButton :disabled="false" @click="openAllowanceDialog">津贴账户/明细</ElButton>
            </template>
          </FaTableHeader>

          <FaTable
            ref="faTableRef"
            :loading="loading"
            :data="data"
            :columns="columns"
            :pagination="pagination"
            @selection-change="onTableSelectionChange"
            @pagination:size-change="handleSizeChange"
            @pagination:current-change="handleCurrentChange"
          />
        </ElCard>
      </ElTabPane>

      <!-- 发放结果：审核通过即归集，这里看到封顶后的实发与滚入下月的津贴 -->
      <ElTabPane label="发放结果" name="result">
        <FaSearchBar
          ref="resultSearchBarRef"
          v-model="resultSearchForm"
          :items="resultSearchItems"
          :is-expand="false"
          :show-expand="true"
          :show-reset="true"
          :show-search="true"
          @search="handleResultSearch"
          @reset="onResetResultSearch"
        />

        <ElCard class="fa-table-card" style="margin-top: 12px">
          <FaTableHeader v-model:columns="resultColumnChecks" :loading="resultLoading" @refresh="refreshResultData" />

          <FaTable
            :loading="resultLoading"
            :data="resultData"
            :columns="resultColumns"
            :pagination="resultPagination"
            @pagination:size-change="handleResultSizeChange"
            @pagination:current-change="handleResultCurrentChange"
          />
        </ElCard>
      </ElTabPane>
    </ElTabs>

    <!-- 新增发放额度配置对话框 -->
    <ElDialog v-model="createVisible" title="新增发放额度配置" width="520px" :close-on-click-modal="false">
      <FaForm
        ref="createFormRef"
        v-model="createForm"
        :items="createFormItems"
        :rules="createRules"
        label-suffix=":"
        :label-width="110"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="createSubmitting" @click="handleCreateSubmit">保存</ElButton>
      </template>
    </ElDialog>

    <!-- 编辑发放额度配置对话框（仅额度 + 启用可改） -->
    <ElDialog v-model="editVisible" title="修改发放额度配置" width="520px" :close-on-click-modal="false">
      <FaForm
        ref="editFormRef"
        v-model="editForm"
        :items="editFormItems"
        :rules="editRules"
        label-suffix=":"
        :label-width="110"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="editVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="editSubmitting" @click="handleEditSubmit">保存</ElButton>
      </template>
    </ElDialog>

    <!-- 津贴账户 / 明细对话框 -->
    <ElDialog v-model="allowanceVisible" title="个人任务津贴" width="760px">
      <ElTabs v-model="allowanceTab">
        <ElTabPane label="津贴账户" name="account">
          <ElTable :data="allowanceData" v-loading="allowanceLoading" size="small" border max-height="360px">
            <ElTableColumn type="index" label="#" width="48" />
            <ElTableColumn prop="user_id" label="用户" min-width="140">
              <template #default="{ row }">{{ userMap[row.user_id] ?? `#${row.user_id}` }}</template>
            </ElTableColumn>
            <ElTableColumn prop="balance" label="累计未发放金额" align="right" min-width="140" />
            <ElTableColumn prop="created_time" label="创建时间" width="168" />
          </ElTable>
        </ElTabPane>
        <ElTabPane label="津贴明细" name="detail">
          <ElTable :data="allowanceDetailData" v-loading="allowanceDetailLoading" size="small" border max-height="360px">
            <ElTableColumn type="index" label="#" width="48" />
            <ElTableColumn prop="user_id" label="用户" min-width="140">
              <template #default="{ row }">{{ userMap[row.user_id] ?? `#${row.user_id}` }}</template>
            </ElTableColumn>
            <ElTableColumn prop="from_period" label="来源周期" width="120" />
            <ElTableColumn prop="amount" label="未发放金额" align="right" width="120" />
            <ElTableColumn prop="status" label="状态" width="100">
              <template #default="{ row }">
                <FaStatusTag :type="allowanceStatusMap[row.status]?.type ?? 'info'" :label="allowanceStatusMap[row.status]?.text ?? (row.status ?? '—')" />
              </template>
            </ElTableColumn>
            <ElTableColumn prop="paid_at" label="发放时间" width="168">
              <template #default="{ row }">{{ row.paid_at ?? "—" }}</template>
            </ElTableColumn>
          </ElTable>
        </ElTabPane>
      </ElTabs>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import PayoutAPI, {
  type PayoutConfigTable,
  type PayoutResultTable,
  type AllowanceTable,
  type AllowanceDetailTable,
} from "@/api/module_market/payout";
import UserAPI from "@/api/module_system/user";
import { useDictStore } from "@stores";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";
import { useFormDraft } from "@/hooks/core/useFormDraft";

defineOptions({ name: "MarketPayout", inheritAttrs: false });

const dictStore = useDictStore();

/** 两个标签页：额度配置（可编辑）与发放结果（只读核算结果）
 *
 * 默认落在「发放结果」：额度配置天然可以是空的（没人配就用默认 20000），
 * 而发放结果是真实业务数据，先看到它才不会被误认为「页面坏了」。
 */
const activeTab = ref("result");

// ── 字典：津贴状态 ──
const allowanceStatusMap = computed<Record<string, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_allowance_status"] ?? []).map((d) => [
      d.dict_value!,
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);

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
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<PayoutConfigTable>();

const opCtx = {
  onEdit: (row: PayoutConfigTable) => void openEditDialog(row),
  onDelete: deleteRow,
};

function buildRowActions(row: PayoutConfigTable): TableOperationAction[] {
  return [
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:payout:update", run: () => opCtx.onEdit(row) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:payout:delete", run: () => opCtx.onDelete(row.id!, `${userMap.value[row.user_id!] ?? `#${row.user_id}`}(${row.period})`) },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshRemove } =
  useTable({
    core: {
      apiFn: PayoutAPI.listPayout,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<PayoutConfigTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "user_id", label: "用户", minWidth: 140, formatter: (row: PayoutConfigTable) => userMap.value[row.user_id!] ?? `#${row.user_id}` },
        { prop: "period", label: "周期", width: 100 },
        { prop: "payout_limit", label: "每月发放额度", width: 130, align: "right" },
        { prop: "enabled", label: "启用", width: 80, align: "center", formatter: (row: PayoutConfigTable) => (row.enabled ? "是" : "否") },
        { prop: "created_time", label: "配置时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 170, fixed: "right", align: "center", formatter: (row: PayoutConfigTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

// ── 发放结果（用户 × 周期的核算结果，只读）──
const resultSearchForm = ref<{ user_id?: number; period?: string }>({ user_id: undefined, period: undefined });
const resultSearchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const resultSearchItems = computed<SearchFormItem[]>(() => [
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "周期", key: "period", type: "input", placeholder: "如 2026-11", clearable: true, span: 8 },
]);

const amountText = (value?: number) => (value == null ? "—" : Number(value).toFixed(2));

/** 发放结果里的「用户」：优先用后端带回的昵称，拿不到才回退到 ID */
const resultUserLabel = (row: PayoutResultTable) => row.user?.name || (row.user_id ? `#${row.user_id}` : "—");

const {
  columns: resultColumns,
  columnChecks: resultColumnChecks,
  data: resultData,
  loading: resultLoading,
  pagination: resultPagination,
  getData: getResultData,
  replaceSearchParams: replaceResultSearchParams,
  resetSearchParams: resetResultSearchParams,
  handleSizeChange: handleResultSizeChange,
  handleCurrentChange: handleResultCurrentChange,
  refreshData: refreshResultData,
} = useTable({
  core: {
    apiFn: PayoutAPI.listPayoutResult,
    apiParams: { page_no: 1, page_size: 10 },
    columnsFactory: () => [
      { type: "globalIndex", width: 56, label: "序号" },
      { prop: "period", label: "周期", width: 100 },
      { prop: "user_name", label: "用户", minWidth: 140, formatter: (row: PayoutResultTable) => resultUserLabel(row) },
      { prop: "user.mobile", label: "手机号", width: 130, formatter: (row: PayoutResultTable) => row.user?.mobile ?? "—" },
      { prop: "payable", label: "应发金额", width: 120, align: "right", formatter: (row: PayoutResultTable) => amountText(row.payable) },
      { prop: "prev_balance", label: "期初津贴", width: 120, align: "right", formatter: (row: PayoutResultTable) => amountText(row.prev_balance) },
      { prop: "limit", label: "当月额度", width: 120, align: "right", formatter: (row: PayoutResultTable) => amountText(row.limit) },
      { prop: "paid", label: "实发金额", width: 120, align: "right", formatter: (row: PayoutResultTable) => amountText(row.paid) },
      { prop: "rollover", label: "滚入下月津贴", width: 140, align: "right", formatter: (row: PayoutResultTable) => amountText(row.rollover) },
    ],
  },
});

async function handleResultSearch(params: Record<string, unknown>) {
  replaceResultSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getResultData();
}

async function onResetResultSearch() {
  resultSearchForm.value = { user_id: undefined, period: undefined };
  await resetResultSearchParams();
}

// ── 新增发放额度配置 ──
const createVisible = ref(false);
const createSubmitting = ref(false);
const createFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const createForm = ref<{ user_id?: number; period?: string; payout_limit?: number; enabled: boolean }>({ user_id: undefined, period: undefined, payout_limit: undefined, enabled: true });

const createFormItems = computed<FormItem[]>(() => [
  { label: "用户", key: "user_id", type: "select", span: 24, props: { placeholder: "请选择 C 端用户", options: userOptions.value, filterable: true } },
  { label: "周期", key: "period", type: "input", span: 24, props: { placeholder: "自然月，如 2026-10", maxlength: 16 } },
  { label: "发放额度", key: "payout_limit", type: "number", span: 24, props: { min: 0, precision: 2, controlsPosition: "right", placeholder: "默认 20000，可调 10000/20000" } },
  { label: "是否启用", key: "enabled", type: "switch", span: 24 },
]);

const createRules = reactive({
  user_id: [{ required: true, message: "请选择用户", trigger: "change" }],
  period: [{ required: true, message: "请输入周期", trigger: "blur" }],
  payout_limit: [{ required: true, message: "请输入发放额度", trigger: "blur" }],
});

const payoutDraft = useFormDraft({
  key: "payout",
  dialogVisible: createVisible,
  form: createForm,
  blank: () => ({ user_id: undefined, period: undefined, payout_limit: undefined, enabled: true }),
});

function handleAdd() {
  payoutDraft.openCreate();
}

async function handleCreateSubmit() {
  if (!createFormRef.value) return;
  try {
    await createFormRef.value.validate();
  } catch {
    return;
  }
  if (!createForm.value.user_id || !createForm.value.period || createForm.value.payout_limit === undefined) return;
  createSubmitting.value = true;
  try {
    await PayoutAPI.createPayout({ user_id: createForm.value.user_id, period: createForm.value.period, payout_limit: createForm.value.payout_limit, enabled: createForm.value.enabled });
    payoutDraft.done();
    createVisible.value = false;
    await refreshCreate();
  } catch {
    // 错误已由拦截器提示
  } finally {
    createSubmitting.value = false;
  }
}

// ── 编辑发放额度配置 ──
const editVisible = ref(false);
const editSubmitting = ref(false);
const editFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const editForm = ref<{ id?: number; user_id?: number; period?: string; payout_limit?: number; enabled: boolean }>({ id: undefined, user_id: undefined, period: undefined, payout_limit: undefined, enabled: true });

const editFormItems = computed<FormItem[]>(() => [
  { label: "用户", key: "user_id", type: "input", span: 24, props: { disabled: true, placeholder: "用户" } },
  { label: "周期", key: "period", type: "input", span: 24, props: { disabled: true, placeholder: "周期" } },
  { label: "发放额度", key: "payout_limit", type: "number", span: 24, props: { min: 0, precision: 2, controlsPosition: "right", placeholder: "默认 20000，可调 10000/20000" } },
  { label: "是否启用", key: "enabled", type: "switch", span: 24 },
]);

const editRules = reactive({
  payout_limit: [{ required: true, message: "请输入发放额度", trigger: "blur" }],
});

function openEditDialog(row: PayoutConfigTable) {
  editForm.value = { id: row.id, user_id: row.user_id, period: row.period, payout_limit: row.payout_limit, enabled: row.enabled ?? true };
  editVisible.value = true;
}

async function handleEditSubmit() {
  if (!editFormRef.value) return;
  try {
    await editFormRef.value.validate();
  } catch {
    return;
  }
  if (editForm.value.id == null || editForm.value.payout_limit === undefined) return;
  editSubmitting.value = true;
  try {
    await PayoutAPI.updatePayout(editForm.value.id, { payout_limit: editForm.value.payout_limit, enabled: editForm.value.enabled });
    editVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    editSubmitting.value = false;
  }
}

async function deleteRow(id: number, name: string) {
  try {
    await confirmDelete(`确定删除「${name}」的发放额度配置吗？`);
    await PayoutAPI.deletePayout([id]);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return;
  try {
    await confirmBatchDelete(selectedIds.value.length, selectedRows.value.map((r) => `${userMap.value[r.user_id!] ?? `#${r.user_id}`}(${r.period})`));
    batchDeleting.value = true;
    await PayoutAPI.deletePayout(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

// ── 津贴账户 / 明细 ──
const allowanceVisible = ref(false);
const allowanceTab = ref("account");
const allowanceLoading = ref(false);
const allowanceDetailLoading = ref(false);
const allowanceData = ref<AllowanceTable[]>([]);
const allowanceDetailData = ref<AllowanceDetailTable[]>([]);

async function loadAllowance() {
  allowanceLoading.value = true;
  try {
    const res = await PayoutAPI.listAllowance({ page_no: 1, page_size: 100 });
    allowanceData.value = res.data.data.items;
  } finally {
    allowanceLoading.value = false;
  }
}

async function loadAllowanceDetail() {
  allowanceDetailLoading.value = true;
  try {
    const res = await PayoutAPI.listAllowanceDetail({ page_no: 1, page_size: 100 });
    allowanceDetailData.value = res.data.data.items;
  } finally {
    allowanceDetailLoading.value = false;
  }
}

async function openAllowanceDialog() {
  allowanceVisible.value = true;
  await Promise.all([loadAllowance(), loadAllowanceDetail()]);
}

async function loadOptions() {
  const userRes = await UserAPI.listUser({ page_no: 1, page_size: 100 });
  userOptions.value = userRes.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}` }));
  userMap.value = Object.fromEntries(userRes.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
}

onMounted(async () => {
  await dictStore.getDict(["market_allowance_status"]);
  await loadOptions();
});

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { user_id: undefined, period: undefined };
  await resetSearchParams();
}
</script>
