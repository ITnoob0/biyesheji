<template>
  <div class="governance-grid">
    <el-card shadow="never" class="workspace-surface-card governance-card">
      <template #header>
        <div class="panel-head">
          <div>
            <strong>操作历史</strong>
            <p>查看近期论文处理记录与单篇论文的历史轨迹。</p>
          </div>
          <el-button plain @click="refreshHistoryOverview" :loading="loading">刷新历史</el-button>
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
import { computed, onMounted, ref, watch } from 'vue'
import type {
  AchievementQueryState,
  PaperGovernanceResponse,
  PaperOperationLogRecord,
  PaperRecord,
} from '../../types/achievements'
import {
  fetchPaperGovernance,
  fetchPaperHistory,
} from './api'

const props = defineProps<{
  papers: PaperRecord[]
  queryState: AchievementQueryState['papers']
}>()

const loading = ref(false)
const historyLoading = ref(false)
const governance = ref<PaperGovernanceResponse | null>(null)
const historyPaperId = ref<number>()
const paperHistory = ref<PaperOperationLogRecord[]>([])

const candidateOptions = computed(() => governance.value?.compare_candidates || props.papers)
const activeHistoryList = computed(() => (paperHistory.value.length ? paperHistory.value : governance.value?.recent_operations || []))

const refreshHistoryOverview = async () => {
  loading.value = true
  try {
    governance.value = await fetchPaperGovernance(props.queryState)
  } finally {
    loading.value = false
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
    paperHistory.value = []
    void refreshHistoryOverview()
  },
)

onMounted(() => {
  void refreshHistoryOverview()
})
</script>

<style scoped>
.governance-grid {
  display: grid;
  gap: 0;
}

.governance-card {
  border: none;
  border-radius: 24px;
}

.panel-head,
.history-toolbar,
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
.history-item p {
  margin: 4px 0 0;
  color: var(--text-tertiary);
  line-height: 1.6;
}

.history-list {
  display: grid;
  gap: 16px;
}
.history-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--divider-color);
}

.history-item:last-child {
  border-bottom: none;
}

.history-meta {
  flex-direction: column;
  align-items: flex-end;
  color: var(--text-tertiary);
  font-size: 13px;
}

@media (max-width: 960px) {
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
