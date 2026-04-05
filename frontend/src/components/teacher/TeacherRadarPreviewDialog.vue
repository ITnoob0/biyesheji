<template>
  <el-dialog
    :model-value="modelValue"
    width="800px"
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
      <template v-else>
        <RadarChart :radar-data="radarData" :teacher-name="teacherName" />
        <div v-if="dimensionInsights.length" class="dimension-insights">
          <div class="insights-grid">
            <div
              v-for="insight in dimensionInsights"
              :key="insight.key"
              class="insight-item"
            >
              <div class="insight-header">
                <span class="insight-name">{{ insight.name }}</span>
                <el-tag size="small" :type="getLevelType(insight.level)" effect="plain">{{ insight.level }}</el-tag>
              </div>
              <div class="insight-score">评分 {{ insight.value }} 分 · 权重 {{ insight.weight }}%</div>
              <div class="insight-desc">{{ insight.source_description }}</div>
              <div class="insight-tags">
                <el-tag v-for="(tag, idx) in insight.evidence" :key="idx" size="small" type="info" effect="plain">
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import axios from 'axios'
import RadarChart from '../RadarChart.vue'

interface DimensionInsight {
  key: string
  name: string
  value: number
  weight: number
  level: string
  formula_note: string
  source_description: string
  evidence: string[]
}

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
const dimensionInsights = ref<DimensionInsight[]>([])

const getLevelType = (level: string) => {
  if (level === '优势维度') return 'success'
  if (level === '稳定维度') return 'primary'
  return 'warning'
}

const loadRadar = async () => {
  if (!props.teacherId) return
  loading.value = true
  try {
    const { data } = await axios.get(`/api/achievements/radar/${props.teacherId}/`)
    radarData.value = data?.radar_dimensions ?? []
    dimensionInsights.value = data?.dimension_insights ?? []
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

.dimension-insights {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.insight-item {
  padding: 14px;
  border-radius: 8px;
  background: var(--el-fill-color-lighter, #fafafa);
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.insight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.insight-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-color-primary, #409eff);
}

.insight-score {
  font-size: 13px;
  color: var(--text-secondary, #606266);
  margin-bottom: 8px;
}

.insight-desc {
  font-size: 12px;
  color: var(--text-tertiary, #909399);
  line-height: 1.6;
  margin-bottom: 10px;
}

.insight-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.insight-tags .el-tag {
  background: rgba(64, 158, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.2);
  color: #409eff;
}
</style>
