<template>
  <el-dialog
    :model-value="modelValue"
    width="760px"
    destroy-on-close
    append-to-body
    class="teacher-preview-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="dialog-head">
        <div>
          <strong>{{ teacherName || '教师' }} · 综合能力雷达评估</strong>
          <p>管理员侧预览当前教师画像的六维综合能力雷达，不跳转离开当前管理页面。</p>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="dialog-body">
      <el-empty v-if="!loading && !radarData.length" description="暂无可展示的雷达数据" :image-size="88" />
      <RadarChart v-else :radar-data="radarData" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import axios from 'axios'
import RadarChart from '../RadarChart.vue'

const props = defineProps<{
  modelValue: boolean
  teacherId?: number | null
  teacherName?: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const loading = ref(false)
const radarData = ref<Array<{ name: string; value: number }>>([])

const loadRadar = async () => {
  if (!props.teacherId) return
  loading.value = true
  try {
    const { data } = await axios.get(`/api/achievements/radar/${props.teacherId}/`)
    radarData.value = data?.radar_dimensions ?? []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.teacherId] as const,
  ([visible, teacherId]) => {
    if (!visible || !teacherId) return
    void loadRadar()
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

.dialog-body {
  min-height: 240px;
}
</style>
