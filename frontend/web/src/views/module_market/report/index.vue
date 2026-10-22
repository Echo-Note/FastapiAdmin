<!-- 报告打包：列表 + 生成 + 详情 -->
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
          <FaTableHeaderLeft
            :perm-create="['module_market:report:add']"
            create-text="生成报告"
            @add="openGenerateDialog"
          />
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

    <!-- 生成报告对话框 -->
    <ElDialog v-model="generateVisible" title="生成报告" width="520px" :close-on-click-modal="false" @closed="resetGenerateForm">
      <FaForm
        ref="generateFormRef"
        v-model="generateForm"
        :items="generateFormItems"
        :rules="generateRules"
        label-suffix=":"
        :label-width="100"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="generateVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="generateSubmitting" @click="handleGenerateSubmit">生成</ElButton>
      </template>
    </ElDialog>

    <!-- 详情对话框 -->
    <ElDialog v-model="detailVisible" title="报告详情" width="720px">
      <FaDescriptions :column="4" :data="detailData" :items="detailItems" />
      <ElDivider content-position="left">汇总数据</ElDivider>
      <pre class="form-data-pre">{{ formattedSummary }}</pre>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import ReportAPI, { type ReportTable } from "@/api/module_market/report";
import CompanyAPI from "@/api/module_market/company";
import { REPORT_STATUS_MAP } from "@/api/module_market/constants";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketReport", inheritAttrs: false });

const searchForm = ref<{ company_id?: number; period?: string; status?: string }>({ company_id: undefined, period: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const companyOptions = ref<OptionType[]>([]);
const statusOptions = computed<OptionType[]>(() => Object.entries(REPORT_STATUS_MAP).map(([value, v]) => ({ value, label: v.text })));

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "委托公司", key: "company_id", type: "select", props: { placeholder: "请选择医药公司", options: companyOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "周期", key: "period", type: "input", placeholder: "如 2026-10", clearable: true, span: 8 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 8 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);

const opCtx = {
  onDetail: (id: number) => void openDetail(id),
};

function buildRowActions(row: ReportTable): TableOperationAction[] {
  return [{ key: "detail", label: "详情", artType: "view", perm: "module_market:report:query", run: () => opCtx.onDetail(row.id!) }];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData } =
  useTable({
    core: {
      apiFn: ReportAPI.listReport,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<ReportTable>(() => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "company", label: "委托公司", minWidth: 150, formatter: (row: ReportTable) => row.company?.name ?? "—" },
        { prop: "period", label: "周期", width: 90 },
        { prop: "status", label: "状态", width: 92, status: REPORT_STATUS_MAP },
        { prop: "attachment", label: "附件", minWidth: 140, showOverflowTooltip: true, formatter: (row: ReportTable) => row.attachment ?? "—" },
        { prop: "created_time", label: "生成时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 90, fixed: "right", align: "center", formatter: (row: ReportTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailVisible = ref(false);
const detailData = ref<Partial<ReportTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "委托公司", prop: "company.name" },
  { label: "周期", prop: "period" },
  { label: "状态", prop: "status", tag: { map: REPORT_STATUS_MAP } },
  { label: "附件", prop: "attachment" },
  { label: "生成时间", prop: "created_time" },
];

const formattedSummary = computed(() => (detailData.value.summary ? JSON.stringify(detailData.value.summary, null, 2) : "—"));

async function openDetail(id: number) {
  const res = await ReportAPI.detailReport(id);
  detailData.value = res.data.data;
  detailVisible.value = true;
}

// ── 生成报告 ──
const generateVisible = ref(false);
const generateSubmitting = ref(false);
const generateFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const generateForm = ref<{ company_id?: number; period?: string }>({ company_id: undefined, period: undefined });

const generateFormItems = computed<FormItem[]>(() => [
  { label: "委托公司", key: "company_id", type: "select", span: 24, props: { placeholder: "请选择医药公司", options: companyOptions.value, filterable: true } },
  { label: "周期", key: "period", type: "input", span: 24, props: { placeholder: "自然月，如 2026-10", maxlength: 16 } },
]);

const generateRules = reactive({
  company_id: [{ required: true, message: "请选择委托公司", trigger: "change" }],
  period: [{ required: true, message: "请输入周期", trigger: "blur" }],
});

function openGenerateDialog() {
  generateVisible.value = true;
}

function resetGenerateForm() {
  generateForm.value = { company_id: undefined, period: undefined };
}

async function handleGenerateSubmit() {
  if (!generateFormRef.value) return;
  try {
    await generateFormRef.value.validate();
  } catch {
    return;
  }
  if (!generateForm.value.company_id || !generateForm.value.period) return;
  generateSubmitting.value = true;
  try {
    await ReportAPI.generateReport({ company_id: generateForm.value.company_id, period: generateForm.value.period });
    generateVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    generateSubmitting.value = false;
  }
}

async function loadOptions() {
  const companyRes = await CompanyAPI.listCompany({ page_no: 1, page_size: 100 });
  companyOptions.value = companyRes.data.data.items.map((c) => ({ value: c.id!, label: c.name ?? "" }));
}

onMounted(loadOptions);

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { company_id: undefined, period: undefined, status: undefined };
  await resetSearchParams();
}
</script>

<style scoped>
.form-data-pre {
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  max-height: 300px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
