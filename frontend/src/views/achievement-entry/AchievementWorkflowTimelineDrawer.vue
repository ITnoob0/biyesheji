<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAchievementWorkflowHistory } from './api'
import type { AchievementOperationLogRecord, AchievementWorkflowHistoryResponse, TabName } from '../../types/achievements'

const props = defineProps<{
  modelValue: boolean
  tab: TabName
  achievementId: number | null
  achievementTitle?: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const loading = ref(false)
const timeline = ref<AchievementWorkflowHistoryResponse | null>(null)

const visible = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value),
})

const tagTypeMap: Record<string, '' | 'info' | 'success' | 'warning' | 'danger'> = {
  CREATE: 'info',
  UPDATE: 'warning',
  DELETE: 'danger',
  IMPORT: 'info',
  SUBMIT_REVIEW: 'warning',
  APPROVE: 'success',
  REJECT: 'danger',
}

const loadTimeline = async () => {
  if (!props.achievementId || !visible.value) return
  loading.value = true
  try {
    timeline.value = await fetchAchievementWorkflowHistory(props.tab, props.achievementId)
  } catch {
    ElMessage.error('审核与变更时间轴加载失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

const resolveTagType = (item: AchievementOperationLogRecord) => tagTypeMap[item.action] || 'info'

watch(
  () => [visible.value, props.achievementId] as const,
  () => {
    void loadTimeline()
  },
  { immediate: true },
)
</script>

<template>
  <el-drawer v-model="visible" size="540px" :title="`${achievementTitle || '成果'} · 审核与变更时间轴`">
    <div v-loading="loading" class="timeline-shell">
      <el-timeline v-if="timeline?.history?.length">
        <el-timeline-item
          v-for="item in timeline.history"
          :key="item.id"
          :timestamp="item.created_at"
          placement="top"
          :type="resolveTagType(item)"
        >
          <div class="timeline-card">
            <div class="timeline-head">
              <strong>{{ item.summary }}</strong>
              <el-tag size="small" :type="resolveTagType(item)" effect="plain">{{ item.action_label }}</el-tag>
            </div>
            <p class="timeline-meta">
              操作人：{{ item.operator_name || '系统' }} · 来源：{{ item.source_label }}
            </p>
            <p v-if="item.review_comment" class="timeline-comment">审核意见：{{ item.review_comment }}</p>
            <ul v-if="item.change_details?.length" class="timeline-changes">
              <li v-for="detail in item.change_details" :key="`${item.id}-${detail.field}-${detail.summary}`">
                {{ detail.summary }}
              </li>
            </ul>
          </div>
        </el-timeline-item>
      </el-timeline>

      <el-empty v-else description="当前成果暂无审核与变更记录" />
    </div>
  </el-drawer>
</template>

<style scoped>
.timeline-shell {
  min-height: 240px;
}

.timeline-card {
  padding: 14px 16px;
  border: 1px solid var(--border-color-soft);
  border-radius: 18px;
  background: var(--panel-bg);
}

.timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.timeline-head strong {
  color: var(--text-primary);
}

.timeline-meta,
.timeline-comment {
  margin: 0 0 8px;
  color: var(--text-tertiary);
  line-height: 1.6;
}

.timeline-changes {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  line-height: 1.7;
}
</style>
