<script setup lang="ts">
import type { FormSchemaField, InstitutionItem } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'

definePage({ name: 'market-submission-form', style: { navigationBarTitleText: '提交成果' } })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

const assignmentId = ref<number>()
const taskNo = ref('')
const formLoading = ref(false)
const formSchema = ref<FormSchemaField[]>([])
const formData = reactive<Record<string, any>>({})

const institutionId = ref<number>()
const institutions = ref<InstitutionItem[]>([])
const region = ref('')
const archiveNo = ref('')

const showInstitutionPicker = ref(false)
const institutionColumns = computed(() => [institutions.value.map(i => ({ value: i.id, label: i.name }))])

/** 动态下拉字段选择器 */
const activeField = ref<FormSchemaField | null>(null)
const showFieldPicker = ref(false)
const fieldPickerColumns = computed(() => [(activeField.value?.options ?? []).map(o => ({ value: o.value, label: o.label }))])

const submitting = ref(false)

/** 是否为分节标题（纯分组，不渲染输入项） */
function isSection(field: FormSchemaField) {
  return field.type === 'section'
}

/** 是否为多行子表 */
function isTable(field: FormSchemaField) {
  return field.type === 'table'
}

/** 简单输入字段（排除 section 分节标题与 table 子表） */
const simpleFields = computed(() => formSchema.value.filter(f => !isSection(f) && !isTable(f)))
const tableFields = computed(() => formSchema.value.filter(isTable))

function isRequired(field: FormSchemaField) {
  return field.required === true
}

/** 动态字段是否使用选择器（select / radio） */
function usePicker(field: FormSchemaField) {
  return field.type === 'select' || field.type === 'radio' || !!field.options?.length
}

function openInstitutionPicker() {
  if (institutions.value.length === 0)
    return
  showInstitutionPicker.value = true
}

function onInstitutionConfirm(e: { value: Array<string | number> }) {
  const item = institutions.value.find(i => String(i.id) === String(e.value[0]))
  if (item)
    institutionId.value = item.id
  showInstitutionPicker.value = false
}

function openFieldPicker(field: FormSchemaField) {
  if (!field.options?.length)
    return
  activeField.value = field
  showFieldPicker.value = true
}

function onFieldPickerConfirm(e: { value: Array<string | number> }) {
  if (activeField.value?.name)
    formData[activeField.value.name] = e.value[0]
  showFieldPicker.value = false
}

function fieldLabel(field: FormSchemaField) {
  return field.label || field.name || ''
}

function fieldValueText(field: FormSchemaField) {
  if (!field.name)
    return ''
  const v = formData[field.name]
  if (v === undefined || v === null || v === '')
    return ''
  if (usePicker(field)) {
    const opt = field.options?.find(o => String(o.value) === String(v))
    return opt?.label ?? String(v)
  }
  return String(v)
}

/** 当前正在上传的字段名（防止重复上传） */
const uploadingField = ref('')

/** 解析上传响应，返回 file_url，失败提示并返回 null */
function parseUploadUrl(result: UniApp.UploadFileSuccessCallbackResult): string | null {
  try {
    const parsed = JSON.parse(result.data) as { code: number, msg?: string, data?: { file_url?: string } }
    if (parsed.code === 0 && parsed.data?.file_url)
      return parsed.data.file_url
    toast.error(parsed.msg || '上传失败')
  }
  catch {
    toast.error('上传失败')
  }
  return null
}

/** 选择并上传图片（image 字段） */
function chooseAndUploadImage(field: FormSchemaField) {
  if (uploadingField.value || !field.name)
    return
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    success: async (res) => {
      const filePath = res.tempFilePaths?.[0]
      if (!filePath)
        return
      uploadingField.value = field.name!
      try {
        const result = await MarketAPI.uploadFile(filePath)
        const url = parseUploadUrl(result)
        if (url)
          formData[field.name!] = url
      }
      catch {
        toast.error('上传失败')
      }
      finally {
        uploadingField.value = ''
      }
    },
  })
}

/** 选择并上传文件（file 字段） */
function chooseAndUploadFile(field: FormSchemaField) {
  if (uploadingField.value || !field.name)
    return
  uni.chooseFile({
    count: 1,
    success: async (res) => {
      const tempFiles = res.tempFiles as any
      const filePath = Array.isArray(tempFiles) ? tempFiles[0]?.path : tempFiles?.path
      if (!filePath)
        return
      uploadingField.value = field.name!
      try {
        const result = await MarketAPI.uploadFile(filePath)
        const url = parseUploadUrl(result)
        if (url)
          formData[field.name!] = url
      }
      catch {
        toast.error('上传失败')
      }
      finally {
        uploadingField.value = ''
      }
    },
  })
}

function institutionName() {
  return institutions.value.find(i => i.id === institutionId.value)?.name ?? ''
}

async function loadInstitutions() {
  try {
    const res = await MarketAPI.getInstitutions({ page_no: 1, page_size: 100 })
    institutions.value = (res as any).items ?? []
  }
  catch {
    institutions.value = []
  }
}

/** 子表行数据：fieldName → 行对象数组 */
const tableRows = reactive<Record<string, Record<string, any>[]>>({})

function tableRowList(field: FormSchemaField): Record<string, any>[] {
  if (!field.name)
    return []
  if (!tableRows[field.name])
    tableRows[field.name] = [tableEmptyRow(field)]
  return tableRows[field.name]
}

function tableEmptyRow(field: FormSchemaField): Record<string, any> {
  const row: Record<string, any> = {}
  for (const col of field.columns ?? [])
    row[col.name ?? ''] = ''
  return row
}

function addTableRow(field: FormSchemaField) {
  if (!field.name)
    return
  tableRows[field.name].push(tableEmptyRow(field))
}

function removeTableRow(field: FormSchemaField, index: number) {
  if (!field.name)
    return
  if (tableRows[field.name].length <= 1)
    return
  tableRows[field.name].splice(index, 1)
}

/** 校验必填字段，返回是否通过 */
function validate(): boolean {
  if (!institutionId.value) {
    toast.warning(t('market.selectInstitution'))
    return false
  }
  for (const field of simpleFields.value) {
    if (field.name && isRequired(field) && (formData[field.name] === undefined || formData[field.name] === null || formData[field.name] === '')) {
      toast.warning(`${fieldLabel(field)} 为必填项`)
      return false
    }
  }
  return true
}

function buildPayload(status: 'DRAFT' | 'PENDING') {
  // 收集子表数据并入 form_data
  const payload: Record<string, any> = { ...formData }
  for (const field of tableFields.value) {
    if (field.name)
      payload[field.name] = tableRowList(field)
  }
  return {
    assignment_id: assignmentId.value,
    institution_id: institutionId.value,
    region: region.value || undefined,
    archive_no: archiveNo.value || undefined,
    form_data: payload,
    status,
  }
}

async function handleSubmit(status: 'DRAFT' | 'PENDING') {
  if (!validate())
    return
  submitting.value = true
  try {
    await MarketAPI.createSubmission(buildPayload(status))
    toast.success(status === 'DRAFT' ? t('market.draftSaved') : t('market.submitSuccess'))
    // 提交完成回跳「我的任务」，列表刷新后展示最新状态
    setTimeout(() => router.replace({ name: 'market-my-task' }), 300)
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    submitting.value = false
  }
}

/** 从「我的任务」现取分派实例以获取 form_schema（消除 URL 透传，规避超长与模板陈旧） */
async function loadAssignment() {
  formLoading.value = true
  try {
    const res = await MarketAPI.getMyAssignments({ page_no: 1, page_size: 100 })
    const items = (res as any).items as Array<{ id?: number; task_no?: string; task?: { task_type?: { template?: { form_schema?: FormSchemaField[] } | null } | null } | null }> ?? []
    const found = items.find(i => String(i.id) === String(assignmentId.value))
    if (found?.task?.task_type?.template?.form_schema) {
      formSchema.value = found.task.task_type.template.form_schema
      taskNo.value = found.task_no ?? ''
    }
    else {
      formSchema.value = []
    }
  }
  catch {
    formSchema.value = []
    toast.error(t('common.loadFailed'))
  }
  finally {
    formLoading.value = false
  }
  // 初始化动态字段默认值（简单字段 + 子表首行）
  for (const field of simpleFields.value) {
    if (field.name)
      formData[field.name] = field.type === 'number' ? undefined : ''
  }
  for (const field of tableFields.value) {
    if (field.name)
      tableRows[field.name] = [tableEmptyRow(field)]
  }
}

onLoad((query) => {
  assignmentId.value = Number(query?.assignment_id)
  taskNo.value = query?.task_no ?? ''
  loadAssignment()
  loadInstitutions()
})
</script>

<template>
  <view class="page-wraper">
    <view class="px-3 py-3">
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell :title="taskNo || '提交成果'" :value="t('market.submitResult')" />
      </wd-cell-group>

      <view class="mt-3 rounded-2 bg-white p-4">
        <wd-loading v-if="formLoading" class="my-4 block" />
        <wd-form v-if="!formLoading" :model="formData" label-position="left">
          <wd-form-item :label="t('market.institution')" required border>
            <view class="flex-1" @click="openInstitutionPicker">
              <wd-cell :value="institutionName() || t('market.selectInstitution')" is-link :border="false" />
            </view>
            <wd-picker :visible="showInstitutionPicker" :columns="institutionColumns" @confirm="onInstitutionConfirm" @cancel="showInstitutionPicker = false" />
          </wd-form-item>
          <wd-form-item :label="t('market.region')" border>
            <wd-input v-model="region" :placeholder="t('market.region')" />
          </wd-form-item>
          <wd-form-item :label="t('market.archiveNo')" border>
            <wd-input v-model="archiveNo" :placeholder="t('market.archiveNo')" />
          </wd-form-item>

          <!-- 动态采集字段：分节标题 / 简单字段 / 多行子表 -->
          <template v-for="field in formSchema" :key="field.name || field.label">
            <!-- 分节标题 -->
            <view v-if="isSection(field)" class="mt-3 mb-1 flex items-center gap-2">
              <view class="h-3 w-1 rounded-full bg-blue-500" />
              <text class="text-sm font-semibold text-gray-800">{{ field.label }}</text>
            </view>

            <!-- 多行子表 -->
            <view v-else-if="isTable(field)" class="mb-3 w-full">
              <view class="mb-1 text-sm font-medium text-gray-700">{{ field.label }}</view>
              <view v-for="(row, rowIndex) in tableRowList(field)" :key="rowIndex" class="mb-2 rounded-lg bg-gray-50 p-2">
                <view class="mb-1 flex items-center justify-between">
                  <text class="text-xs text-gray-500">{{ field.label }} #{{ rowIndex + 1 }}</text>
                  <text v-if="tableRowList(field).length > 1" class="text-xs text-red-500" @click="removeTableRow(field, rowIndex)">删除行</text>
                </view>
                <view v-for="col in field.columns ?? []" :key="col.name" class="mb-2 flex items-center gap-2">
                  <text class="w-20 shrink-0 text-xs text-gray-600">{{ col.label }}</text>
                  <input
                    v-model="row[col.name ?? '']"
                    class="flex-1 rounded bg-white px-2 py-1 text-sm"
                    :placeholder="col.label || ''"
                  />
                </view>
              </view>
              <view class="text-center">
                <text class="text-xs text-blue-500" @click="addTableRow(field)">+ 添加一行</text>
              </view>
            </view>

            <!-- 简单字段 -->
            <wd-form-item v-else :label="fieldLabel(field)" border :required="isRequired(field)">
              <view v-if="usePicker(field)" class="flex-1" @click="openFieldPicker(field)">
                <wd-cell :value="fieldValueText(field)" is-link :border="false" />
              </view>
              <wd-input
                v-else-if="field.type === 'textarea'"
                v-model="formData[field.name ?? '']"
                type="textarea"
                :placeholder="field.placeholder || fieldLabel(field)"
              />
              <view v-else-if="field.type === 'image'" class="flex-1" @click="chooseAndUploadImage(field)">
                <image
                  v-if="formData[field.name ?? '']"
                  :src="formData[field.name ?? '']"
                  mode="aspectFill"
                  class="h-40 w-40 rounded-2 object-cover"
                />
                <view v-else class="flex h-24 items-center justify-center rounded-2 bg-gray-50 text-sm text-gray-400">
                  {{ uploadingField === field.name ? '上传中…' : '点击上传图片' }}
                </view>
              </view>
              <view v-else-if="field.type === 'file'" class="flex-1" @click="chooseAndUploadFile(field)">
                <view class="flex h-12 items-center justify-between rounded-2 bg-gray-50 px-3 text-sm">
                  <text class="text-gray-600">{{ formData[field.name ?? ''] ? '已上传，点击重新上传' : '点击上传文件' }}</text>
                  <text class="text-gray-400">{{ uploadingField === field.name ? '上传中…' : '' }}</text>
                </view>
              </view>
              <wd-input
                v-else
                v-model="formData[field.name ?? '']"
                :type="field.type === 'number' ? 'number' : 'text'"
                :placeholder="field.placeholder || fieldLabel(field)"
              />
            </wd-form-item>
          </template>
        </wd-form>
        <wd-picker :visible="showFieldPicker" :columns="fieldPickerColumns" @confirm="onFieldPickerConfirm" @cancel="showFieldPicker = false" />
      </view>

      <view class="mt-4 flex gap-3">
        <wd-button block variant="plain" :loading="submitting" @click="handleSubmit('DRAFT')">
          {{ t('market.saveDraft') }}
        </wd-button>
        <wd-button block type="primary" :loading="submitting" @click="handleSubmit('PENDING')">
          {{ t('market.submit') }}
        </wd-button>
      </view>
      <wd-gap height="100rpx" safe-area-bottom />
    </view>
  </view>
</template>
