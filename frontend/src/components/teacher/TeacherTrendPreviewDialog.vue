<template>
  <el-dialog
    :model-value="modelValue"
    width="1080px"
    destroy-on-close
    append-to-body
    class="teacher-preview-dialog teacher-trend-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="dialog-head">
        <div>
          <strong>{{ teacherName || '教师' }} · 趋势分析</strong>
          <p>按当前规则化科研成果口径展示画像维度变化与近年成果结构，不跳转离开管理员看板。</p>
        </div>
        <div class="dialog-controls">
          <el-select
            v-model="selectedRuleVersionId"
            class="rule-version-select"
            size="small"
            placeholder="规则版本"
            @change="loadTrendData"
          >
            <el-option label="全部版本" value="all" />
            <el-option
              v-for="version in ruleVersionOptions"
              :key="version.id"
              :label="version.name"
              :value="version.id"
            />
          </el-select>
          <el-tag size="small" type="primary" effect="plain">{{ achievementOverview.total_score ?? 0 }} 分</el-tag>
          <el-tag size="small" effect="plain">{{ achievementOverview.total_achievements ?? 0 }} 项成果</el-tag>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="dialog-body">
      <el-empty
        v-if="!loading && !dimensionTrend.length && !recentStructure.length"
        description="暂无可展示的趋势数据"
        :image-size="88"
      />
      <template v-else>
        <div class="trend-summary-grid">
          <div class="summary-item">
            <span>学术产出</span>
            <strong>{{ achievementOverview.paper_score ?? 0 }} 分</strong>
            <p>{{ achievementOverview.paper_count ?? 0 }} 项</p>
          </div>
          <div class="summary-item">
            <span>科研项目</span>
            <strong>{{ achievementOverview.project_score ?? 0 }} 分</strong>
            <p>{{ achievementOverview.project_count ?? 0 }} 项</p>
          </div>
          <div class="summary-item">
            <span>奖励转化</span>
            <strong>{{ achievementOverview.intellectual_property_score ?? 0 }} 分</strong>
            <p>{{ achievementOverview.intellectual_property_count ?? 0 }} 项</p>
          </div>
          <div class="summary-item">
            <span>平台科普</span>
            <strong>{{ achievementOverview.academic_service_score ?? 0 }} 分</strong>
            <p>{{ achievementOverview.academic_service_count ?? 0 }} 项</p>
          </div>
        </div>

        <div class="chart-grid">
          <section class="chart-panel">
            <div class="chart-panel__head">
              <strong>画像维度变化趋势</strong>
              <span>按五个画像维度展示近年变化。</span>
            </div>
            <div ref="dimensionTrendChartRef" class="trend-chart"></div>
          </section>

          <section class="chart-panel">
            <div class="chart-panel__head">
              <strong>近年成果结构</strong>
              <span>当前科研成果口径：学术产出、科研项目、奖励转化、平台科普。</span>
            </div>
            <div ref="structureChartRef" class="trend-chart"></div>
          </section>
        </div>
      </template>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import axios from 'axios'
import * as echarts from 'echarts'
import { computed, markRaw, nextTick, onUnmounted, ref, watch } from 'vue'
import { observeElementsResize } from '../../utils/resizeObserver'
import { WORKSPACE_THEME_CHANGED_EVENT } from '../../utils/workspaceTheme'
import {
  buildAchievementStructureOption,
  buildDimensionTrendOption,
  type AchievementOverview,
  type DashboardStatsResponse,
  type DimensionTrendPoint,
  type RecentStructurePoint,
  type RuleVersionScope,
} from '../../views/dashboard/portrait'

const props = defineProps<{
  modelValue: boolean
  teacherId?: number | null
  teacherName?: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const loading = ref(false)
const dimensionTrend = ref<DimensionTrendPoint[]>([])
const recentStructure = ref<RecentStructurePoint[]>([])
const ruleVersionScope = ref<RuleVersionScope | null>(null)
const selectedRuleVersionId = ref<string | number>('all')
const achievementOverview = ref<AchievementOverview>({
  paper_count: 0,
  project_count: 0,
  intellectual_property_count: 0,
  academic_service_count: 0,
  total_achievements: 0,
  total_score: 0,
})
const dimensionTrendChartRef = ref<HTMLElement | null>(null)
const structureChartRef = ref<HTMLElement | null>(null)
let dimensionTrendChart: echarts.ECharts | null = null
let structureChart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const ruleVersionOptions = computed(() => ruleVersionScope.value?.available_versions ?? [])

const ensureChart = (instance: echarts.ECharts | null, element: HTMLElement | null) => {
  if (!element) {
    instance?.dispose()
    return null
  }
  if (!instance || instance.isDisposed?.() || instance.getDom?.() !== element) {
    instance?.dispose()
    return markRaw(echarts.init(element))
  }
  return instance
}

const renderCharts = async () => {
  await nextTick()
  dimensionTrendChart = ensureChart(dimensionTrendChart, dimensionTrendChartRef.value)
  if (dimensionTrendChart) {
    dimensionTrendChart.setOption(buildDimensionTrendOption(dimensionTrend.value, echarts))
  }
  structureChart = ensureChart(structureChart, structureChartRef.value)
  if (structureChart) {
    structureChart.setOption(buildAchievementStructureOption(recentStructure.value, echarts))
  }
}

const resizeCharts = () => {
  dimensionTrendChart?.resize()
  structureChart?.resize()
}

const resetCharts = () => {
  dimensionTrendChart?.dispose()
  structureChart?.dispose()
  dimensionTrendChart = null
  structureChart = null
  resizeObserver?.disconnect()
  resizeObserver = null
}

const syncRuleVersionScope = (scope?: RuleVersionScope) => {
  if (!scope) return
  ruleVersionScope.value = scope
  selectedRuleVersionId.value = scope.is_all_versions || !scope.selected_rule_version_id
    ? 'all'
    : scope.selected_rule_version_id
}

const loadTrendData = async () => {
  if (!props.teacherId) return
  loading.value = true
  try {
    const { data } = await axios.get<DashboardStatsResponse>('/api/achievements/dashboard-stats/', {
      params: {
        user_id: props.teacherId,
        ...(selectedRuleVersionId.value === 'all' ? {} : { rule_version: selectedRuleVersionId.value }),
      },
    })
    dimensionTrend.value = data.dimension_trend ?? []
    recentStructure.value = data.recent_structure ?? []
    achievementOverview.value = data.achievement_overview ?? achievementOverview.value
    syncRuleVersionScope(data.rule_version_scope)
    await renderCharts()
    resizeObserver?.disconnect()
    resizeObserver = observeElementsResize([dimensionTrendChartRef.value, structureChartRef.value], resizeCharts)
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.teacherId] as const,
  async ([visible, teacherId]) => {
    if (!visible || !teacherId) {
      resetCharts()
      return
    }
    selectedRuleVersionId.value = 'all'
    await loadTrendData()
  },
  { immediate: true },
)

watch(
  () => props.modelValue,
  visible => {
    if (visible) {
      window.addEventListener(WORKSPACE_THEME_CHANGED_EVENT, resizeCharts)
      return
    }
    window.removeEventListener(WORKSPACE_THEME_CHANGED_EVENT, resizeCharts)
  },
)

onUnmounted(() => {
  window.removeEventListener(WORKSPACE_THEME_CHANGED_EVENT, resizeCharts)
  resetCharts()
})
</script>

<style scoped>
.dialog-head {
  display: flex;
  align-items: flex-start;
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
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rule-version-select {
  width: 180px;
}

.dialog-body {
  min-height: 340px;
}

.trend-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
}

.summary-item span {
  display: block;
  color: var(--text-tertiary);
  font-size: 12px;
}

.summary-item strong {
  display: block;
  margin-top: 8px;
  color: var(--text-primary);
  font-size: 20px;
}

.summary-item p {
  margin: 6px 0 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-panel {
  min-width: 0;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
}

.chart-panel__head {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
}

.chart-panel__head strong {
  color: var(--text-primary);
}

.chart-panel__head span {
  color: var(--text-tertiary);
  font-size: 13px;
}

.trend-chart {
  width: 100%;
  height: 360px;
}

@media (max-width: 960px) {
  .dialog-head {
    flex-direction: column;
  }

  .dialog-controls {
    justify-content: flex-start;
  }

  .trend-summary-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
