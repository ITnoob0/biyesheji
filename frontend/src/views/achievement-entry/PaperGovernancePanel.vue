<template>
  <div class="governance-grid">
    <el-card shadow="never" class="workspace-surface-card governance-card">
      <template #header>
        <div class="panel-head">
          <div>
            <strong>论文治理面板</strong>
            <p>围绕异常提示、代表作运营、导出、对比与历史回溯增强当前成果中心。</p>
          </div>
          <div class="panel-actions">
            <el-button plain @click="refreshGovernance" :loading="loading">刷新治理视图</el-button>
            <el-button type="primary" plain @click="handleExport" :loading="exporting">导出 CSV</el-button>
          </div>
        </div>
      </template>

      <div v-if="governance" class="governance-content">
        <div class="summary-strip">
          <el-tag type="success">代表作 {{ governance.representative_overview.count }} 篇</el-tag>
          <el-tag type="warning">缺 DOI {{ governance.summary.missing_doi_count }} 篇</el-tag>
          <el-tag type="danger">待清洗 {{ governance.summary.incomplete_metadata_count }} 篇</el-tag>
          <el-tag type="info">重复 DOI 组 {{ governance.summary.duplicate_doi_count }}</el-tag>
        </div>

        <div class="bulk-toolbar">
          <el-select v-model="selectedPaperIds" multiple collapse-tags placeholder="选择要批量运营的论文">
            <el-option v-for="paper in papers" :key="paper.id" :label="paper.title" :value="paper.id" />
          </el-select>
          <el-button type="success" plain :disabled="!selectedPaperIds.length" @click="updateRepresentative(true)">
            批量标记代表作
          </el-button>
          <el-button plain :disabled="!selectedPaperIds.length" @click="updateRepresentative(false)">
            批量取消代表作
          </el-button>
          <el-button type="warning" plain :disabled="!selectedPaperIds.length" @click="runCleanup">
            批量标准化清洗
          </el-button>
        </div>

        <div class="insight-grid">
          <section class="insight-card">
            <div class="section-head">
              <strong>异常与清洗建议</strong>
              <span>优先处理高频问题</span>
            </div>
            <div class="tag-list">
              <el-tag
                v-for="item in governance.summary.metadata_alert_breakdown || []"
                :key="item.code"
                :type="item.severity === 'warning' ? 'warning' : 'info'"
                effect="plain"
              >
                {{ item.label }} {{ item.count }}
              </el-tag>
            </div>
            <div class="suggestion-list">
              <div v-for="item in governance.cleanup_suggestions" :key="item.key" class="suggestion-item">
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>{{ item.description }}</p>
                </div>
                <div class="suggestion-actions">
                  <el-tag type="info" effect="plain">{{ item.count }} 条</el-tag>
                  <el-button
                    v-if="item.key === 'normalize_text_fields'"
                    link
                    type="primary"
                    @click="applySuggestion(item.example_ids)"
                  >
                    清洗示例
                  </el-button>
                </div>
              </div>
              <el-empty v-if="!governance.cleanup_suggestions.length" description="当前筛选范围内暂无明显清洗建议" />
            </div>
          </section>

          <section class="insight-card">
            <div class="section-head">
              <strong>代表作运营</strong>
              <span>优先关注高被引代表作</span>
            </div>
            <div class="suggestion-list">
              <div
                v-for="item in governance.representative_overview.top_items"
                :key="item.id"
                class="suggestion-item"
              >
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.journal_name }} / {{ item.date_acquired }}</p>
                </div>
                <div class="suggestion-actions">
                  <el-tag type="success" effect="plain">{{ item.citation_count }} 引用</el-tag>
                  <el-button link type="primary" @click="emit('editPaper', item.id)">继续修订</el-button>
                </div>
              </div>
              <el-empty v-if="!governance.representative_overview.top_items.length" description="当前还没有已标记的代表作" />
            </div>
          </section>
        </div>
      </div>

      <el-skeleton v-else :rows="6" animated />
    </el-card>

    <el-card shadow="never" class="workspace-surface-card governance-card">
      <template #header>
        <div class="panel-head">
          <div>
            <strong>结构化对比</strong>
            <p>对比两篇论文的元数据完整度、引用表现与协作结构。</p>
          </div>
        </div>
      </template>
      <div class="compare-toolbar">
        <el-select v-model="compareLeftId" placeholder="选择论文 A" clearable>
          <el-option v-for="item in candidateOptions" :key="`left-${item.id}`" :label="item.title" :value="item.id" />
        </el-select>
        <el-select v-model="compareRightId" placeholder="选择论文 B" clearable>
          <el-option v-for="item in candidateOptions" :key="`right-${item.id}`" :label="item.title" :value="item.id" />
        </el-select>
        <el-button type="primary" plain :disabled="!canCompare" :loading="compareLoading" @click="loadComparison">
          开始对比
        </el-button>
      </div>
      <div v-if="comparison" class="compare-result">
        <div class="summary-strip">
          <el-tag type="info">引用差值 {{ comparison.summary.citation_gap }}</el-tag>
          <el-tag type="warning">完整度差值 {{ comparison.summary.metadata_completeness_gap }}</el-tag>
          <el-tag type="success">共享关键词 {{ comparison.summary.shared_keywords.length }}</el-tag>
          <el-tag>共享作者 {{ comparison.summary.shared_coauthors.length }}</el-tag>
        </div>
        <el-table :data="comparison.comparison_rows" size="small">
          <el-table-column prop="label" label="比较项" width="120" />
          <el-table-column prop="left" :label="comparison.left.title" min-width="160" />
          <el-table-column prop="right" :label="comparison.right.title" min-width="160" />
        </el-table>
      </div>
      <el-empty v-else description="选择两篇论文后可查看结构化对比结果" />
    </el-card>

    <el-card shadow="never" class="workspace-surface-card governance-card">
      <template #header>
        <div class="panel-head">
          <div>
            <strong>操作历史</strong>
            <p>查看近期治理动作与单篇论文版本轨迹。</p>
          </div>
        </div>
      </template>
      <div class="history-toolbar">
        <el-select v-model="historyPaperId" clearable placeholder="选择论文查看历史">
          <el-option v-for="item in candidateOptions" :key="`history-${item.id}`" :label="item.title" :value="item.id" />
        </el-select>
        <el-button plain :disabled="!historyPaperId" :loading="historyLoading" @click="loadHistory">查看历史</el-button>
      </div>

      <div class="history-list">
        <div v-for="item in activeHistoryList" :key="`${item.id}-${item.created_at}`" class="history-item">
          <div>
            <strong>{{ item.action_label }} / {{ item.source_label }}</strong>
            <p>{{ item.summary }}</p>
          </div>
          <div class="history-meta">
            <span>{{ item.paper_title_snapshot || '论文已删除' }}</span>
            <span>{{ item.created_at }}</span>
          </div>
        </div>
        <el-empty v-if="!activeHistoryList.length" description="当前还没有可展示的治理历史" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import type {
  AchievementQueryState,
  PaperComparisonResponse,
  PaperGovernanceResponse,
  PaperOperationLogRecord,
  PaperRecord,
} from '../../types/achievements'
import {
  applyPaperCleanup,
  batchUpdatePaperRepresentative,
  exportPaperGovernance,
  fetchPaperComparison,
  fetchPaperGovernance,
  fetchPaperHistory,
} from './api'

const props = defineProps<{
  papers: PaperRecord[]
  queryState: AchievementQueryState['papers']
}>()

const emit = defineEmits<{
  refresh: []
  editPaper: [paperId: number]
}>()

const loading = ref(false)
const exporting = ref(false)
const compareLoading = ref(false)
const historyLoading = ref(false)
const governance = ref<PaperGovernanceResponse | null>(null)
const comparison = ref<PaperComparisonResponse | null>(null)
const selectedPaperIds = ref<number[]>([])
const compareLeftId = ref<number>()
const compareRightId = ref<number>()
const historyPaperId = ref<number>()
const paperHistory = ref<PaperOperationLogRecord[]>([])

const candidateOptions = computed(() => governance.value?.compare_candidates || props.papers)
const canCompare = computed(() => Boolean(compareLeftId.value && compareRightId.value && compareLeftId.value !== compareRightId.value))
const activeHistoryList = computed(() => (paperHistory.value.length ? paperHistory.value : governance.value?.recent_operations || []))

const refreshGovernance = async () => {
  loading.value = true
  try {
    governance.value = await fetchPaperGovernance(props.queryState)
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  exporting.value = true
  try {
    const blob = await exportPaperGovernance(props.queryState)
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `papers-governance-${Date.now()}.csv`
    anchor.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('论文治理导出已开始')
  } finally {
    exporting.value = false
  }
}

const updateRepresentative = async (nextValue: boolean) => {
  const result = await batchUpdatePaperRepresentative(selectedPaperIds.value, nextValue)
  ElMessage.success(`已更新 ${result.updated_count} 篇论文的代表作标记`)
  await refreshGovernance()
  emit('refresh')
}

const runCleanup = async () => {
  const result = await applyPaperCleanup(selectedPaperIds.value)
  ElMessage.success(`已标准化清洗 ${result.updated_count} 篇论文`)
  await refreshGovernance()
  emit('refresh')
}

const applySuggestion = async (paperIds: number[]) => {
  selectedPaperIds.value = paperIds
  if (paperIds.length) {
    await runCleanup()
  }
}

const loadComparison = async () => {
  if (!canCompare.value) return
  compareLoading.value = true
  try {
    comparison.value = await fetchPaperComparison(Number(compareLeftId.value), Number(compareRightId.value))
  } finally {
    compareLoading.value = false
  }
}

const loadHistory = async () => {
  if (!historyPaperId.value) return
  historyLoading.value = true
  try {
    const result = await fetchPaperHistory(Number(historyPaperId.value))
    paperHistory.value = result.history
  } finally {
    historyLoading.value = false
  }
}

watch(
  () => JSON.stringify(props.queryState),
  () => {
    void refreshGovernance()
  },
)

onMounted(() => {
  void refreshGovernance()
})
</script>

<style scoped>
.governance-grid {
  display: grid;
  gap: 20px;
  margin-top: 20px;
}

.governance-card {
  border: none;
  border-radius: 24px;
}

.panel-head,
.panel-actions,
.bulk-toolbar,
.compare-toolbar,
.history-toolbar,
.summary-strip,
.suggestion-actions,
.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.panel-head {
  justify-content: space-between;
}

.panel-head p,
.suggestion-item p,
.history-item p {
  margin: 4px 0 0;
  color: #64748b;
  line-height: 1.6;
}

.governance-content,
.suggestion-list,
.history-list {
  display: grid;
  gap: 16px;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.insight-card {
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f8fb 100%);
  display: grid;
  gap: 12px;
}

.section-head {
  display: grid;
  gap: 4px;
}

.section-head span {
  color: #64748b;
  font-size: 13px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-item,
.history-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid #e2e8f0;
}

.suggestion-item:last-child,
.history-item:last-child {
  border-bottom: none;
}

.history-meta {
  flex-direction: column;
  align-items: flex-end;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 960px) {
  .insight-grid {
    grid-template-columns: 1fr;
  }

  .suggestion-item,
  .history-item,
  .panel-head {
    flex-direction: column;
    align-items: stretch;
  }

  .history-meta {
    align-items: flex-start;
  }
}
</style>
