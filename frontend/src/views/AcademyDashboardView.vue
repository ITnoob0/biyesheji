<script setup lang="ts">
import { computed, markRaw, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import TeacherAchievementPreviewDialog from '../components/teacher/TeacherAchievementPreviewDialog.vue'
import TeacherRadarPreviewDialog from '../components/teacher/TeacherRadarPreviewDialog.vue'
import TeacherTrendPreviewDialog from '../components/teacher/TeacherTrendPreviewDialog.vue'
import { buildAdminRouteNotice } from '../utils/authPresentation.js'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import { observeElementsResize } from '../utils/resizeObserver'
import { WORKSPACE_THEME_CHANGED_EVENT } from '../utils/workspaceTheme'
import {
  buildAcademyTrendOption,
  buildDepartmentDistributionOption,
  buildScopeComparisonOption,
  type AcademyOverviewResponse,
  type DepartmentDistributionRecord,
} from './academy-dashboard/overview'

type AcademyDashboardSection = 'overview' | 'comparison' | 'drilldown' | 'teacher-analysis'
type YearQuickFilter = 'recent_1' | 'recent_3' | 'recent_5'

interface SectionFilterState {
  department: string
  compare_department: string
  teacher_id: number | undefined
  teacher_title: string
  year: string | undefined
}

const YEAR_QUICK_FILTER_OPTIONS: Array<{ label: string; value: YearQuickFilter }> = [
  { label: '近一年', value: 'recent_1' },
  { label: '近三年', value: 'recent_3' },
  { label: '近五年', value: 'recent_5' },
]
const FALLBACK_TEACHER_TITLES = ['教授', '副教授', '讲师', '助教', '研究员', '副研究员', '助理研究员', '研究实习员']

const props = withDefaults(
  defineProps<{
    sectionMode?: AcademyDashboardSection
  }>(),
  {
    sectionMode: 'overview',
  },
)

const router = useRouter()
const checkedUser = ref<SessionUser | null>(null)
const loading = ref(false)
const radarPreviewVisible = ref(false)
const achievementPreviewVisible = ref(false)
const trendPreviewVisible = ref(false)
const previewTeacherId = ref<number | null>(null)
const previewTeacherName = ref('')
const overviewData = ref<AcademyOverviewResponse | null>(null)
const comparisonData = ref<AcademyOverviewResponse | null>(null)
const drilldownData = ref<AcademyOverviewResponse | null>(null)
const teacherAnalysisData = ref<AcademyOverviewResponse | null>(null)

const sectionStates = reactive<Record<AcademyDashboardSection, SectionFilterState>>({
  overview: {
    department: '',
    compare_department: '',
    teacher_id: undefined,
    teacher_title: '',
    year: undefined,
  },
  comparison: {
    department: '',
    compare_department: '',
    teacher_id: undefined,
    teacher_title: '',
    year: undefined,
  },
  drilldown: {
    department: '',
    compare_department: '',
    teacher_id: undefined,
    teacher_title: '',
    year: undefined,
  },
  'teacher-analysis': {
    department: '',
    compare_department: '',
    teacher_id: undefined,
    teacher_title: '',
    year: undefined,
  },
})

const trendChartRef = ref<HTMLElement | null>(null)
const sideChartRef = ref<HTMLElement | null>(null)
const comparisonChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let sideChart: echarts.ECharts | null = null
let comparisonChart: echarts.ECharts | null = null
let chartResizeObserver: ResizeObserver | null = null

const activeSection = computed(() => props.sectionMode)
const isSystemAdmin = computed(() => checkedUser.value?.role_code === 'admin')
const isCollegeAdmin = computed(() => checkedUser.value?.role_code === 'college_admin')
const activeState = computed(() => sectionStates[activeSection.value])
const activeData = computed(() => {
  if (activeSection.value === 'comparison') return comparisonData.value
  if (activeSection.value === 'drilldown') return drilldownData.value
  if (activeSection.value === 'teacher-analysis') return teacherAnalysisData.value
  return overviewData.value
})

const filterOptions = computed(
  () =>
    activeData.value?.filter_options ?? {
      departments: [],
      teacher_titles: [],
      teachers: [],
      years: [],
      achievement_types: [],
      ranking_modes: [],
    },
)
const yearFilterOptions = computed(() => [
  ...YEAR_QUICK_FILTER_OPTIONS,
  ...filterOptions.value.years.map(item => ({
    label: `${item} 年`,
    value: String(item),
  })),
])
const teacherTitleOptions = computed(() => {
  const source = filterOptions.value.teacher_titles?.length ? filterOptions.value.teacher_titles : FALLBACK_TEACHER_TITLES
  return Array.from(new Set(source.filter(Boolean)))
})
const statistics = computed(() => activeData.value?.score_statistics ?? activeData.value?.statistics ?? [])
const countStatistics = computed(() => activeData.value?.statistics ?? [])
const drillTeacherRows = computed(() => drilldownData.value?.top_active_teachers ?? [])
const teacherAnalysisRows = computed(() => teacherAnalysisData.value?.top_active_teachers ?? [])
const departmentDistribution = computed<DepartmentDistributionRecord[]>(() => {
  if (activeSection.value === 'comparison') {
    const compareRecords = comparisonData.value?.comparison_department_distribution ?? []
    if (compareRecords.length) {
      return compareRecords
    }
  }
  return activeData.value?.department_distribution ?? []
})
const countSummary = computed(() => {
  const target = countStatistics.value.find(item => item.title.includes('唯一成果')) ?? countStatistics.value[2]
  return target?.value ?? 0
})
const pendingSummary = computed(() => {
  const target =
    activeData.value?.top_active_teachers?.reduce((sum, item) => sum + Number(item.pending_count || 0), 0) ?? 0
  return target
})
const teacherTotalSummary = computed(() => activeData.value?.comparison_summary?.teacher_total ?? 0)
const dashboardScopeTags = computed(() => [
  { label: '教师总数', value: `${teacherTotalSummary.value} 人` },
  { label: '唯一成果', value: `${countSummary.value} 项` },
  { label: '待审核', value: `${pendingSummary.value} 项` },
])

const ensureChart = (instance: echarts.ECharts | null, element: HTMLElement | null) => {
  if (!element) {
    instance?.dispose()
    return null
  }
  if (instance && instance.getDom() !== element) {
    instance.dispose()
    instance = null
  }
  if (!instance) {
    instance = markRaw(echarts.init(element))
  }
  return instance
}

const renderCharts = async () => {
  await nextTick()
  const data = activeData.value
  if (!data) return

  trendChart = ensureChart(trendChart, trendChartRef.value)
  if (trendChart) {
    trendChart.setOption(buildAcademyTrendOption(data.yearly_trend ?? [], echarts))
  }

  sideChart = ensureChart(sideChart, sideChartRef.value)
  if (sideChart) {
    sideChart.setOption(buildDepartmentDistributionOption(departmentDistribution.value))
  }

  comparisonChart = ensureChart(comparisonChart, comparisonChartRef.value)
  if (comparisonChart) {
    comparisonChart.setOption(buildScopeComparisonOption(data.comparison_trend ?? [], echarts), true)
  }
}

const currentExportTarget = computed(() => {
  if (activeSection.value === 'drilldown' || activeSection.value === 'teacher-analysis') return 'teachers'
  if (activeSection.value === 'overview' && isCollegeAdmin.value) return 'teachers'
  return 'departments'
})

const buildRequestParams = () => {
  const state = activeState.value
  const yearParams = resolveYearFilterParams(state.year)
  const params: Record<string, string | number | undefined> = {
    ...yearParams,
    teacher_title: state.teacher_title || undefined,
  }

  if (activeSection.value === 'comparison') {
    params.department = state.department || undefined
    params.compare_department = state.compare_department || undefined
    return params
  }

  if (activeSection.value === 'drilldown') {
    params.department = state.department || undefined
    params.teacher_id = state.teacher_id
    return params
  }

  if (activeSection.value === 'teacher-analysis') {
    params.teacher_id = state.teacher_id
    params.rank_limit = 'all'
    return params
  }

  if (isSystemAdmin.value) {
    params.department = state.department || undefined
  }
  return params
}

const resolveYearFilterParams = (value: string | undefined): { year?: number; year_from?: number } => {
  if (!value) {
    return {}
  }

  if (value === 'recent_1') {
    return { year_from: new Date().getFullYear() }
  }

  if (value === 'recent_3') {
    return { year_from: new Date().getFullYear() - 2 }
  }

  if (value === 'recent_5') {
    return { year_from: new Date().getFullYear() - 4 }
  }

  const parsed = Number(value)
  if (Number.isFinite(parsed)) {
    return { year: parsed }
  }

  return {}
}

const applyPayload = (payload: AcademyOverviewResponse) => {
  if (activeSection.value === 'comparison') {
    comparisonData.value = payload
    return
  }
  if (activeSection.value === 'drilldown') {
    drilldownData.value = payload
    return
  }
  if (activeSection.value === 'teacher-analysis') {
    teacherAnalysisData.value = payload
    return
  }
  overviewData.value = payload
}

const syncCollegeAdminDefaults = () => {
  if (!isCollegeAdmin.value) return
  const currentDepartment = checkedUser.value?.department || ''
  sectionStates.overview.department = currentDepartment
  sectionStates.comparison.department = currentDepartment
  sectionStates.drilldown.department = currentDepartment
  sectionStates['teacher-analysis'].department = currentDepartment
}

const loadSectionData = async () => {
  loading.value = true
  try {
    const { data } = await axios.get<AcademyOverviewResponse>('/api/achievements/academy-overview/', {
      params: buildRequestParams(),
    })
    applyPayload(data)
    await renderCharts()
  } catch (error: any) {
    if (error?.response?.status === 403) {
      ElMessage.error(buildAdminRouteNotice('学院看板'))
      router.replace('/dashboard')
      return
    }
    ElMessage.error('学院看板加载失败，请检查后端统计接口。')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  const baseDepartment = isCollegeAdmin.value ? checkedUser.value?.department || '' : ''
  sectionStates[activeSection.value] = {
    department: baseDepartment,
    compare_department: '',
    teacher_id: undefined,
    teacher_title: '',
    year: undefined,
  }
  await loadSectionData()
}

const exportCurrentData = async () => {
  const response = await axios.get('/api/achievements/academy-overview/export/', {
    params: {
      ...buildRequestParams(),
      export_target: currentExportTarget.value,
    },
    responseType: 'blob',
  })

  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `academy-dashboard-${activeSection.value}.csv`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出当前统计结果。')
}

const drillTeacher = async (userId: number) => {
  sectionStates.drilldown.teacher_id = userId
  await loadSectionData()
}

const openTeacherProfile = (userId: number, teacherName = '') => {
  previewTeacherId.value = userId
  previewTeacherName.value = teacherName
  radarPreviewVisible.value = true
}

const openTeacherAchievementsPreview = (userId: number, teacherName = '') => {
  previewTeacherId.value = userId
  previewTeacherName.value = teacherName
  achievementPreviewVisible.value = true
}

const openTeacherTrendPreview = (userId: number, teacherName = '') => {
  previewTeacherId.value = userId
  previewTeacherName.value = teacherName
  trendPreviewVisible.value = true
}

const openReviewPage = () => {
  router.push('/teachers/achievement-review')
}

const handleResize = () => {
  trendChart?.resize()
  sideChart?.resize()
  comparisonChart?.resize()
}

const ensureChartResizeObserver = () => {
  chartResizeObserver?.disconnect()
  chartResizeObserver = observeElementsResize([trendChartRef.value, sideChartRef.value, comparisonChartRef.value], handleResize)
}

watch(activeSection, async () => {
  await loadSectionData()
  ensureChartResizeObserver()
})

watch(
  () => activeState.value.department,
  value => {
    if (activeSection.value === 'comparison' && activeState.value.compare_department === value) {
      sectionStates.comparison.compare_department = ''
    }
  },
)

onMounted(async () => {
  checkedUser.value = await ensureSessionUserContext()
  if (!checkedUser.value?.is_admin) {
    return
  }
  syncCollegeAdminDefaults()
  await loadSectionData()
  ensureChartResizeObserver()
  window.addEventListener(WORKSPACE_THEME_CHANGED_EVENT, handleResize)
})

onUnmounted(() => {
  window.removeEventListener(WORKSPACE_THEME_CHANGED_EVENT, handleResize)
  chartResizeObserver?.disconnect()
  chartResizeObserver = null
  trendChart?.dispose()
  sideChart?.dispose()
  comparisonChart?.dispose()
})
</script>

<template>
  <div class="academy-page workspace-page">
    <section class="hero-shell workspace-hero workspace-hero--brand">
      <div class="hero-main">
        <div>
          <p class="eyebrow workspace-hero__eyebrow">Academy Dashboard</p>
          <h1 class="workspace-hero__title">学院看板</h1>
          <p class="subtitle workspace-hero__text">
            {{ isSystemAdmin ? '面向系统管理员查看全校范围的学院对比、教师排行与规则成果积分分布。' : '面向学院管理员查看本院教师的规则成果积分、数量趋势与审核后生效情况。' }}
          </p>
          <div v-if="activeData" class="hero-scope-tags">
            <span v-for="item in dashboardScopeTags" :key="item.label" class="hero-scope-tag">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button plain @click="exportCurrentData">导出当前结果</el-button>
          <el-button v-if="checkedUser?.is_admin" type="primary" @click="openReviewPage">进入成果审核</el-button>
        </div>
      </div>
    </section>

    <div v-if="checkedUser && !checkedUser.is_admin" class="workspace-status-result workspace-content-shell">
      <el-result icon="warning" title="仅管理员可访问学院看板" sub-title="教师账号无法访问学院级统计视图。" />
    </div>

    <template v-else>
      <section class="filter-shell">
        <el-card class="filter-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="section-head workspace-section-head">
              <span>{{ isSystemAdmin ? '筛选与导出' : '本院筛选与导出' }}</span>
              <div class="filter-header-actions">
                <el-button plain @click="resetFilters">重置筛选</el-button>
                <el-button type="success" plain @click="exportCurrentData">导出当前数据</el-button>
              </div>
            </div>
          </template>

          <div class="filter-grid" :class="{ 'filter-grid--compact': isCollegeAdmin }">
            <el-select
              v-if="isSystemAdmin && activeSection !== 'teacher-analysis'"
              v-model="activeState.department"
              clearable
              placeholder="选择学院"
              @change="loadSectionData"
            >
              <el-option v-for="item in filterOptions.departments" :key="item" :label="item" :value="item" />
            </el-select>

            <el-select
              v-if="activeSection === 'comparison' && isSystemAdmin"
              v-model="activeState.compare_department"
              clearable
              placeholder="对比学院"
              @change="loadSectionData"
            >
              <el-option
                v-for="item in filterOptions.departments.filter(option => option !== activeState.department)"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>

            <el-select v-model="activeState.year" clearable placeholder="年份" @change="loadSectionData">
              <el-option v-for="item in yearFilterOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>

            <el-select v-model="activeState.teacher_title" clearable placeholder="职称" @change="loadSectionData">
              <el-option v-for="item in teacherTitleOptions" :key="item" :label="item" :value="item" />
            </el-select>

            <el-select
              v-if="activeSection === 'drilldown' || activeSection === 'teacher-analysis'"
              v-model="activeState.teacher_id"
              clearable
              filterable
              placeholder="教师"
              @change="loadSectionData"
            >
              <el-option
                v-for="item in filterOptions.teachers"
                :key="item.user_id"
                :label="`${item.teacher_name}（${item.department}）`"
                :value="item.user_id"
              />
            </el-select>
          </div>
        </el-card>
      </section>

      <section class="metric-grid">
        <el-card v-for="item in statistics" :key="item.title" class="metric-card workspace-surface-card" shadow="never">
          <span class="metric-label">{{ item.title }}</span>
          <div class="metric-value-row">
            <strong class="metric-value">{{ item.value }}</strong>
            <span class="metric-suffix">{{ item.suffix }}</span>
          </div>
          <p class="metric-helper">{{ item.helper }}</p>
        </el-card>
      </section>

      <template v-if="activeSection === 'overview'">
        <section class="single-row">
          <el-card class="chart-card workspace-surface-card" shadow="never">
            <template #header>
              <div class="section-head workspace-section-head">
                <span>年度积分趋势</span>
                <el-tag type="primary" effect="plain">积分 / 成果 / 活跃教师</el-tag>
              </div>
            </template>
            <div ref="trendChartRef" class="chart-canvas"></div>
          </el-card>
        </section>
      </template>

      <template v-if="activeSection === 'comparison' && isSystemAdmin">
        <section class="chart-row">
          <el-card class="chart-card workspace-surface-card" shadow="never">
            <template #header>
              <div class="section-head workspace-section-head">
                <span>范围积分对比</span>
              </div>
            </template>
            <div ref="comparisonChartRef" class="chart-canvas"></div>
          </el-card>

          <el-card class="chart-card workspace-surface-card" shadow="never">
            <template #header>
              <div class="section-head workspace-section-head">
                <span>学院结构分布</span>
              </div>
            </template>
            <div ref="sideChartRef" class="chart-canvas"></div>
          </el-card>
        </section>

        <section class="single-row">
          <el-card class="meta-card workspace-surface-card" shadow="never">
            <template #header>
              <div class="section-head workspace-section-head">
                <span>对比摘要</span>
              </div>
            </template>
            <div class="meta-list">
              <div class="meta-item">
                <strong>当前范围</strong>
                <p>{{ comparisonData?.comparison_summary.scope_label || '当前筛选范围' }}</p>
              </div>
              <div class="meta-item">
                <strong>对比范围</strong>
                <p>{{ comparisonData?.comparison_summary.compare_label || '全校口径' }}</p>
              </div>
              <div class="meta-item">
                <strong>趋势说明</strong>
                <p>{{ comparisonData?.comparison_summary.description || '暂无对比摘要。' }}</p>
              </div>
            </div>
          </el-card>
        </section>
      </template>

      <template v-if="activeSection === 'drilldown' && isSystemAdmin">
        <section class="single-row">
          <el-card class="rank-card workspace-surface-card" shadow="never">
            <template #header>
              <div class="section-head workspace-section-head">
                <span>学院钻取与教师排行</span>
              </div>
            </template>

            <el-table :data="drillTeacherRows" empty-text="暂无教师统计数据">
              <el-table-column type="index" label="#" width="60" align="center" header-align="center" />
              <el-table-column prop="teacher_name" label="教师" min-width="120" align="center" header-align="center" />
              <el-table-column prop="department" label="学院" min-width="150" align="center" header-align="center" />
              <el-table-column label="核心科研积分" width="120" align="center" header-align="center">
                <template #default="{ row }">{{ row.total_score ?? 0 }}</template>
              </el-table-column>
              <el-table-column prop="achievement_total" label="成果数" width="90" align="center" header-align="center" />
              <el-table-column prop="pending_count" label="待审核" width="90" align="center" header-align="center" />
              <el-table-column label="操作" min-width="200" align="center" header-align="center">
                <template #default="{ row }">
                  <div class="table-actions">
                    <el-button link type="warning" @click="drillTeacher(row.user_id)">钻取</el-button>
                    <el-button link type="primary" @click="openTeacherProfile(row.user_id, row.teacher_name)">画像</el-button>
                    <el-button link type="success" @click="openTeacherAchievementsPreview(row.user_id, row.teacher_name)">成果</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </section>
      </template>

      <template v-if="activeSection === 'teacher-analysis' && (isCollegeAdmin || isSystemAdmin)">
        <section class="single-row">
          <el-card class="rank-card workspace-surface-card" shadow="never">
            <template #header>
              <div class="section-head workspace-section-head">
                <span>{{ isSystemAdmin ? '全校教师分析' : '本院教师分析' }}</span>
                <el-tag effect="plain">{{ teacherAnalysisRows.length }} 名教师</el-tag>
              </div>
            </template>

            <el-table :data="teacherAnalysisRows" empty-text="暂无教师统计数据">
              <el-table-column type="index" label="#" width="60" align="center" header-align="center" />
              <el-table-column prop="teacher_name" label="教师" min-width="120" align="center" header-align="center" />
              <el-table-column v-if="isSystemAdmin" prop="department" label="学院" min-width="150" align="center" header-align="center" />
              <el-table-column prop="title" label="职称" width="110" align="center" header-align="center" />
              <el-table-column label="积分" width="100" align="center" header-align="center">
                <template #default="{ row }">{{ row.total_score ?? 0 }}</template>
              </el-table-column>
              <el-table-column prop="achievement_total" label="成果数" width="90" align="center" header-align="center" />
              <el-table-column prop="pending_count" label="待审核" width="90" align="center" header-align="center" />
              <el-table-column label="操作" width="220" align="center" header-align="center">
                <template #default="{ row }">
                  <div class="table-actions">
                    <el-button link type="primary" @click="openTeacherProfile(row.user_id, row.teacher_name)">画像</el-button>
                    <el-button link type="success" @click="openTeacherAchievementsPreview(row.user_id, row.teacher_name)">成果</el-button>
                    <el-button link type="warning" @click="openTeacherTrendPreview(row.user_id, row.teacher_name)">趋势</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </section>
      </template>
    </template>

    <TeacherRadarPreviewDialog v-model="radarPreviewVisible" :teacher-id="previewTeacherId" :teacher-name="previewTeacherName" />
    <TeacherAchievementPreviewDialog
      v-model="achievementPreviewVisible"
      :teacher-id="previewTeacherId"
      :teacher-name="previewTeacherName"
    />
    <TeacherTrendPreviewDialog v-model="trendPreviewVisible" :teacher-id="previewTeacherId" :teacher-name="previewTeacherName" />
  </div>
</template>

<style scoped>
.academy-page {
  min-height: 100%;
  padding: 24px;
  background: var(--page-bg);
}

.hero-shell {
  margin-bottom: 22px;
  padding: 28px 32px;
  border-radius: 28px;
  background: var(--hero-bg);
  color: var(--text-on-brand);
  box-shadow: var(--workspace-shadow-strong);
}

.hero-main,
.hero-actions,
.section-head,
.filter-header-actions,
.metric-value-row,
.table-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero-main,
.section-head {
  justify-content: space-between;
}

.hero-scope-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.hero-scope-tag {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  min-height: 34px;
  padding: 6px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.86);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.16);
}

.hero-scope-tag strong {
  color: #fff;
  font-size: 15px;
}

.hero-scope-tag span {
  font-size: 12px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

h1 {
  margin: 0;
}

.subtitle {
  margin: 12px 0 0;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.86);
}

.filter-shell,
.metric-grid,
.single-row,
.chart-row,
.overview-bottom-row {
  margin-bottom: 20px;
}

.filter-card,
.metric-card,
.chart-card,
.rank-card,
.meta-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 22px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.filter-grid--compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}

.metric-label,
.metric-helper,
.metric-suffix,
.meta-item p,
.drill-record p {
  color: var(--text-tertiary);
}

.metric-value {
  font-size: 30px;
  color: var(--text-primary);
}

.metric-helper,
.meta-item p,
.drill-record p {
  margin: 0;
  line-height: 1.7;
}

.chart-row,
.overview-bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.overview-bottom-row {
  grid-template-columns: 1.35fr 0.85fr;
}

.overview-bottom-row__wide {
  min-width: 0;
}

.chart-canvas {
  width: 100%;
  height: 420px;
}

.chart-canvas--compact {
  height: 360px;
}

.meta-list,
.drill-list {
  display: grid;
  gap: 14px;
}

.meta-item,
.drill-record {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.meta-item strong,
.drill-record strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.table-actions {
  justify-content: center;
  white-space: nowrap;
}

@media (max-width: 1320px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1180px) {
  .filter-grid,
  .filter-grid--compact,
  .metric-grid,
  .chart-row,
  .overview-bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .academy-page {
    padding: 16px;
  }

  .hero-main,
  .hero-actions,
  .section-head,
  .filter-header-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
