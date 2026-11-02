<script setup lang="ts">
import type { UploadFileItem, UploadMethod } from '@wot-ui/ui/components/wd-upload/types'
import type { FeedbackItem } from '@/api/module_system/ticket'
import { onLoad, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { TicketAPI } from '@/api/module_system/ticket'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useListPage } from '@/composables/useListPage'

definePage({
  name: 'feedback',
  style: { navigationBarTitleText: '意见反馈', enablePullDownRefresh: true },
})
useI18nNavTitle('feedback.title')

const { t } = useI18n()
const toast = useToast()

/** 反馈类型：值域与后端 ticket_type 约定一致 */
const type = ref('suggestion')
const content = ref('')
const fileList = ref<UploadFileItem[]>([])
const submitting = ref(false)

const TYPE_OPTIONS = computed(() => [
  { value: 'suggestion', label: t('feedback.typeSuggestion') },
  { value: 'bug', label: t('feedback.typeBug') },
  { value: 'optimize', label: t('feedback.typeOptimize') },
  { value: 'other', label: t('feedback.typeOther') },
])

/** 从 wd-upload 的响应体里取文件地址：`{ code, data: { file_url } }` */
function parseFileUrl(response?: string | Record<string, any>): string {
  if (!response)
    return ''
  try {
    const raw = typeof response === 'string' ? response : JSON.stringify(response)
    const parsed = JSON.parse(raw) as { data?: { file_url?: string } }
    return parsed?.data?.file_url || ''
  }
  catch {
    return ''
  }
}

/** wd-upload 上传成功后的 `response` 即后端响应体，据此收集远程图片地址 */
const imageUrls = computed(() =>
  fileList.value
    .map(file => parseFileUrl(file.response))
    .filter((url): url is string => !!url),
)

/** 有文件仍在上传时禁止提交，避免漏传图片 */
const uploading = computed(() =>
  fileList.value.some(file => file.status === 'loading' || file.status === 'pending'),
)

/** 图片上传走统一 http 层（与个人资料头像同一套 upload 适配） */
const uploadImage: UploadMethod = async (file, formData, options) => {
  try {
    const res = await MarketAPI.uploadFile(file.url)
    const successStatus = options.statusCode ?? 200
    const isSuccess = Array.isArray(successStatus)
      ? successStatus.includes(res.statusCode)
      : res.statusCode === successStatus

    if (isSuccess)
      options.onSuccess(res, file, formData)
    else
      options.onError({ ...res, errMsg: res.errMsg || `HTTP ${res.statusCode}` }, file, formData)
  }
  catch (error) {
    options.onError({ errMsg: (error as Error)?.message || 'upload failed' } as UniApp.GeneralCallbackResult, file, formData)
  }
}

/** 我的反馈列表（后端返回 items/total，与 useListPage 兼容） */
const { list, total, loading, error, loadData, reload, refreshData, loadNext } = useListPage<FeedbackItem>({
  fetcher: params => TicketAPI.getMyFeedback(params),
  pageSize: 10,
})

function resetForm() {
  content.value = ''
  type.value = 'suggestion'
  fileList.value = []
}

async function handleSubmit() {
  if (submitting.value || uploading.value)
    return
  const text = content.value.trim()
  if (!text) {
    toast.warning(t('feedback.contentRequired'))
    return
  }
  if (text.length > 2000) {
    toast.warning(t('feedback.contentTooLong'))
    return
  }

  submitting.value = true
  try {
    await TicketAPI.createFeedback({
      content: text,
      ticket_type: type.value,
      images: imageUrls.value.length > 0 ? JSON.stringify(imageUrls.value) : undefined,
    })
    toast.success(t('feedback.submitSuccess'))
    resetForm()
    reload()
  }
  catch {
    // http 层已统一错误提示
  }
  finally {
    submitting.value = false
  }
}

function statusKey(status?: number) {
  switch (status) {
    case 1:
      return 'feedback.statusProcessing'
    case 2:
      return 'feedback.statusDone'
    case 3:
      return 'feedback.statusClosed'
    default:
      return 'feedback.statusPending'
  }
}

function statusClass(status?: number) {
  switch (status) {
    case 1:
      return 'fb-status--processing'
    case 2:
      return 'fb-status--done'
    case 3:
      return 'fb-status--closed'
    default:
      return 'fb-status--pending'
  }
}

function feedbackTitle(item: FeedbackItem) {
  return item.title || (item.ticket_content || '').split('\n')[0] || '-'
}

/** 标题已由后端取内容首行，内容与标题不同时才额外展示正文预览 */
function feedbackContent(item: FeedbackItem) {
  const text = item.ticket_content || ''
  return text && text !== feedbackTitle(item) ? text : ''
}

function submittedAt(time?: string) {
  return time ? t('feedback.submittedAt', { time: time.slice(0, 16) }) : ''
}

onLoad(() => {
  loadData()
})

onPullDownRefresh(() => {
  refreshData()
})

onReachBottom(() => {
  if (!loading.value && list.value.length < total.value)
    loadNext()
})
</script>

<template>
  <view class="page-wraper py-3">
    <!-- 提交表单 -->
    <view class="fb-card mx-3">
      <view class="fb-label">
        {{ t('feedback.typeLabel') }}
      </view>
      <view class="flex flex-wrap gap-2">
        <view
          v-for="opt in TYPE_OPTIONS"
          :key="opt.value"
          class="fb-type"
          :class="{ 'fb-type--active': type === opt.value }"
          hover-class="fb-type--pressed"
          @click="type = opt.value"
        >
          {{ opt.label }}
        </view>
      </view>

      <view class="fb-label mt-4">
        {{ t('feedback.contentLabel') }}
      </view>
      <wd-textarea
        v-model="content"
        :placeholder="t('feedback.contentPlaceholder')"
        :maxlength="2000"
        show-word-limit
        auto-height
      />

      <view class="fb-label mt-4">
        {{ t('feedback.imagesLabel') }}
      </view>
      <wd-upload
        v-model:file-list="fileList"
        :upload-method="uploadImage"
        :limit="3"
        accept="image"
        :max-size="5242880"
        :source-type="['album', 'camera']"
      />

      <view class="mt-4">
        <wd-button
          type="primary"
          size="large"
          round
          block
          :loading="submitting"
          :disabled="uploading"
          @click="handleSubmit"
        >
          {{ t('feedback.submit') }}
        </wd-button>
      </view>
    </view>

    <!-- 我的反馈 -->
    <view class="fb-section-title mx-3 mb-2 mt-4">
      {{ t('feedback.mine') }}
    </view>

    <SkeletonPage v-if="loading && list.length === 0" :rows="3" />

    <view v-else-if="error && list.length === 0" class="mx-3 mt-8 flex flex-col items-center gap-3">
      <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
      <wd-text :text="t('common.loadFailed')" class="wot-text-text-secondary text-3" />
      <wd-button size="small" round @click="reload">
        {{ t('common.retry') }}
      </wd-button>
    </view>

    <view v-else-if="list.length === 0" class="mx-3 mt-8">
      <wd-empty :tip="t('feedback.empty')" />
    </view>

    <view v-else class="mx-3 flex flex-col gap-3">
      <view v-for="item in list" :key="item.id" class="fb-item">
        <view class="fb-item__head">
          <view class="min-w-0 flex-1">
            <view class="fb-item__title">
              {{ feedbackTitle(item) }}
            </view>
            <view class="fb-item__time">
              {{ submittedAt(item.created_time) }}
            </view>
          </view>
          <text class="fb-status" :class="statusClass(item.status)">
            {{ t(statusKey(item.status)) }}
          </text>
        </view>

        <view v-if="feedbackContent(item)" class="fb-item__content">
          {{ feedbackContent(item) }}
        </view>

        <view v-if="item.reply" class="fb-reply">
          <view class="fb-reply__label">
            {{ t('feedback.reply') }}
          </view>
          <view class="fb-reply__text">
            {{ item.reply }}
          </view>
        </view>
      </view>

      <view v-if="loading" class="fb-more">
        <wd-loading />
      </view>
      <view v-else-if="list.length >= total" class="fb-more">
        <text>{{ t('common.noMore') }}</text>
      </view>
    </view>

    <wd-gap height="40rpx" />
  </view>
</template>

<style lang="scss" scoped>
.fb-card {
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);
}

.fb-label {
  margin-bottom: 16rpx;
  font-size: 26rpx;
  font-weight: 600;
  color: var(--wot-text-main);
}

.fb-section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--wot-text-main);
}

.fb-type {
  padding: 12rpx 28rpx;
  border-radius: 9999rpx;
  font-size: 26rpx;
  color: var(--wot-text-secondary);
  background: var(--wot-filled-content);
  border: 1rpx solid var(--wot-border-light);
  transition: opacity 0.15s ease;

  &--active {
    color: rgba(255, 255, 255, 1);
    font-weight: 600;
    background: var(--wot-primary-6);
    border-color: var(--wot-primary-6);
  }

  &--pressed {
    opacity: 0.72;
  }
}

/* 反馈条目：单一表面卡片，头部状态右侧对齐 */
.fb-item {
  padding: 24rpx 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16rpx;
  }

  &__title {
    font-size: 28rpx;
    font-weight: 600;
    line-height: 1.4;
    color: var(--wot-text-main);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__time {
    margin-top: 8rpx;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
    font-variant-numeric: tabular-nums;
  }

  &__content {
    margin-top: 12rpx;
    font-size: 26rpx;
    line-height: 1.6;
    color: var(--wot-text-secondary);
    word-break: break-all;
  }
}

.fb-status {
  flex-shrink: 0;
  padding: 4rpx 14rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;

  &--pending {
    color: var(--wot-warning-main);
    background: var(--wot-warning-surface);
  }

  &--processing {
    color: var(--wot-primary-6);
    background: var(--wot-filled-content);
  }

  &--done {
    color: var(--wot-success-main);
    background: var(--wot-success-surface);
  }

  &--closed {
    color: var(--wot-text-auxiliary);
    background: var(--wot-filled-content);
  }
}

.fb-reply {
  margin-top: 16rpx;
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  background: var(--wot-filled-content);

  &__label {
    font-size: 22rpx;
    font-weight: 600;
    color: var(--wot-primary-6);
  }

  &__text {
    margin-top: 8rpx;
    font-size: 26rpx;
    line-height: 1.6;
    color: var(--wot-text-secondary);
    word-break: break-all;
  }
}

.fb-more {
  display: flex;
  justify-content: center;
  padding: 16rpx 0;
  font-size: 22rpx;
  color: var(--wot-text-auxiliary);
}
</style>
