<template>
  <el-dialog
    :model-value="modelValue"
    title="BibTeX 批量导入"
    width="980px"
    destroy-on-close
    @close="handleClose"
  >
    <div class="import-dialog">
      <el-alert type="info" show-icon :closable="false" class="import-alert">
        <template #title>
          一期最小方案当前支持 BibTeX 文件导入。PDF 元数据解析暂作预留，不纳入当前阶段验收。
        </template>
      </el-alert>

      <div class="upload-panel">
        <input ref="fileInputRef" class="hidden-input" type="file" accept=".bib,.bibtex,text/plain" @change="handleFileChange" />
        <div class="upload-actions">
          <el-button @click="fileInputRef?.click()">选择 BibTeX 文件</el-button>
          <span class="file-name">{{ selectedFile?.name || '尚未选择文件' }}</span>
        </div>
        <div class="upload-actions">
          <el-button type="primary" :disabled="!selectedFile" :loading="previewLoading" @click="previewImport">
            解析预览
          </el-button>
          <el-button :disabled="!selectedFile && !previewEntries.length" @click="resetPreview">清空</el-button>
        </div>
      </div>

      <div v-if="previewSummary" class="summary-row">
        <el-tag type="info">共 {{ previewSummary.total_count }} 条</el-tag>
        <el-tag type="success">可导入 {{ previewSummary.ready_count }} 条</el-tag>
        <el-tag type="warning">重复疑似 {{ previewSummary.duplicate_count }} 条</el-tag>
        <el-tag type="danger">字段异常 {{ previewSummary.invalid_count }} 条</el-tag>
      </div>

      <el-alert v-if="lastImportResult" type="success" show-icon :closable="false">
        <template #title>本次导入结果</template>
        <template #default>
          <div class="feedback-list">
            <p v-for="line in importFeedbackLines" :key="line">{{ line }}</p>
          </div>
        </template>
      </el-alert>

      <el-table v-if="previewEntries.length" :data="previewEntries" max-height="360">
        <el-table-column prop="source_index" label="#" width="56" />
        <el-table-column prop="title" label="论文题目" min-width="220" />
        <el-table-column prop="journal_name" label="期刊/会议" min-width="170" />
        <el-table-column prop="date_acquired" label="时间" width="120" />
        <el-table-column prop="doi" label="DOI" min-width="180" />
        <el-table-column label="合作者" min-width="160">
          <template #default="{ row }">
            {{ row.coauthors.length ? row.coauthors.join('，') : '无' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTypeFor(row.preview_status)">{{ statusLabelFor(row.preview_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提示" min-width="220">
          <template #default="{ row }">
            <span class="issue-text">{{ row.issues.length ? row.issues.join('；') : '校验通过，可直接导入。' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-else
        description="上传 BibTeX 文件后可先查看预览，再确认导入，不会直接写入已有论文数据。"
      />

      <div v-if="lastImportResult?.skipped_entries.length || lastImportResult?.failed_entries.length" class="result-grid">
        <el-card v-if="lastImportResult?.skipped_entries.length" shadow="never">
          <template #header>重复或跳过记录</template>
          <div v-for="item in lastImportResult.skipped_entries" :key="`${item.source_index}-${item.title}`" class="result-item">
            <strong>#{{ item.source_index || '-' }} {{ item.title || '未命名论文' }}</strong>
            <p>{{ item.issue_summary || '当前记录已跳过，请检查 DOI 或重复提示。' }}</p>
          </div>
        </el-card>

        <el-card v-if="lastImportResult?.failed_entries.length" shadow="never">
          <template #header>导入失败记录</template>
          <div v-for="item in lastImportResult.failed_entries" :key="`${item.source_index}-${item.title}`" class="result-item">
            <strong>#{{ item.source_index || '-' }} {{ item.title || '未命名论文' }}</strong>
            <p>{{ item.issue_summary || '字段校验未通过，请补全信息后重试。' }}</p>
          </div>
        </el-card>
      </div>
    </div>

    <template #footer>
      <div class="footer-actions">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :disabled="readyEntries.length === 0"
          :loading="confirmLoading"
          @click="confirmImport"
        >
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
  imported: []
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const previewEntries = ref<BibtexPreviewEntry[]>([])
const previewSummary = ref<BibtexPreviewSummary | null>(null)
const previewLoading = ref(false)
const confirmLoading = ref(false)
const lastImportResult = ref<BibtexImportResponse | null>(null)

const statusLabelMap: Record<BibtexPreviewEntry['preview_status'], string> = {
  ready: '可导入',
  duplicate: '重复',
  invalid: '异常',
}

const statusTypeMap: Record<BibtexPreviewEntry['preview_status'], 'success' | 'warning' | 'danger'> = {
  ready: 'success',
  duplicate: 'warning',
  invalid: 'danger',
}

const statusLabelFor = (status: BibtexPreviewStatus) => statusLabelMap[status]

const statusTypeFor = (status: BibtexPreviewStatus) => statusTypeMap[status]

const readyEntries = computed(() => previewEntries.value.filter(item => item.preview_status === 'ready'))
const importFeedbackLines = computed(() => (lastImportResult.value ? buildImportFeedbackLines(lastImportResult.value) : []))

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

const resetPreview = () => {
  previewEntries.value = []
  previewSummary.value = null
  selectedFile.value = null
  lastImportResult.value = null
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

const confirmImport = async () => {
  if (!readyEntries.value.length) {
    ElMessage.warning('当前没有可导入的论文记录')
    return
  }

  confirmLoading.value = true
  try {
    const payload = {
      entries: readyEntries.value.map(item => ({
        source_index: item.source_index,
        citation_key: item.citation_key,
        entry_type: item.entry_type,
        title: item.title,
        abstract: item.abstract,
        date_acquired: item.date_acquired,
        paper_type: item.paper_type,
        journal_name: item.journal_name,
        journal_level: item.journal_level,
        published_volume: item.published_volume,
        published_issue: item.published_issue,
        pages: item.pages,
        source_url: item.source_url,
        citation_count: item.citation_count,
        is_first_author: item.is_first_author,
        is_representative: item.is_representative,
        doi: item.doi,
        coauthors: item.coauthors,
        preview_status: item.preview_status,
        issues: item.issues,
      })),
    }

    const { data } = await axios.post<BibtexImportResponse>(paperImportEndpointMap.bibtexConfirm, payload)
    lastImportResult.value = data
    ElMessage.success(`导入完成：成功 ${data.imported_count} 条，跳过 ${data.skipped_count} 条，失败 ${data.failed_count} 条`)
    emit('imported')
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

.import-alert {
  border-radius: 16px;
}

.upload-panel {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: #f5f8f6;
}

.upload-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hidden-input {
  display: none;
}

.file-name,
.issue-text {
  color: #5b6c66;
  line-height: 1.6;
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feedback-list {
  display: grid;
  gap: 4px;
}

.feedback-list p,
.result-item p {
  margin: 0;
  line-height: 1.6;
}

.result-grid {
  display: grid;
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
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .upload-panel,
  .upload-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
