<!-- 采集字段 Schema 可视化配置器：运营人员可视化增删改采集字段，替代手写 JSON -->
<template>
  <div class="form-schema-editor">
    <div class="mb-2 flex items-center justify-between">
      <div class="flex gap-2">
        <ElButton type="primary" plain @click="handleAdd">添加字段</ElButton>
        <ElButton @click="loadExample">载入示例</ElButton>
      </div>
      <span class="text-xs text-gray-500">共 {{ fields.length }} 个字段</span>
    </div>

    <ElTable :data="fields" border size="small" class="w-full">
      <ElTableColumn type="index" label="序" width="50" align="center" />
      <ElTableColumn label="显示名" prop="label" min-width="110" show-overflow-tooltip />
      <ElTableColumn label="字段标识" prop="name" min-width="120" show-overflow-tooltip />
      <ElTableColumn label="类型" width="90" align="center">
        <template #default="{ row }">{{ typeLabel(row.type) }}</template>
      </ElTableColumn>
      <ElTableColumn label="必填" width="60" align="center">
        <template #default="{ row }">
          <span :class="row.required ? 'text-red-500' : 'text-gray-400'">{{ row.required ? "是" : "否" }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="选项" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.options?.length">{{ row.options.map((o: FormSchemaOption) => o.label).join("、") }}</span>
          <span v-else class="text-gray-400">—</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="190" align="center" fixed="right">
        <template #default="{ $index }">
          <ElButton link type="primary" @click="handleEdit($index)">编辑</ElButton>
          <ElButton link :disabled="$index === 0" @click="move($index, -1)">上移</ElButton>
          <ElButton link :disabled="$index === fields.length - 1" @click="move($index, 1)">下移</ElButton>
          <ElButton link type="danger" @click="handleDelete($index)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog
      v-model="editorVisible"
      :title="editingIndex >= 0 ? '编辑字段' : '添加字段'"
      width="560px"
      append-to-body
      :close-on-click-modal="false"
    >
      <ElForm :model="editing" label-width="86px">
        <ElFormItem label="显示名" required>
          <ElInput v-model="editing.label" placeholder="如 医院名称" maxlength="128" />
        </ElFormItem>
        <ElFormItem label="字段标识" required>
          <ElInput v-model="editing.name" placeholder="如 hospital_name（英文/拼音，勿重复）" maxlength="64" />
        </ElFormItem>
        <ElFormItem label="类型" required>
          <ElSelect v-model="editing.type" class="w-full" @change="handleTypeChange">
            <ElOption v-for="t in FIELD_TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="是否必填">
          <ElSwitch v-model="editing.required" />
        </ElFormItem>
        <ElFormItem label="占位提示">
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
      </ElForm>
      <template #footer>
        <ElButton @click="editorVisible = false">取消</ElButton>
        <ElButton type="primary" @click="saveField">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import type { FormSchemaField, FormSchemaFieldType, FormSchemaOption } from "@/api/module_market/task-type";

defineOptions({ name: "FormSchemaEditor" });

const props = defineProps<{ modelValue?: FormSchemaField[] }>();
const emit = defineEmits<{ (e: "update:modelValue", value: FormSchemaField[]): void }>();

/** 字段类型下拉选项 */
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
];

/** 示例字段（点击「载入示例」一键填入，供运营人员参考） */
const EXAMPLE_FIELDS: FormSchemaField[] = [
  { name: "region", label: "区域", type: "text", required: true, placeholder: "如 重庆市渝中区" },
  { name: "hospital_name", label: "医院名称", type: "text", required: true, placeholder: "请输入医院完整名称" },
  { name: "product_name", label: "产品名称", type: "text", required: true },
  { name: "admission_result", label: "准入结果", type: "select", required: true, options: [{ label: "已入院", value: "已入院" }, { label: "已采购", value: "已采购" }] },
  { name: "pass_date", label: "通过日期", type: "date" },
  { name: "purchase_qty", label: "采购数量", type: "number" },
  { name: "checkin_photo", label: "打卡照片", type: "image", required: true },
];

const fields = computed<FormSchemaField[]>({
  get: () => props.modelValue ?? [],
  set: (val) => emit("update:modelValue", val),
});

const editorVisible = ref(false);
const editingIndex = ref(-1);
const editing = ref<FormSchemaField>(emptyField());

function emptyField(): FormSchemaField {
  return { name: "", label: "", type: "text", required: false, placeholder: "", options: [] };
}

const needsOptions = computed(() => ["select", "radio", "checkbox"].includes(editing.value.type));

function typeLabel(type: FormSchemaFieldType): string {
  return FIELD_TYPE_OPTIONS.find((t) => t.value === type)?.label ?? type;
}

function handleAdd() {
  editingIndex.value = -1;
  editing.value = emptyField();
  editorVisible.value = true;
}

function handleEdit(index: number) {
  editingIndex.value = index;
  const src = fields.value[index]!;
  editing.value = {
    name: src.name,
    label: src.label,
    type: src.type,
    required: src.required ?? false,
    placeholder: src.placeholder ?? "",
    options: src.options ? src.options.map((o) => ({ ...o })) : [],
  };
  editorVisible.value = true;
}

function handleTypeChange() {
  if (needsOptions.value && !editing.value.options) {
    editing.value.options = [];
  }
}

function addOption() {
  if (!editing.value.options) editing.value.options = [];
  editing.value.options.push({ label: "", value: "" });
}

function removeOption(i: number) {
  editing.value.options?.splice(i, 1);
}

function saveField() {
  const name = editing.value.name.trim();
  const label = editing.value.label.trim();
  if (!label) return void ElMessage.warning("请输入显示名");
  if (!name) return void ElMessage.warning("请输入字段标识");
  const duplicate = fields.value.some((f, i) => f.name === name && i !== editingIndex.value);
  if (duplicate) return void ElMessage.warning("字段标识已存在，请勿重复");

  const field: FormSchemaField = {
    name,
    label,
    type: editing.value.type,
    required: editing.value.required,
    placeholder: editing.value.placeholder?.trim() || undefined,
    options: needsOptions.value
      ? (editing.value.options ?? []).filter((o) => o.label.trim() || o.value.trim()).map((o) => ({ label: o.label.trim(), value: o.value.trim() }))
      : undefined,
  };

  const next = [...fields.value];
  if (editingIndex.value >= 0) next[editingIndex.value] = field;
  else next.push(field);
  fields.value = next;
  editorVisible.value = false;
}

function handleDelete(index: number) {
  const next = [...fields.value];
  next.splice(index, 1);
  fields.value = next;
}

function move(index: number, dir: -1 | 1) {
  const target = index + dir;
  if (target < 0 || target >= fields.value.length) return;
  const next = [...fields.value];
  const a = next[index]!;
  next[index] = next[target]!;
  next[target] = a;
  fields.value = next;
}

function loadExample() {
  fields.value = EXAMPLE_FIELDS.map((f) => ({ ...f, options: f.options?.map((o) => ({ ...o })) }));
}
</script>
