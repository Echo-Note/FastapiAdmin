<script setup lang="ts">
import type { FormSchemaField, InstitutionItem } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'

definePage({ name: 'market-submission-form', style: { navigationBarTitleText: '提交成果' } })

const { t } = useI18n()
const toast = useToast()

const assignmentId = ref<number>()
const taskNo = ref('')
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
  if (activeField.value)
    formData[activeField.value.name] = e.value[0]
  showFieldPicker.value = false
}

function fieldLabel(field: FormSchemaField) {
  return field.label || field.name
}

function fieldValueText(field: FormSchemaField) {
  const v = formData[field.name]
  if (v === undefined || v === null || v === '')
    return ''
  if (usePicker(field)) {
    const opt = field.options?.find(o => String(o.value) === String(v))
    return opt?.label ?? String(v)
  }
  return String(v)
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

/** 校验必填字段，返回是否通过 */
function validate(): boolean {
  if (!institutionId.value) {
    toast.warning(t('market.selectInstitution'))
    return false
  }
  for (const field of formSchema.value) {
    if (isRequired(field) && (formData[field.name] === undefined || formData[field.name] === null || formData[field.name] === '')) {
      toast.warning(`${fieldLabel(field)} 为必填项`)
      return false
    }
  }
  return true
}

function buildPayload(status: 'DRAFT' | 'PENDING') {
  return {
    assignment_id: assignmentId.value,
    institution_id: institutionId.value,
    region: region.value || undefined,
    archive_no: archiveNo.value || undefined,
    form_data: { ...formData },
    status,
  }
}

async function handleSubmit(status: 'DRAFT' | 'PENDING') {
  if (!validate())
    return
  submitting.value = true
  try {
    await MarketAPI.createSubmission(buildPayload(status))
    toast.success(t('common.saveSuccess'))
    setTimeout(() => uni.navigateBack(), 500)
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    submitting.value = false
  }
}

onLoad((query) => {
  assignmentId.value = Number(query?.assignment_id)
  taskNo.value = query?.task_no ?? ''
  try {
    const raw = query?.form_schema ? decodeURIComponent(query.form_schema as string) : '[]'
    const parsed = JSON.parse(raw) as FormSchemaField[]
    formSchema.value = Array.isArray(parsed) ? parsed : []
  }
  catch {
    formSchema.value = []
  }
  // 初始化动态字段默认值
  for (const field of formSchema.value) {
    formData[field.name] = field.type === 'number' ? undefined : ''
  }
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
        <wd-form :model="formData" label-position="left">
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

          <!-- 动态采集字段 -->
          <template v-for="field in formSchema" :key="field.name">
            <wd-form-item :label="fieldLabel(field)" border :required="isRequired(field)">
              <view v-if="usePicker(field)" class="flex-1" @click="openFieldPicker(field)">
                <wd-cell :value="fieldValueText(field)" is-link :border="false" />
              </view>
              <wd-input
                v-else-if="field.type === 'textarea'"
                v-model="formData[field.name]"
                type="textarea"
                :placeholder="field.placeholder || fieldLabel(field)"
              />
              <wd-input
                v-else
                v-model="formData[field.name]"
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
