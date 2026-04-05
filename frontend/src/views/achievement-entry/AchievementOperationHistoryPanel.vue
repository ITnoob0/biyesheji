<template>
  <el-card shadow="never" class="workspace-surface-card history-card">
    <template #header>
      <div class="panel-head">
        <div>
          <strong>操作历史</strong>
          <p>默认展示当前账号在该成果类型下的最近操作记录，删除记录也会保留在历史中。</p>
        </div>
        <div class="history-toolbar">
          <el-select
            v-model="selectedRecordId"
            clearable
            placeholder="按当前成果筛选"
            class="history-select"
            @change="handleFilterChange"
          >
            <el-option v-for="item in records" :key="`history-${item.id}`" :label="item.title" :value="item.id" />
          </el-select>
          <el-button plain :loading="loading" @click="refreshHistory">刷新历史</el-button>
        </div>
      </div>
    </template>

    <div class="history-list">
      <div v-for="item in history" :key="`${item.id}-${item.created_at}`" class="history-item">
        <div class="history-main">
          <strong>{{ item.action_label }} / {{ item.source_label }}</strong>
          <p>{{ item.summary }}</p>
          <div class="history-meta-inline">
            <span>{{ item.title_snapshot || '已删除记录' }}</span>
            <span v-if="item.detail_snapshot">{{ item.detail_snapshot }}</span>
          </div>
        </div>
        <div class="history-side">
          <span>{{ item.created_at }}</span>
          <el-button link type="primary" @click="openDetail(item)">查看详情</el-button>
        </div>
      </div>
      <el-empty v-if="!history.length" description="当前还没有可展示的操作记录" />
    </div>
  </el-card>

  <el-dialog v-model="detailVisible" title="操作详情" width="640px">
    <template v-if="activeDetail">
      <div class="detail-grid">
        <div class="detail-row">
          <span>成果类型</span>
          <strong>{{ activeDetail.achievement_type_label }}</strong>
        </div>
        <div class="detail-row">
          <span>操作类型</span>
          <strong>{{ activeDetail.action_label }}</strong>
        </div>
        <div class="detail-row">
          <span>来源</span>
          <strong>{{ activeDetail.source_label }}</strong>
        </div>
        <div class="detail-row">
          <span>时间</span>
          <strong>{{ activeDetail.created_at }}</strong>
        </div>
        <div class="detail-row">
          <span>成果标题</span>
          <strong>{{ activeDetail.title_snapshot || '已删除记录' }}</strong>
        </div>
        <div class="detail-row" v-if="activeDetail.detail_snapshot">
          <span>补充信息</span>
          <strong>{{ activeDetail.detail_snapshot }}</strong>
        </div>
      </div>

      <div v-if="activeDetail.changed_fields.length" class="detail-section">
        <strong>变动字段</strong>
        <div class="detail-tag-list">
          <el-tag v-for="field in activeDetail.changed_fields" :key="field" size="small" effect="plain">{{ field }}</el-tag>
        </div>
      </div>

      <div v-if="detailSnapshotEntries.length" class="detail-section">
        <strong>当前记录快照</strong>
        <div class="snapshot-grid">
          <div v-for="entry in detailSnapshotEntries" :key="entry.key" class="snapshot-item">
            <span>{{ entry.key }}</span>
            <strong>{{ entry.value || '—' }}</strong>
          </div>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { AchievementOperationLogRecord, TabName } from '../../types/achievements'
import { fetchAchievementOperations } from './api'

interface HistoryOption {
  id: number
  title: string
}

const props = defineProps<{
  tab: TabName
  records: HistoryOption[]
  scopedTeacherId?: number | null
  refreshKey?: number
}>()

const loading = ref(false)
const history = ref<AchievementOperationLogRecord[]>([])
const selectedRecordId = ref<number>()
const detailVisible = ref(false)
const activeDetail = ref<AchievementOperationLogRecord | null>(null)

const detailSnapshotEntries = computed(() =>
  Object.entries(activeDetail.value?.snapshot_payload || {}).map(([key, value]) => ({
    key,
    value,
  })),
)

const loadHistory = async () => {
  loading.value = true
  try {
    const response = await fetchAchievementOperations(props.tab, {
      achievement_id: selectedRecordId.value,
      teacher_id: props.scopedTeacherId ?? undefined,
      _ts: Date.now(),
    })
    history.value = response.history
  } finally {
    loading.value = false
  }
}

const refreshHistory = async () => {
  await loadHistory()
}

const handleFilterChange = async () => {
  await loadHistory()
}

const openDetail = (item: AchievementOperationLogRecord) => {
  activeDetail.value = item
  detailVisible.value = true
}

watch(
  () => [props.tab, props.scopedTeacherId, props.refreshKey, props.records.map(item => item.id).join(',')],
  () => {
    if (selectedRecordId.value && !props.records.some(item => item.id === selectedRecordId.value)) {
      selectedRecordId.value = undefined
    }
    void loadHistory()
  },
)

onMounted(() => {
  void loadHistory()
})
</script>

<style scoped>
.history-card {
  border-radius: 24px;
}

.panel-head,
.history-toolbar,
.history-meta-inline,
.history-side {
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

.history-select {
  min-width: 240px;
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

.history-main {
  display: grid;
  gap: 8px;
}

.history-meta-inline {
  color: var(--text-tertiary);
  font-size: 13px;
}

.history-side {
  flex-direction: column;
  align-items: flex-end;
  color: var(--text-tertiary);
  font-size: 13px;
  white-space: nowrap;
}

.detail-grid {
  display: grid;
  gap: 12px;
}

.detail-row,
.snapshot-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--divider-color);
}

.detail-row span,
.snapshot-item span {
  color: var(--text-tertiary);
}

.detail-section {
  margin-top: 20px;
  display: grid;
  gap: 12px;
}

.detail-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.snapshot-grid {
  display: grid;
  gap: 8px;
}

@media (max-width: 960px) {
  .panel-head,
  .history-item,
  .history-side {
    flex-direction: column;
    align-items: stretch;
  }

  .history-select {
    min-width: 100%;
  }
}
</style>
