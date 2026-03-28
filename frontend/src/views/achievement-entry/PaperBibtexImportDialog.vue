<template>
  <el-dialog
    :model-value="modelValue"
    title="BibTeX 批量导入"
    width="1100px"
    destroy-on-close
    @close="handleClose"
  >
    <div class="import-dialog">
      <el-alert type="info" show-icon :closable="false" class="import-alert">
        <template #title>
          当前保留原有 BibTeX 预览确认链路，并新增预览后修订、重新校验和更清晰的失败分类。
        </template>
      </el-alert>

      <div class="upload-panel">
        <input ref="fileInputRef" class="hidden-input" type="file" accept=".bib,.bibtex,text/plain" @change="handleFileChange" />
        <div class="upload-actions">
          <el-button @click="fileInputRef?.click()">选择 BibTeX 文件</el-button>
          <span class="file-name">{{ selectedFile?.name || '尚未选择文件' }}</span>
        </div>
        <div class="upload-actions">
          <el-button type="primary" :disabled="!selectedFile" :loading="previewLoading" @click="previewImport">解析预览</el-button>
          <el-button :disabled="!previewEntries.length" :loading="revalidateLoading" @click="revalidateCurrentEntries">重新校验</el-button>
          <el-button :disabled="!selectedFile && !previewEntries.length" @click="resetPreview">清空</el-button>
        </div>
      </div>

      <div v-if="previewSummary" class="summary-row">
        <el-tag type="info">总计 {{ previewSummary.total_count }} 条</el-tag>
        <el-tag type="success">可导入 {{ previewSummary.ready_count }} 条</el-tag>
        <el-tag type="warning">疑似重复 {{ previewSummary.duplicate_count }} 条</el-tag>
        <el-tag type="danger">需修订 {{ previewSummary.invalid_count }} 条</el-tag>
      </div>

      <el-alert v-if="lastImportResult" type="success" show-icon :closable="false">
        <template #title>本次导入结果</template>
        <template #default>
          <div class="feedback-list">
            <p v-for="line in importFeedbackLines" :key="line">{{ line }}</p>
          </div>
        </template>
      </el-alert>

      <el-table v-if="previewEntries.length" :data="previewEntries" max-height="340">
        <el-table-column prop="source_index" label="#" width="56" />
        <el-table-column prop="title" label="论文题目" min-width="200" />
        <el-table-column prop="journal_name" label="期刊/会议" min-width="160" />
        <el-table-column prop="date_acquired" label="时间" width="120" />
        <el-table-column prop="doi" label="DOI" min-width="160" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTypeFor(row.preview_status)">{{ statusLabelFor(row.preview_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="问题分类" min-width="180">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag v-for="item in row.issue_categories" :key="`${row.source_index}-${item}`" size="small" effect="plain">
                {{ item }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="修订" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="startEditing(row)">修订条目</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else description="上传 BibTeX 文件后可先查看预览，再确认导入，不会直接写入已有论文数据。" />

      <el-card v-if="editingEntry" shadow="never" class="editor-card">
        <template #header>
          <div class="panel-head">
            <strong>预览后修订</strong>
            <el-tag type="warning" effect="plain">#{{ editingEntry.source_index }}</el-tag>
          </div>
        </template>
        <div class="editor-grid">
          <el-input v-model="editingEntry.title" placeholder="论文题目" />
          <el-input v-model="editingEntry.journal_name" placeholder="期刊/会议名称" />
          <el-date-picker v-model="editingEntry.date_acquired" type="date" value-format="YYYY-MM-DD" placeholder="发表时间" />
          <el-select v-model="editingEntry.paper_type">
            <el-option label="期刊论文" value="JOURNAL" />
            <el-option label="会议论文" value="CONFERENCE" />
          </el-select>
          <el-input v-model="editingEntry.doi" placeholder="DOI" />
          <el-input v-model="editingEntry.source_url" placeholder="来源链接" />
          <el-input v-model="editingEntry.pages" placeholder="页码范围" />
          <el-input v-model="editingEntry.journal_level" placeholder="期刊级别" />
        </div>
        <el-input v-model="editingEntry.abstract" type="textarea" :rows="3" placeholder="摘要" />
        <div class="editor-actions">
          <el-button @click="editingEntry = null">取消修订</el-button>
          <el-button type="primary" :loading="revalidateLoading" @click="saveAndRevalidate">保存并重新校验</el-button>
        </div>
      </el-card>

      <div v-if="lastImportResult?.skipped_entries.length || lastImportResult?.failed_entries.length" class="result-grid">
        <el-card v-if="lastImportResult?.skipped_entries.length" shadow="never">
          <template #header>重复或跳过记录</template>
          <div v-for="item in lastImportResult.skipped_entries" :key="`${item.source_index}-${item.title}`" class="result-item">
            <strong>#{{ item.source_index || '-' }} {{ item.title || '未命名论文' }}</strong>
            <p>{{ item.reason_label || '跳过' }} / {{ item.issue_summary || '请检查 DOI 或预览阶段的重复提示。' }}</p>
          </div>
        </el-card>

        <el-card v-if="lastImportResult?.failed_entries.length" shadow="never">
          <template #header>导入失败记录</template>
          <div v-for="item in lastImportResult.failed_entries" :key="`${item.source_index}-${item.title}`" class="result-item">
            <strong>#{{ item.source_index || '-' }} {{ item.title || '未命名论文' }}</strong>
            <p>{{ item.reason_label || '失败' }} / {{ item.issue_summary || '字段校验未通过，请补全信息后重试。' }}</p>
          </div>
        </el-card>
      </div>
    </div>

    <template #footer>
      <div class="footer-actions">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :disabled="readyEntries.length === 0" :loading="confirmLoading" @click="confirmImport">
          确认导入 {{ readyEntries.length }} 条
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { paperImportEndpointMap } from './constants'
import { revalidateBibtexEntries } from './api'
import { buildImportFeedbackLines } from './paperLifecycle.js'
import type {
  BibtexImportResponse,
  BibtexPreviewEntry,
  BibtexPreviewResponse,
  BibtexPreviewStatus,
  BibtexPreviewSummary,
} from './types'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  imported: [payload: BibtexImportResponse]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const previewEntries = ref<BibtexPreviewEntry[]>([])
const previewSummary = ref<BibtexPreviewSummary | null>(null)
const previewLoading = ref(false)
const revalidateLoading = ref(false)
const confirmLoading = ref(false)
const lastImportResult = ref<BibtexImportResponse | null>(null)
const editingEntry = ref<BibtexPreviewEntry | null>(null)

const statusLabelMap: Record<BibtexPreviewStatus, string> = {
  ready: '可导入',
  duplicate: '重复',
  invalid: '需修订',
}

const statusTypeMap: Record<BibtexPreviewStatus, 'success' | 'warning' | 'danger'> = {
  ready: 'success',
  duplicate: 'warning',
  invalid: 'danger',
}

const readyEntries = computed(() => previewEntries.value.filter(item => item.preview_status === 'ready'))
const importFeedbackLines = computed(() => (lastImportResult.value ? buildImportFeedbackLines(lastImportResult.value) : []))

const statusLabelFor = (status: BibtexPreviewStatus) => statusLabelMap[status]
const statusTypeFor = (status: BibtexPreviewStatus) => statusTypeMap[status]

const cloneEntry = (entry: BibtexPreviewEntry): BibtexPreviewEntry => ({
  ...entry,
  issues: [...(entry.issues || [])],
  issue_details: [...(entry.issue_details || [])],
  issue_categories: [...(entry.issue_categories || [])],
  coauthors: [...(entry.coauthors || [])],
})

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

const resetPreview = () => {
  previewEntries.value = []
  previewSummary.value = null
  selectedFile.value = null
  lastImportResult.value = null
  editingEntry.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const previewImport = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 BibTeX 文件')
    return
  }

  previewLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const { data } = await axios.post<BibtexPreviewResponse>(paperImportEndpointMap.bibtexPreview, formData)
    previewEntries.value = data.entries
    previewSummary.value = data.summary
    ElMessage.success(`已解析 ${data.summary.total_count} 条 BibTeX 记录`)
  } catch (error: any) {
    const detail = error?.response?.data?.detail || 'BibTeX 预览解析失败，请检查文件内容。'
    ElMessage.error(detail)
  } finally {
    previewLoading.value = false
  }
}

const revalidateCurrentEntries = async () => {
  if (!previewEntries.value.length) return
  revalidateLoading.value = true
  try {
    const data = await revalidateBibtexEntries(previewEntries.value)
    previewEntries.value = data.entries
    previewSummary.value = data.summary
    ElMessage.success('已完成重新校验')
  } finally {
    revalidateLoading.value = false
  }
}

const startEditing = (row: BibtexPreviewEntry) => {
  editingEntry.value = cloneEntry(row)
}

const saveAndRevalidate = async () => {
  if (!editingEntry.value) return
  const nextEntries = previewEntries.value.map(item =>
    item.source_index === editingEntry.value?.source_index ? cloneEntry(editingEntry.value) : item,
  )
  previewEntries.value = nextEntries
  editingEntry.value = null
  await revalidateCurrentEntries()
}

const confirmImport = async () => {
  if (!readyEntries.value.length) {
    ElMessage.warning('当前没有可导入的论文记录')
    return
  }

  confirmLoading.value = true
  try {
    const payload = {
      entries: readyEntries.value.map(item => ({
        ...item,
      })),
    }
    const { data } = await axios.post<BibtexImportResponse>(paperImportEndpointMap.bibtexConfirm, payload)
    lastImportResult.value = data
    ElMessage.success(`导入完成：成功 ${data.imported_count} 条，跳过 ${data.skipped_count} 条，失败 ${data.failed_count} 条`)
    emit('imported', data)
    if (!data.skipped_count && !data.failed_count) {
      handleClose()
    }
  } catch (error: any) {
    const detail = error?.response?.data?.detail || 'BibTeX 导入失败，请稍后重试。'
    ElMessage.error(detail)
  } finally {
    confirmLoading.value = false
  }
}

const handleClose = () => {
  resetPreview()
  emit('update:modelValue', false)
}
</script>

<style scoped>
.import-dialog {
  display: grid;
  gap: 16px;
}

.import-alert,
.editor-card {
  border-radius: 18px;
}

.upload-panel,
.upload-actions,
.summary-row,
.footer-actions,
.editor-actions,
.tag-list,
.panel-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.upload-panel {
  justify-content: space-between;
  padding: 16px 18px;
  border-radius: 18px;
  background: #f5f8f6;
}

.hidden-input {
  display: none;
}

.file-name {
  color: #5b6c66;
}

.feedback-list,
.result-grid {
  display: grid;
  gap: 4px;
}

.editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.result-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.result-item {
  display: grid;
  gap: 6px;
  padding: 12px 0;
  border-bottom: 1px solid #e5efe8;
}

.result-item:last-child {
  border-bottom: none;
}

.footer-actions {
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .editor-grid,
  .result-grid {
    grid-template-columns: 1fr;
  }

  .upload-panel,
  .upload-actions,
  .panel-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
