<template>
  <el-dialog
    :model-value="modelValue"
    width="980px"
    destroy-on-close
    append-to-body
    class="teacher-preview-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="dialog-head">
        <div>
          <strong>{{ response?.teacher_name || teacherName || '教师' }} · 全部成果</strong>
          <p>代表成果优先展示，其余成果按时间从近到远排序；统计口径与教师画像中的已生效成果保持一致。</p>
        </div>
        <div class="dialog-tag-group">
          <el-tag type="success" effect="plain">{{ response?.achievement_total || 0 }} 条</el-tag>
          <el-tag type="primary" effect="plain">{{ response?.achievement_score_total || 0 }} 分</el-tag>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="dialog-body">
      <TeacherAchievementListPanel v-if="!loading" :records="records" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import type { AllAchievementRecord, AllAchievementResponse } from '../../views/dashboard/portrait'
import TeacherAchievementListPanel from './TeacherAchievementListPanel.vue'

const props = defineProps<{
  modelValue: boolean
  teacherId?: number | null
  teacherName?: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const loading = ref(false)
const response = ref<AllAchievementResponse | null>(null)
const records = computed<AllAchievementRecord[]>(() => response.value?.records ?? [])

const loadAchievements = async () => {
  if (!props.teacherId) return
  loading.value = true
  try {
    const { data } = await axios.get<AllAchievementResponse>(`/api/achievements/all-achievements/${props.teacherId}/`)
    response.value = data
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.teacherId] as const,
  ([visible, teacherId]) => {
    if (!visible || !teacherId) return
    void loadAchievements()
  },
  { immediate: true },
)
</script>

<style scoped>
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dialog-head strong {
  color: var(--text-primary);
}

.dialog-head p {
  margin: 6px 0 0;
  color: var(--text-tertiary);
}

.dialog-tag-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.dialog-body {
  min-height: 240px;
}
</style>
