<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ensureSessionUserContext, type SessionUser } from '../../utils/sessionAuth'
import { approvePaper, fetchPaperGovernance, fetchPendingReviewPapers, rejectPaper } from './api'
import AchievementWorkflowTimelineDrawer from './AchievementWorkflowTimelineDrawer.vue'
import type { AchievementQueryState, PaperGovernanceResponse, PaperRecord } from '../../types/achievements'

const props = defineProps<{
  queryState?: Partial<AchievementQueryState['papers']>
  canManage?: boolean
  scopedTeacherId?: number | null
}>()

const emit = defineEmits<{
  (event: 'refresh'): void
  (event: 'edit-paper', paperId: number): void
}>()

const sessionUser = ref<SessionUser | null>(null)
const loading = ref(false)
const pendingLoading = ref(false)
const activeTab = ref<'overview' | 'pending'>('overview')
const governance = ref<PaperGovernanceResponse | null>(null)
const pendingPapers = ref<PaperRecord[]>([])
const rejectDialogVisible = ref(false)
const rejectingPaper = ref<PaperRecord | null>(null)
const rejectReason = ref('')
const timelineVisible = ref(false)
const timelinePaperId = ref<number | null>(null)
const timelinePaperTitle = ref('')

const isAdmin = computed(() => Boolean(sessionUser.value?.is_admin))
const isCollegeAdmin = computed(() => sessionUser.value?.role_code === 'college_admin')
const pendingTabTitle = computed(() => (isCollegeAdmin.value ? '本院待审核' : '待审核'))

const loadGovernance = async () => {
  loading.value = true
  try {
    governance.value = await fetchPaperGovernance(props.queryState)
  } catch {
    ElMessage.error('论文治理面板加载失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

const loadPendingPapers = async () => {
  if (!isAdmin.value) return
  pendingLoading.value = true
  try {
    pendingPapers.value = await fetchPendingReviewPapers()
  } catch {
    ElMessage.error('待审核列表加载失败，请稍后重试。')
  } finally {
    pendingLoading.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([loadGovernance(), loadPendingPapers()])
}

const handleApprove = async (paper: PaperRecord) => {
  await ElMessageBox.confirm(`确认通过《${paper.title}》的审核吗？`, '审核通过确认', {
    type: 'warning',
  })

  await approvePaper(paper.id)
  ElMessage.success('论文成果已审核通过')
  await refreshAll()
  emit('refresh')
}

const openRejectDialog = (paper: PaperRecord) => {
  rejectingPaper.value = paper
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

const submitReject = async () => {
  if (!rejectingPaper.value || !rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回原因。')
    return
  }

  await rejectPaper(rejectingPaper.value.id, rejectReason.value.trim())
  ElMessage.success('论文成果已驳回')
  rejectDialogVisible.value = false
  await refreshAll()
  emit('refresh')
}

const openTimeline = (paper: PaperRecord) => {
  timelinePaperId.value = paper.id
  timelinePaperTitle.value = paper.title
  timelineVisible.value = true
}

watch(
  () => props.queryState,
  () => {
    void loadGovernance()
  },
  { deep: true },
)

onMounted(async () => {
  sessionUser.value = await ensureSessionUserContext()
  await refreshAll()
})
</script>

<template>
  <el-card shadow="never" class="workspace-surface-card governance-card">
    <template #header>
      <div class="governance-header workspace-section-head">
        <span>论文治理与审批</span>
        <el-tag type="primary" effect="plain">{{ isCollegeAdmin ? '学院管理员视角' : '管理员视角' }}</el-tag>
      </div>
    </template>

    <el-tabs v-model="activeTab" class="governance-tabs">
      <el-tab-pane label="治理概览" name="overview">
        <div v-loading="loading" class="governance-stack">
          <div class="summary-grid">
            <div class="summary-item">
              <strong>{{ governance?.summary.total_count || 0 }}</strong>
              <span>论文总量</span>
            </div>
            <div class="summary-item">
              <strong>{{ governance?.summary.representative_count || 0 }}</strong>
              <span>代表作</span>
            </div>
            <div class="summary-item">
              <strong>{{ governance?.summary.incomplete_metadata_count || 0 }}</strong>
              <span>待补元数据</span>
            </div>
            <div class="summary-item">
              <strong>{{ pendingPapers.length }}</strong>
              <span>{{ pendingTabTitle }}</span>
            </div>
          </div>

          <div class="list-shell">
            <div class="section-inline-head">
              <h3>最近治理操作</h3>
              <el-button plain size="small" @click="$emit('refresh')">通知父页面刷新</el-button>
            </div>
            <div class="record-list">
              <div v-for="item in governance?.recent_operations || []" :key="item.id" class="record-item">
                <strong>{{ item.paper_title_snapshot || '论文成果' }}</strong>
                <p>{{ item.summary }}</p>
                <span>{{ item.created_at }}</span>
              </div>
              <el-empty v-if="!(governance?.recent_operations || []).length" description="暂无治理操作记录" />
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="isAdmin" :label="pendingTabTitle" name="pending">
        <div v-loading="pendingLoading" class="pending-shell">
          <el-table :data="pendingPapers" empty-text="当前暂无待审核论文">
            <el-table-column prop="title" label="题目" min-width="260" />
            <el-table-column prop="teacher_name" label="教师" width="120" />
            <el-table-column prop="journal_name" label="期刊/会议" min-width="180" />
            <el-table-column prop="date_acquired" label="时间" width="120" />
            <el-table-column prop="status_label" label="状态" width="100" />
            <el-table-column label="操作" min-width="220">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button link type="primary" @click="emit('edit-paper', row.id)">查看/编辑</el-button>
                  <el-button link type="success" @click="handleApprove(row)">通过</el-button>
                  <el-button link type="danger" @click="openRejectDialog(row)">驳回</el-button>
                  <el-button link type="info" @click="openTimeline(row)">时间轴</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="rejectDialogVisible" title="填写驳回理由" width="520px">
      <el-form label-position="top">
        <el-form-item label="驳回原因" required>
          <el-input v-model="rejectReason" type="textarea" :rows="4" placeholder="请明确填写驳回原因，便于教师修改后再次提交。" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="rejectDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="submitReject">确认驳回</el-button>
        </div>
      </template>
    </el-dialog>

    <AchievementWorkflowTimelineDrawer
      v-model="timelineVisible"
      tab="papers"
      :achievement-id="timelinePaperId"
      :achievement-title="timelinePaperTitle"
    />
  </el-card>
</template>

<style scoped>
.governance-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
}

.governance-stack,
.pending-shell {
  display: grid;
  gap: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-item,
.record-item {
  padding: 16px 18px;
  border: 1px solid var(--border-color-soft);
  border-radius: 18px;
  background: var(--panel-bg);
}

.summary-item {
  display: grid;
  gap: 6px;
}

.summary-item strong {
  font-size: 28px;
  color: var(--text-primary);
}

.summary-item span,
.record-item p,
.record-item span {
  color: var(--text-tertiary);
}

.record-list {
  display: grid;
  gap: 12px;
}

.record-item strong {
  display: block;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.record-item p {
  margin: 0 0 6px;
  line-height: 1.6;
}

.section-inline-head,
.table-actions,
.dialog-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-inline-head,
.dialog-actions {
  justify-content: space-between;
}

.table-actions {
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .section-inline-head,
  .dialog-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
