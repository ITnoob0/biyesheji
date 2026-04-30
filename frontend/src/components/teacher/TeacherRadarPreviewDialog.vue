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
          <strong>{{ teacherName || '教师' }} · 科研积分结构雷达</strong>
          <p>管理员侧可按年份查看画像，并叠加同侪基准线，不跳转离开当前管理页面。</p>
        </div>
        <div class="dialog-controls">
          <el-select
            v-model="selectedRuleVersionId"
            class="control-item rule-version-select"
            size="small"
            placeholder="规则版本"
            @change="loadPortraitAnalysis"
          >
            <el-option label="全部版本" value="all" />
            <el-option
              v-for="version in ruleVersionOptions"
              :key="version.id"
              :label="version.name"
              :value="version.id"
            />
          </el-select>
          <el-select
            v-model="selectedYear"
            class="control-item year-select"
            size="small"
            placeholder="年份"
            @change="loadPortraitAnalysis"
          >
            <el-option
              v-for="year in availableYears"
              :key="year"
              :label="`${year} 年`"
              :value="year"
            />
          </el-select>
          <el-radio-group
            v-if="isSystemAdmin"
            v-model="benchmarkScope"
            size="small"
            class="control-item"
            @change="loadPortraitAnalysis"
          >
            <el-radio-button label="college">本院平均</el-radio-button>
            <el-radio-button label="university">全校平均</el-radio-button>
          </el-radio-group>
          <el-tag size="small" effect="plain" class="control-item">
            {{ activeScope === 'university' ? '当前：全校平均' : '当前：本院平均' }}
          </el-tag>
          <el-tag v-if="ruleVersionScope?.active_version" size="small" effect="plain" class="control-item">
            启用：{{ ruleVersionScope.active_version.name }}
          </el-tag>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="dialog-body">
      <el-empty v-if="!loading && !radarData.length" description="暂无可展示的雷达数据" :image-size="88" />
      <template v-else>
        <RadarChart :radar-data="radarData" :series-data="radarSeriesData" :teacher-name="teacherName" />
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
              <div class="insight-score">雷达展示分 {{ insight.value }} 分 · 原始积分 {{ insight.raw_score ?? 0 }} 分</div>
              <div class="insight-rule-box">
                <div class="insight-rule-row">
                  <span class="insight-rule-label">纳入大类</span>
                  <span class="insight-rule-text">{{ insight.source_description }}</span>
                </div>
                <div class="insight-rule-row">
                  <span class="insight-rule-label">转换公式</span>
                  <span class="insight-rule-text">{{ insight.formula_note }}</span>
                </div>
              </div>
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
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import RadarChart from '../RadarChart.vue'
import { ensureSessionUserContext, type SessionUser } from '../../utils/sessionAuth'

interface DimensionInsight {
  key: string
  name: string
  value: number
  weight: number
  raw_score?: number
  score_role?: string
  level: string
  formula_note: string
  source_description: string
  evidence: string[]
}

interface RuleVersionOption {
  id: number
  name: string
  score_total?: number
}

interface RuleVersionScope {
  selected_rule_version_id?: number | null
  is_all_versions: boolean
  selected_version?: RuleVersionOption | null
  active_version?: RuleVersionOption | null
  available_versions: RuleVersionOption[]
}

interface PortraitAnalysisResponse {
  year: number
  available_years: number[]
  radar_dimensions: Array<{ name: string; value: number }>
  radar_series_data: Array<{ name: string; value: number[]; series_role?: string }>
  dimension_insights?: DimensionInsight[]
  benchmark_data?: {
    active_scope?: 'college' | 'university'
  }
  rule_version_scope?: RuleVersionScope
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
const radarSeriesData = ref<Array<{ name: string; value: number[]; series_role?: string }>>([])
const dimensionInsights = ref<DimensionInsight[]>([])
const selectedYear = ref(new Date().getFullYear())
const availableYears = ref<number[]>([new Date().getFullYear()])
const benchmarkScope = ref<'college' | 'university'>('college')
const activeScope = ref<'college' | 'university'>('college')
const currentUser = ref<SessionUser | null>(null)
const selectedRuleVersionId = ref<string | number>('all')
const ruleVersionScope = ref<RuleVersionScope | null>(null)
const isSystemAdmin = computed(() => currentUser.value?.role_code === 'admin')
const ruleVersionOptions = computed(() => ruleVersionScope.value?.available_versions ?? [])

const getLevelType = (level: string) => {
  if (level === '优势维度') return 'success'
  if (level === '稳定维度') return 'primary'
  return 'warning'
}

const ensureCurrentUser = async () => {
  if (!currentUser.value) {
    currentUser.value = await ensureSessionUserContext()
  }
}

const loadPortraitAnalysis = async () => {
  if (!props.teacherId) return
  await ensureCurrentUser()
  loading.value = true
  try {
    const { data } = await axios.get<PortraitAnalysisResponse>('/api/achievements/portrait/analysis/', {
      params: {
        user_id: props.teacherId,
        year: selectedYear.value,
        scope: isSystemAdmin.value ? benchmarkScope.value : 'college',
        ...(selectedRuleVersionId.value === 'all' ? {} : { rule_version: selectedRuleVersionId.value }),
      },
    })
    radarData.value = data?.radar_dimensions ?? []
    radarSeriesData.value = data?.radar_series_data ?? []
    dimensionInsights.value = data?.dimension_insights ?? []
    selectedYear.value = Number(data?.year || selectedYear.value)
    availableYears.value = (data?.available_years || [])
      .map(item => Number(item))
      .filter(item => Number.isFinite(item))
    if (!availableYears.value.length) {
      availableYears.value = [selectedYear.value]
    }
    if (data?.rule_version_scope) {
      ruleVersionScope.value = data.rule_version_scope
      selectedRuleVersionId.value = data.rule_version_scope.is_all_versions
        ? 'all'
        : data.rule_version_scope.selected_rule_version_id || 'all'
    }
    activeScope.value = data?.benchmark_data?.active_scope === 'university' ? 'university' : 'college'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.teacherId] as const,
  async ([visible, teacherId]) => {
    if (!visible || !teacherId) return
    selectedYear.value = new Date().getFullYear()
    benchmarkScope.value = 'college'
    selectedRuleVersionId.value = 'all'
    await loadPortraitAnalysis()
  },
  { immediate: true },
)

watch(
  () => props.teacherId,
  async teacherId => {
    if (!props.modelValue || !teacherId) return
    await loadPortraitAnalysis()
  },
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

.dialog-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.control-item {
  flex-shrink: 0;
}

.year-select {
  width: 120px;
}

.rule-version-select {
  width: 180px;
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

.insight-rule-box {
  display: grid;
  gap: 6px;
  margin-bottom: 10px;
  padding: 8px 10px;
  border: 1px solid rgba(64, 158, 255, 0.18);
  border-radius: 8px;
  background: rgba(64, 158, 255, 0.05);
}

.insight-rule-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.insight-rule-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(64, 158, 255, 0.12);
  color: #409eff;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
}

.insight-rule-text {
  min-width: 0;
  color: var(--text-secondary, #606266);
  font-size: 12px;
  line-height: 1.55;
  word-break: break-word;
}

.insight-tags {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.insight-tags .el-tag {
  width: 100%;
  height: auto;
  min-height: 26px;
  justify-content: center;
  padding: 4px 8px;
  line-height: 1.35;
  white-space: normal;
  text-align: center;
  background: rgba(64, 158, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.2);
  color: #409eff;
}

@media (max-width: 900px) {
  .dialog-head {
    flex-direction: column;
    align-items: stretch;
  }

  .dialog-controls {
    justify-content: flex-start;
  }

  .insights-grid,
  .insight-tags {
    grid-template-columns: 1fr;
  }

  .insight-rule-row {
    grid-template-columns: 1fr;
  }

  .insight-rule-label {
    width: fit-content;
  }
}
</style>
