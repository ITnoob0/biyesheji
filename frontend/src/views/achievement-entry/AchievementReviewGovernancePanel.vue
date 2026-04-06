<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type {
  AchievementRecordMap,
  AchievementReviewActionResponse,
  TabName,
} from '../../types/achievements'
import {
  approveAchievement,
  fetchPendingReviewAchievements,
  rejectAchievement,
} from './api'
import AchievementWorkflowTimelineDrawer from './AchievementWorkflowTimelineDrawer.vue'

type AnyAchievementRecord = AchievementRecordMap[TabName]

const props = defineProps<{
  tab: TabName
  canReview: boolean
}>()

const emit = defineEmits<{
  (event: 'updated', payload: AchievementReviewActionResponse): void
}>()

const loading = ref(false)
const pendingRecords = ref<AnyAchievementRecord[]>([])
const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejectingRecord = ref<AnyAchievementRecord | null>(null)
const timelineVisible = ref(false)
const timelineAchievementId = ref<number | null>(null)
const timelineAchievementTitle = ref('')

const tabLabels: Record<TabName, string> = {
  papers: '论文成果',
  projects: '科研项目',
  'intellectual-properties': '知识产权',
  'teaching-achievements': '教学成果',
  'academic-services': '学术服务',
}

const panelTitle = computed(() => `${tabLabels[props.tab]}审批`)

const detailLabel = computed(() => {
  if (props.tab === 'papers') return '期刊/会议'
  if (props.tab === 'projects') return '项目详情'
  if (props.tab === 'intellectual-properties') return '登记信息'
  if (props.tab === 'teaching-achievements') return '成果详情'
  return '服务机构'
})

const resolveDetail = (row: AnyAchievementRecord): string => {
  if (props.tab === 'papers') {
    return (row as AchievementRecordMap['papers']).journal_name || '—'
  }
  if (props.tab === 'projects') {
    const project = row as AchievementRecordMap['projects']
    return `${project.level_display} / ${project.role_display} / ${project.project_status || '—'}`
  }
  if (props.tab === 'intellectual-properties') {
    const ip = row as AchievementRecordMap['intellectual-properties']
    return `${ip.ip_type_display} / ${ip.registration_number}`
  }
  if (props.tab === 'teaching-achievements') {
    const teaching = row as AchievementRecordMap['teaching-achievements']
    return `${teaching.achievement_type_display} / ${teaching.level}`
  }
  const service = row as AchievementRecordMap['academic-services']
  return `${service.service_type_display} / ${service.organization}`
}

const loadPendingRecords = async () => {
  if (!props.canReview) {
    pendingRecords.value = []
    return
  }
  loading.value = true
  try {
    pendingRecords.value = await fetchPendingReviewAchievements(props.tab)
  } catch {
    ElMessage.error(`${tabLabels[props.tab]}待审核列表加载失败，请稍后重试。`)
  } finally {
    loading.value = false
  }
}

const approveRecord = async (record: AnyAchievementRecord) => {
  await ElMessageBox.confirm(`确认通过《${record.title}》吗？`, '审核通过确认', {
    type: 'warning',
  })

  const payload = await approveAchievement(props.tab, record.id)
  ElMessage.success('审核通过成功')
  emit('updated', payload)
  await loadPendingRecords()
}

const openRejectDialog = (record: AnyAchievementRecord) => {
  rejectingRecord.value = record
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

const submitReject = async () => {
  if (!rejectingRecord.value) return
  const reason = rejectReason.value.trim()
  if (!reason) {
    ElMessage.warning('请填写驳回原因。')
    return
  }

  const payload = await rejectAchievement(props.tab, rejectingRecord.value.id, reason)
  ElMessage.success('审核驳回成功')
  rejectDialogVisible.value = false
  emit('updated', payload)
  await loadPendingRecords()
}

const openTimeline = (record: AnyAchievementRecord) => {
  timelineAchievementId.value = record.id
  timelineAchievementTitle.value = record.title
  timelineVisible.value = true
}

watch(
  () => [props.tab, props.canReview] as const,
  () => {
    void loadPendingRecords()
  },
)

onMounted(() => {
  void loadPendingRecords()
})
</script>

<template>
  <el-card v-if="canReview" shadow="never" class="workspace-surface-card governance-card">
    <template #header>
      <div class="workspace-section-head governance-head">
        <span>{{ panelTitle }}</span>
        <el-tag type="warning" effect="plain">待审核 {{ pendingRecords.length }} 条</el-tag>
      </div>
    </template>

    <el-table :data="pendingRecords" v-loading="loading" empty-text="当前暂无待审核记录">
      <el-table-column prop="title" label="标题" min-width="240" />
      <el-table-column prop="teacher_name" label="教师" width="120" />
      <el-table-column :label="detailLabel" min-width="180">
        <template #default="{ row }">
          <span>{{ resolveDetail(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="date_acquired" label="时间" width="120" />
      <el-table-column prop="status_label" label="状态" width="100" />
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <div class="table-action-group workspace-table-actions table-action-group--compact">
            <el-button link type="success" @click="approveRecord(row)">通过</el-button>
            <el-button link type="danger" @click="openRejectDialog(row)">驳回</el-button>
            <el-button link type="info" @click="openTimeline(row)">时间轴</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="rejectDialogVisible" title="填写驳回理由" width="520px">
      <el-form label-position="top">
        <el-form-item label="驳回原因" required>
          <el-input
            v-model="rejectReason"
            type="textarea"
            :rows="4"
            placeholder="请明确填写驳回原因，便于教师修改后再次提交。"
          />
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
      :tab="tab"
      :achievement-id="timelineAchievementId"
      :achievement-title="timelineAchievementTitle"
    />
  </el-card>
</template>

<style scoped>
.governance-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 18px;
}

.governance-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>
