<!-- C 端成员管理：market_member 档案（存在即 C 端），支持纳入与启停 -->
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
          <FaTableHeaderLeft :perm-create="['module_market:member:create']" create-text="纳入 C 端成员" @add="handleAdd" />
        </template>
      </FaTableHeader>

      <FaTable
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>

    <!-- 纳入 C 端成员 -->
    <ElDialog v-model="createVisible" title="纳入 C 端成员" width="520px" :close-on-click-modal="false">
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
  </div>
</template>

<script setup lang="ts">
import MemberAPI, { type MemberTable } from "@/api/module_market/member";
import UserAPI from "@/api/module_system/user";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";
import { useFormDraft } from "@/hooks/core/useFormDraft";

defineOptions({ name: "MarketMember", inheritAttrs: false });

/** 成员状态：只有启用/停用两态，不值得单开字典 */
const memberStatusMap = computed<Record<string, { type: StatusType; text: string }>>(() => ({
  ACTIVE: { type: "success", text: "启用" },
  DISABLED: { type: "info", text: "停用" },
}));
const statusOptions = [
  { value: "ACTIVE", label: "启用" },
  { value: "DISABLED", label: "停用" },
];

const searchForm = ref<{ user_id?: number; member_no?: string; status?: string }>({
  user_id: undefined,
  member_no: undefined,
  status: undefined,
});
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "成员编号", key: "member_no", type: "input", placeholder: "如 U-0001", clearable: true, span: 8 },
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions, clearable: true }, span: 8 },
]);

const opCtx = {
  onToggle: (row: MemberTable) => void toggleStatus(row),
};

/** 成员显示名：昵称（手机号），拿不到才回退到 ID */
function memberLabel(row: MemberTable): string {
  const name = row.user?.name || userMap.value[row.user_id!] || `#${row.user_id}`;
  const mobile = row.user?.mobile;
  return mobile ? `${name}（${mobile}）` : name;
}

function buildRowActions(row: MemberTable): TableOperationAction[] {
  const active = row.status === "ACTIVE";
  return [
    {
      key: "toggle",
      label: active ? "停用" : "启用",
      artType: "edit",
      perm: "module_market:member:update",
      run: () => opCtx.onToggle(row),
    },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate } =
  useTable({
    core: {
      apiFn: MemberAPI.listMember,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<MemberTable>(() => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "member_no", label: "成员编号", width: 120 },
        { prop: "user_name", label: "用户", minWidth: 180, formatter: (row: MemberTable) => memberLabel(row) },
        { prop: "user.username", label: "登录账号", minWidth: 130, formatter: (row: MemberTable) => row.user?.username ?? "—" },
        { prop: "user.mobile", label: "手机号", width: 130, formatter: (row: MemberTable) => row.user?.mobile ?? "—" },
        { prop: "status", label: "状态", width: 90, status: memberStatusMap.value },
        { prop: "created_time", label: "建档时间", width: 168, showOverflowTooltip: true },
        {
          prop: "operation",
          label: "操作",
          width: 110,
          fixed: "right",
          align: "center",
          formatter: (row: MemberTable) =>
            renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }),
        },
      ]),
    },
  });

// ── 纳入 C 端成员 ──
const createVisible = ref(false);
const createSubmitting = ref(false);
const createFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const createForm = ref<{ user_id?: number; status: string }>({ user_id: undefined, status: "ACTIVE" });

const createFormItems = computed<FormItem[]>(() => [
  { label: "用户", key: "user_id", type: "select", span: 24, props: { placeholder: "选择要纳入 C 端的系统用户", options: userOptions.value, filterable: true } },
  { label: "状态", key: "status", type: "select", span: 24, props: { options: statusOptions } },
]);

const createRules = reactive({
  user_id: [{ required: true, message: "请选择用户", trigger: "change" }],
  status: [{ required: true, message: "请选择状态", trigger: "change" }],
});

const memberDraft = useFormDraft({
  key: "member",
  dialogVisible: createVisible,
  form: createForm,
  blank: () => ({ user_id: undefined, status: "ACTIVE" }),
});

function handleAdd() {
  memberDraft.openCreate();
}

async function handleCreateSubmit() {
  if (!createFormRef.value) return;
  try {
    await createFormRef.value.validate();
  } catch {
    return;
  }
  if (!createForm.value.user_id) return;
  createSubmitting.value = true;
  try {
    await MemberAPI.createMember({ user_id: createForm.value.user_id, status: createForm.value.status });
    memberDraft.done();
    createVisible.value = false;
    await refreshCreate();
  } catch {
    // 错误已由拦截器提示
  } finally {
    createSubmitting.value = false;
  }
}

async function toggleStatus(row: MemberTable) {
  const next = row.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
  const action = next === "DISABLED" ? "停用" : "启用";
  try {
    await ElMessageBox.confirm(
      next === "DISABLED"
        ? `停用后「${memberLabel(row)}」将无法再接单或提交成果，历史数据保留。确定停用吗？`
        : `确定启用「${memberLabel(row)}」吗？`,
      `${action}成员`,
      { type: "warning" },
    );
    await MemberAPI.updateMember(row.id!, { status: next });
    await refreshData();
  } catch {
    // 用户取消
  }
}

async function loadOptions() {
  const res = await UserAPI.listUser({ page_no: 1, page_size: 100 });
  userOptions.value = res.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}（${u.username ?? ""}）` }));
  userMap.value = Object.fromEntries(res.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
}

onMounted(async () => {
  await loadOptions();
});

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { user_id: undefined, member_no: undefined, status: undefined };
  await resetSearchParams();
}
</script>
