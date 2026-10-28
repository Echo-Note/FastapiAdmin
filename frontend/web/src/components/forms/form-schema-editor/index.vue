<!-- 采集字段可视化配置器（二级模板通用字段 / 三级任务采集字段共用）：
     按分节组织的字段编辑，字段形态含单值字段与 type=table 多行子表（columns 子列）。
     对齐后端 FormSchema 分节数组结构：FormSchemaSection[]（code 英文标识 + name 中文展示名 + required + fields）。 -->
<template>
  <div class="form-schema-editor">
    <div class="mb-2 flex items-center justify-between">
      <div class="flex gap-2">
        <ElButton type="primary" plain @click="handleAddSection">添加分节</ElButton>
        <ElButton @click="loadExample">载入示例</ElButton>
      </div>
      <span class="text-xs text-gray-500">共 {{ sections.length }} 个分节 / {{ totalFields }} 个字段</span>
    </div>

    <div v-for="(section, si) in sections" :key="section.code" class="mb-3 overflow-hidden rounded-md border border-gray-200">
      <div class="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-3 py-2">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-gray-700">{{ section.name }}{{ section.required ? "（必填）" : "" }}</span>
          <span class="text-xs text-gray-400">{{ section.code }}</span>
        </div>
        <div class="flex items-center gap-1">
          <ElButton link type="primary" size="small" @click="handleAddField(si)">添加字段</ElButton>
          <ElButton link size="small" @click="handleEditSection(si)">编辑分节</ElButton>
          <ElButton link type="danger" size="small" @click="handleRemoveSection(si)">删除分节</ElButton>
        </div>
      </div>

      <ElTable :data="section.fields" border size="small" class="w-full">
        <ElTableColumn label="显示名" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.field.label }}</template>
        </ElTableColumn>
        <ElTableColumn label="字段标识" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.name }}</template>
        </ElTableColumn>
        <ElTableColumn label="类型" width="90" align="center">
          <template #default="{ row }">{{ typeLabel(row.field.type) }}</template>
        </ElTableColumn>
        <ElTableColumn label="必填" width="60" align="center">
          <template #default="{ row }">
            <span :class="row.field.required ? 'text-red-500' : 'text-gray-400'">{{ row.field.required ? "是" : "否" }}</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="选项/子列" min-width="240">
          <template #default="{ row }">
            <template v-if="row.field.type === 'table'">
              <div v-for="col in row.field.columns ?? []" :key="col.name" class="flex items-center gap-1 py-0.5 text-xs">
                <span>{{ col.label }}</span>
                <span class="text-gray-400">{{ col.name }}</span>
                <span class="text-blue-400">{{ typeLabel(col.type) }}</span>
                <span v-if="col.required" class="text-red-400">必填</span>
              </div>
            </template>
            <span v-else-if="row.field.options?.length">{{ row.field.options.map((o: FormSchemaOption) => o.label).join("、") }}</span>
            <span v-else class="text-gray-400">—</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="190" align="center" fixed="right">
          <template #default="{ $index }">
            <ElButton link type="primary" @click="handleEditField(si, $index)">编辑</ElButton>
            <ElButton link :disabled="$index === 0" @click="moveField(si, $index, -1)">上移</ElButton>
            <ElButton link :disabled="$index === section.fields.length - 1" @click="moveField(si, $index, 1)">下移</ElButton>
            <ElButton link type="danger" @click="handleRemoveField(si, $index)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <!-- 分节编辑对话框（新增/编辑） -->
    <ElDialog v-model="sectionDialogVisible" :title="sectionDialogMode === 'edit' ? '编辑分节' : '添加分节'" width="440px" append-to-body :close-on-click-modal="false">
      <ElForm :model="sectionEditing" label-width="86px">
        <ElFormItem label="分节标识" required>
          <ElInput v-model="sectionEditing.code" placeholder="如 execution_info（英文/拼音，勿重复）" maxlength="64" />
        </ElFormItem>
        <ElFormItem label="分节名" required>
          <ElInput v-model="sectionEditing.name" placeholder="如 执行信息" maxlength="128" />
        </ElFormItem>
        <ElFormItem label="是否必填">
          <ElSwitch v-model="sectionEditing.required" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="sectionDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="saveSection">确定</ElButton>
      </template>
    </ElDialog>

    <!-- 字段编辑对话框（新增/编辑） -->
    <ElDialog v-model="editorVisible" :title="editingFieldIndex >= 0 ? '编辑字段' : '添加字段'" width="640px" append-to-body :close-on-click-modal="false">
      <ElForm :model="editing" label-width="86px">
        <ElFormItem label="显示名" required>
          <ElInput v-model="editing.label" placeholder="如 医院名称" maxlength="128" />
        </ElFormItem>
        <ElFormItem label="字段标识" required>
          <ElInput v-model="editing.name" placeholder="如 hospital_name（英文/拼音，勿重复）" maxlength="64" />
        </ElFormItem>
        <ElFormItem label="类型" required>
          <ElSelect v-model="editing.type" class="w-full">
            <ElOption v-for="t in FIELD_TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="是否必填">
          <ElSwitch v-model="editing.required" />
        </ElFormItem>
        <ElFormItem v-if="!needsColumns" label="占位提示">
          <ElInput v-model="editing.placeholder" placeholder="输入框占位提示" maxlength="255" />
        </ElFormItem>
        <ElFormItem v-if="needsOptions" label="选项">
          <div class="w-full space-y-2">
            <div v-for="(opt, i) in editing.options" :key="i" class="flex items-center gap-2">
              <ElInput v-model="opt.label" placeholder="显示名" class="flex-1" />
              <ElInput v-model="opt.value" placeholder="值" class="flex-1" />
              <ElButton link type="danger" @click="removeOption(i)">删除</ElButton>
            </div>
            <ElButton link type="primary" @click="addOption">+ 添加选项</ElButton>
          </div>
        </ElFormItem>
        <ElFormItem v-if="needsColumns" label="子表列">
          <div class="w-full space-y-2">
            <div v-for="(col, i) in editing.columns" :key="i" class="flex items-center gap-2">
              <ElInput v-model="col.label" placeholder="列显示名(如 产品名称)" class="w-36" maxlength="128" />
              <ElInput v-model="col.name" placeholder="列标识(如 product_name)" class="w-40" maxlength="64" />
              <ElSelect v-model="col.type" class="w-28">
                <ElOption v-for="t in COLUMN_TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
              </ElSelect>
              <ElCheckbox v-model="col.required">必填</ElCheckbox>
              <ElButton link type="danger" @click="removeColumn(i)">删除</ElButton>
            </div>
            <ElButton link type="primary" @click="addColumn">+ 添加子列</ElButton>
          </div>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editorVisible = false">取消</ElButton>
        <ElButton type="primary" @click="saveField">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type {
  FormSchema,
  FormSchemaColumn,
  FormSchemaField,
  FormSchemaFieldType,
  FormSchemaOption,
} from "@/api/module_market/form-schema";

defineOptions({ name: "FormSchemaEditor" });

const props = defineProps<{ modelValue?: FormSchema }>();
const emit = defineEmits<{ (e: "update:modelValue", value: FormSchema): void }>();

/** 字段行：字段名 + 字段定义 */
interface FieldRow {
  name: string;
  field: FormSchemaField;
}
/** 分节行：英文标识 + 中文名 + 必填标记 + 其下字段有序列表 */
interface SectionRow {
  code: string;
  name: string;
  required: boolean;
  fields: FieldRow[];
}

/** 字段类型下拉选项（table 为分节内多行子表） */
const FIELD_TYPE_OPTIONS: { value: FormSchemaFieldType; label: string }[] = [
  { value: "text", label: "单行文本" },
  { value: "textarea", label: "多行文本" },
  { value: "number", label: "数字" },
  { value: "date", label: "日期" },
  { value: "select", label: "下拉单选" },
  { value: "radio", label: "单选按钮" },
  { value: "checkbox", label: "多选" },
  { value: "image", label: "图片上传" },
  { value: "file", label: "文件附件" },
  { value: "table", label: "多行子表" },
];

/** 子列类型下拉选项（不允许 table，防无限嵌套） */
const COLUMN_TYPE_OPTIONS: { value: Exclude<FormSchemaFieldType, "table">; label: string }[] = [
  { value: "text", label: "单行文本" },
  { value: "textarea", label: "多行文本" },
  { value: "number", label: "数字" },
  { value: "date", label: "日期" },
  { value: "select", label: "下拉单选" },
  { value: "radio", label: "单选按钮" },
  { value: "checkbox", label: "多选" },
  { value: "image", label: "图片上传" },
  { value: "file", label: "文件附件" },
];

/** 示例结构（点击「载入示例」一键填入） */
const EXAMPLE_SCHEMA: FormSchema = [
  {
    code: "execution_info",
    name: "执行信息",
    required: true,
    fields: {
      region: { label: "区域", type: "text", required: true, placeholder: "如 重庆市渝中区" },
      hospital_name: { label: "医院名称", type: "text", required: true, placeholder: "请输入医院完整名称" },
    },
  },
  {
    code: "price_check",
    name: "价格核查",
    required: true,
    fields: {
      price_items: {
        label: "价格明细",
        type: "table",
        columns: [
          { name: "product_name", label: "产品名称", type: "text", required: true },
          { name: "retail_price", label: "零售价", type: "number" },
        ],
      },
      exception_note: { label: "异常说明", type: "textarea" },
    },
  },
  {
    code: "management_verification",
    name: "管理核实",
    required: true,
    fields: {
      door_photo: { label: "打卡照片", type: "image", required: true },
    },
  },
];

function parseSchema(schema: FormSchema): SectionRow[] {
  return (schema ?? []).map((section) => ({
    code: section.code,
    name: section.name,
    required: section.required ?? false,
    fields: Object.entries(section.fields ?? {}).map(([name, field]) => ({ name, field: JSON.parse(JSON.stringify(field)) })),
  }));
}

function serializeSchema(list: SectionRow[]): FormSchema {
  return list.map((section) => ({
    code: section.code,
    name: section.name,
    ...(section.required ? { required: true } : {}),
    fields: Object.fromEntries(section.fields.map(({ name, field }) => [name, field])),
  }));
}

const sections = computed<SectionRow[]>({
  get: () => parseSchema(props.modelValue ?? []),
  set: (val) => emit("update:modelValue", serializeSchema(val)),
});

const totalFields = computed(() => sections.value.reduce((n, s) => n + s.fields.length, 0));

function mutateSections(fn: (draft: SectionRow[]) => void) {
  const draft = sections.value;
  fn(draft);
  sections.value = draft;
}

function typeLabel(type: FormSchemaFieldType): string {
  return FIELD_TYPE_OPTIONS.find((t) => t.value === type)?.label ?? type;
}

// ── 分节编辑 ──
const sectionDialogVisible = ref(false);
const sectionDialogMode = ref<"create" | "edit">("create");
const sectionEditingIndex = ref(-1);
const sectionEditing = reactive({ code: "", name: "", required: false });

function handleAddSection() {
  sectionDialogMode.value = "create";
  sectionEditingIndex.value = -1;
  sectionEditing.code = "";
  sectionEditing.name = "";
  sectionEditing.required = false;
  sectionDialogVisible.value = true;
}

function handleEditSection(index: number) {
  sectionDialogMode.value = "edit";
  sectionEditingIndex.value = index;
  sectionEditing.code = sections.value[index]!.code;
  sectionEditing.name = sections.value[index]!.name;
  sectionEditing.required = sections.value[index]!.required;
  sectionDialogVisible.value = true;
}

function handleRemoveSection(index: number) {
  mutateSections((draft) => draft.splice(index, 1));
}

function saveSection() {
  const code = sectionEditing.code.trim();
  const name = sectionEditing.name.trim();
  if (!code) return void ElMessage.warning("请输入分节标识");
  if (!name) return void ElMessage.warning("请输入分节名");
  if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(code)) return void ElMessage.warning("分节标识需以字母开头，仅含字母/数字/下划线");
  const duplicate = sections.value.some((s, i) => s.code === code && i !== sectionEditingIndex.value);
  if (duplicate) return void ElMessage.warning("分节标识已存在，请勿重复");

  if (sectionDialogMode.value === "edit") {
    mutateSections((draft) => {
      draft[sectionEditingIndex.value]!.code = code;
      draft[sectionEditingIndex.value]!.name = name;
      draft[sectionEditingIndex.value]!.required = sectionEditing.required;
    });
  } else {
    mutateSections((draft) => draft.push({ code, name, required: sectionEditing.required, fields: [] }));
  }
  sectionDialogVisible.value = false;
}

// ── 字段编辑 ──
const editorVisible = ref(false);
const editingSectionIndex = ref(-1);
const editingFieldIndex = ref(-1); // -1 表示新增
const editing = reactive<{
  name: string;
  label: string;
  type: FormSchemaFieldType;
  required: boolean;
  placeholder: string;
  options: FormSchemaOption[];
  columns: FormSchemaColumn[];
}>({ name: "", label: "", type: "text", required: false, placeholder: "", options: [], columns: [] });

const needsOptions = computed(() => ["select", "radio", "checkbox"].includes(editing.type));
const needsColumns = computed(() => editing.type === "table");

function resetEditing() {
  editing.name = "";
  editing.label = "";
  editing.type = "text";
  editing.required = false;
  editing.placeholder = "";
  editing.options = [];
  editing.columns = [];
}

function handleAddField(sectionIndex: number) {
  editingSectionIndex.value = sectionIndex;
  editingFieldIndex.value = -1;
  resetEditing();
  editorVisible.value = true;
}

function handleEditField(sectionIndex: number, fieldIndex: number) {
  editingSectionIndex.value = sectionIndex;
  editingFieldIndex.value = fieldIndex;
  const row = sections.value[sectionIndex]!.fields[fieldIndex]!;
  editing.name = row.name;
  editing.label = row.field.label;
  editing.type = row.field.type;
  editing.required = row.field.required ?? false;
  editing.placeholder = row.field.placeholder ?? "";
  editing.options = (row.field.options ?? []).map((o) => ({ ...o }));
  editing.columns = (row.field.columns ?? []).map((c) => JSON.parse(JSON.stringify(c)));
  editorVisible.value = true;
}

function addOption() {
  editing.options.push({ label: "", value: "" });
}

function removeOption(i: number) {
  editing.options.splice(i, 1);
}

function addColumn() {
  editing.columns.push({ name: "", label: "", type: "text", required: false });
}

function removeColumn(i: number) {
  editing.columns.splice(i, 1);
}

function saveField() {
  const label = editing.label.trim();
  if (!label) return void ElMessage.warning("请输入显示名");
  const name = editing.name.trim();
  if (!name) return void ElMessage.warning("请输入字段标识");
  if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return void ElMessage.warning("字段标识需以字母开头，仅含字母/数字/下划线");

  const section = sections.value[editingSectionIndex.value];
  if (!section) return;
  const duplicate = section.fields.some((f, i) => f.name === name && i !== editingFieldIndex.value);
  if (duplicate) return void ElMessage.warning("字段标识已存在，请勿重复");

  let field: FormSchemaField;
  if (needsColumns.value) {
    // 多行子表：校验并收集子列
    const columns: FormSchemaColumn[] = [];
    for (const col of editing.columns) {
      const colLabel = col.label.trim();
      const colName = col.name.trim();
      if (!colLabel) return void ElMessage.warning("子列显示名不能为空");
      if (!colName) return void ElMessage.warning("子列标识不能为空");
      if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(colName)) return void ElMessage.warning(`子列标识 ${colName} 需以字母开头，仅含字母/数字/下划线`);
      if (columns.some((c) => c.name === colName)) return void ElMessage.warning(`子列标识 ${colName} 重复`);
      columns.push({
        name: colName,
        label: colLabel,
        type: col.type,
        ...(col.required ? { required: true } : {}),
      });
    }
    if (columns.length === 0) return void ElMessage.warning("多行子表至少需要一个子列");
    field = { label, type: "table", columns };
  } else {
    field = {
      label,
      type: editing.type,
      required: editing.required,
      placeholder: editing.placeholder.trim() || undefined,
      options: needsOptions.value
        ? editing.options.filter((o) => o.label.trim() || o.value.trim()).map((o) => ({ label: o.label.trim(), value: o.value.trim() }))
        : undefined,
    };
  }

  mutateSections((draft) => {
    const target = draft[editingSectionIndex.value]!;
    if (editingFieldIndex.value >= 0) {
      target.fields[editingFieldIndex.value] = { name, field };
    } else {
      target.fields.push({ name, field });
    }
  });
  editorVisible.value = false;
}

function handleRemoveField(sectionIndex: number, fieldIndex: number) {
  mutateSections((draft) => draft[sectionIndex]!.fields.splice(fieldIndex, 1));
}

function moveField(sectionIndex: number, fieldIndex: number, dir: -1 | 1) {
  mutateSections((draft) => {
    const fields = draft[sectionIndex]!.fields;
    const target = fieldIndex + dir;
    if (target < 0 || target >= fields.length) return;
    const a = fields[fieldIndex]!;
    fields[fieldIndex] = fields[target]!;
    fields[target] = a;
  });
}

function loadExample() {
  sections.value = parseSchema(EXAMPLE_SCHEMA);
}
</script>
