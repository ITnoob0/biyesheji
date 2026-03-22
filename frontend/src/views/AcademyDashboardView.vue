<template>
  <div class="academy-page workspace-page">
    <section class="hero-shell workspace-hero workspace-hero--brand">
      <div class="hero-main">
        <div>
          <p class="eyebrow workspace-hero__eyebrow">Academy Overview</p>
          <h1 class="workspace-hero__title">学院级科研统计看板</h1>
          <p class="subtitle workspace-hero__text">面向管理员聚合展示教师、成果、合作与院系统计，聚焦当前阶段可演示、可验收的核心指标。</p>
        </div>
        <div class="hero-actions workspace-page-actions">
          <el-button type="primary" plain :loading="loading" @click="loadOverview">刷新统计</el-button>
          <el-button @click="router.push('/dashboard')">返回教师画像</el-button>
        </div>
      </div>
    </section>

    <div
      v-if="checkedUser && !checkedUser.is_admin"
      class="workspace-status-result workspace-content-shell"
    >
      <el-result
        icon="warning"
        title="仅管理员可访问学院级统计看板"
        sub-title="当前页面为管理端统计视图，教师账号无法访问。"
      />
    </div>

    <template v-else>
      <section class="filter-shell">
        <el-card class="filter-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="section-head workspace-section-head">
              <span>筛选、钻取与导出</span>
              <el-tag type="primary" effect="plain">第三轮增强</el-tag>
            </div>
          </template>

          <div class="filter-grid">
            <el-select v-model="selectedDepartment" clearable placeholder="按学院筛选" @change="loadOverview">
              <el-option v-for="item in filterOptions.departments" :key="item" :label="item" :value="item" />
            </el-select>

            <el-select v-model="selectedYear" clearable placeholder="按年份筛选" @change="loadOverview">
              <el-option v-for="item in filterOptions.years" :key="item" :label="`${item} 年`" :value="item" />
            </el-select>

            <el-select v-model="selectedTeacherId" clearable filterable placeholder="按教师筛选" @change="loadOverview">
              <el-option
                v-for="item in filterOptions.teachers"
                :key="item.user_id"
                :label="`${item.teacher_name}（${item.department}）`"
                :value="item.user_id"
              />
            </el-select>

            <div class="filter-actions">
              <el-button plain @click="resetFilters">重置筛选</el-button>
              <el-button type="success" plain @click="exportTopTeachersCsv">导出当前排行</el-button>
            </div>
          </div>
        </el-card>
      </section>

      <section class="metric-grid">
      <el-card v-for="item in statistics" :key="item.title" class="metric-card workspace-surface-card" shadow="hover">
          <div class="metric-top">
            <span class="metric-label">{{ item.title }}</span>
            <el-icon :class="item.iconClass" :size="22">
              <component :is="item.icon"></component>
            </el-icon>
          </div>
          <div class="metric-value-row">
            <span class="metric-value">{{ item.value }}</span>
            <span v-if="item.suffix" class="metric-suffix">{{ item.suffix }}</span>
          </div>
          <p class="metric-helper">{{ item.helper }}</p>
        </el-card>
      </section>

      <section class="chart-grid">
        <el-card class="chart-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="section-head workspace-section-head">
              <span>年度成果趋势</span>
              <el-tag type="success" effect="plain">MySQL 实时聚合</el-tag>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-canvas"></div>
        </el-card>

        <el-card class="chart-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="section-head workspace-section-head">
              <span>院系统计分布</span>
              <el-tag type="warning" effect="plain">{{ departmentDistribution.length }} 个分组</el-tag>
            </div>
          </template>
          <div ref="departmentChartRef" class="chart-canvas"></div>
        </el-card>
      </section>

      <section class="bottom-grid">
        <el-card class="rank-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="section-head workspace-section-head">
              <span>高活跃教师排行</span>
              <el-tag type="primary" effect="plain">按成果总量排序</el-tag>
            </div>
          </template>

          <el-table :data="topActiveTeachers" empty-text="暂无教师统计数据">
            <el-table-column type="index" label="#" width="56" />
            <el-table-column prop="teacher_name" label="教师" min-width="120" />
            <el-table-column prop="department" label="院系" min-width="150" />
            <el-table-column prop="achievement_total" label="总成果" width="100" />
            <el-table-column prop="paper_count" label="论文" width="90" />
            <el-table-column prop="project_count" label="项目" width="90" />
            <el-table-column label="钻取" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openTeacherProfile(row.user_id)">画像</el-button>
                <el-button link type="success" @click="openTeacherRecommendations(row.user_id)">推荐</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card class="meta-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="section-head workspace-section-head">
              <span>合作活跃度概览</span>
              <el-tag type="info" effect="plain">轻量聚合</el-tag>
            </div>
          </template>

          <div class="meta-panel">
            <div class="meta-item">
              <strong>合作关系总量</strong>
              <p>{{ collaborationOverview.coauthor_relation_total }} 条</p>
            </div>
            <div class="meta-item">
              <strong>有合作记录的教师</strong>
              <p>{{ collaborationOverview.teachers_with_collaboration }} 人</p>
            </div>
            <div class="meta-item">
              <strong>有合作的论文数</strong>
              <p>{{ collaborationOverview.paper_with_collaboration }} 篇</p>
            </div>
            <div class="meta-item">
              <strong>平均每篇论文合作人数</strong>
              <p>{{ collaborationOverview.average_coauthors_per_paper }}</p>
            </div>
          </div>

          <div class="meta-list">
            <div class="meta-item">
              <strong>数据来源说明</strong>
              <p>{{ dataMeta.source_note }}</p>
            </div>
            <div class="meta-item">
              <strong>当前阶段说明</strong>
              <p>{{ dataMeta.acceptance_scope }}</p>
            </div>
            <div class="meta-item">
              <strong>后续扩展预留</strong>
              <p>{{ dataMeta.future_extension_hint }}</p>
            </div>
          </div>
        </el-card>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { markRaw, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { buildAdminRouteNotice } from '../utils/authPresentation.js'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import {
  buildAcademyTrendOption,
  buildDepartmentDistributionOption,
  type AcademyActiveFilters,
  type AcademyFilterOptions,
  type AcademyOverviewResponse,
  type AcademyStatisticItem,
  type CollaborationOverview,
  type DepartmentDistributionRecord,
  type TopActiveTeacherRecord,
  type YearlyTrendRecord,
} from './academy-dashboard/overview'

const router = useRouter()
const checkedUser = ref<SessionUser | null>(null)
const loading = ref(false)
const statistics = ref<AcademyStatisticItem[]>([])
const yearlyTrend = ref<YearlyTrendRecord[]>([])
const departmentDistribution = ref<DepartmentDistributionRecord[]>([])
const topActiveTeachers = ref<TopActiveTeacherRecord[]>([])
const filterOptions = ref<AcademyFilterOptions>({
  departments: [],
  teacher_titles: [],
  teachers: [],
  years: [],
})
const activeFilters = ref<AcademyActiveFilters>({
  department: '',
  teacher_id: null,
  teacher_title: '',
  year: null,
  has_collaboration: null,
})
const collaborationOverview = ref<CollaborationOverview>({
  coauthor_relation_total: 0,
  teachers_with_collaboration: 0,
  paper_with_collaboration: 0,
  average_coauthors_per_paper: 0,
})
const dataMeta = ref({
  source_note: '学院级看板当前基于 MySQL 业务数据实时聚合。',
  acceptance_scope: '本能力属于当前阶段扩展方向。',
  future_extension_hint: '后续可扩展更复杂的学院级统计分析。',
})

const trendChartRef = ref<HTMLElement | null>(null)
const departmentChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let departmentChart: echarts.ECharts | null = null
const selectedDepartment = ref('')
const selectedYear = ref<number | undefined>(undefined)
const selectedTeacherId = ref<number | undefined>(undefined)

const renderCharts = () => {
  if (trendChartRef.value) {
    if (!trendChart) {
      trendChart = markRaw(echarts.init(trendChartRef.value))
    }
    trendChart.setOption(buildAcademyTrendOption(yearlyTrend.value, echarts))
  }

  if (departmentChartRef.value) {
    if (!departmentChart) {
      departmentChart = markRaw(echarts.init(departmentChartRef.value))
    }
    departmentChart.setOption(buildDepartmentDistributionOption(departmentDistribution.value))
  }
}

const loadOverview = async () => {
  loading.value = true
  try {
    const params = {
      department: selectedDepartment.value || undefined,
      year: selectedYear.value || undefined,
      teacher_id: selectedTeacherId.value || undefined,
    }
    const { data } = await axios.get<AcademyOverviewResponse>('/api/achievements/academy-overview/', { params })
    statistics.value = data.statistics || []
    yearlyTrend.value = data.yearly_trend || []
    departmentDistribution.value = data.department_distribution || []
    topActiveTeachers.value = data.top_active_teachers || []
    collaborationOverview.value = data.collaboration_overview || collaborationOverview.value
    dataMeta.value = data.data_meta || dataMeta.value
    filterOptions.value = data.filter_options || filterOptions.value
    activeFilters.value = data.active_filters || activeFilters.value
    renderCharts()
  } catch (error: any) {
    console.error(error)
    if (error?.response?.status === 403) {
      ElMessage.error(buildAdminRouteNotice('学院级统计看板'))
      router.replace('/dashboard')
      return
    }
    ElMessage.error('学院级统计看板加载失败，请检查后端接口状态。')
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  selectedDepartment.value = ''
  selectedYear.value = undefined
  selectedTeacherId.value = undefined
  await loadOverview()
}

const openTeacherProfile = (userId: number) => {
  router.push(`/profile/${userId}`)
}

const openTeacherRecommendations = (userId: number) => {
  router.push({
    name: 'project-recommendations',
    query: { user_id: String(userId) },
  })
}

const exportTopTeachersCsv = () => {
  const rows = [
    ['教师', '院系', '总成果', '论文', '项目'],
    ...topActiveTeachers.value.map(item => [
      item.teacher_name,
      item.department,
      String(item.achievement_total),
      String(item.paper_count),
      String(item.project_count),
    ]),
  ]
  const content =
    '\uFEFF' +
    rows
      .map(row => row.map(value => `"${String(value).split('"').join('""')}"`).join(','))
      .join('\n')
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'academy-dashboard-top-teachers.csv'
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出当前排行 CSV')
}

const handleResize = () => {
  trendChart?.resize()
  departmentChart?.resize()
}

onMounted(async () => {
  checkedUser.value = await ensureSessionUserContext()
  if (checkedUser.value?.is_admin) {
    await loadOverview()
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  departmentChart?.dispose()
})
</script>

<style scoped>
.academy-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 26%),
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 22%),
    linear-gradient(180deg, #f7fbfc 0%, #eef5f8 100%);
}

.hero-shell {
  display: grid;
  gap: 18px;
  margin-bottom: 22px;
  padding: 28px 32px;
  border-radius: 28px;
  background: linear-gradient(130deg, #0f172a 0%, #0f766e 58%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 28px 64px rgba(15, 23, 42, 0.16);
}

.hero-main,
.hero-actions,
.metric-top,
.section-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.hero-actions {
  flex-wrap: wrap;
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
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.8;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.filter-shell {
  margin-bottom: 20px;
}

.filter-card {
  border: none;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.filter-actions {
  display: flex;
  gap: 12px;
}

.metric-card,
.chart-card,
.rank-card,
.meta-card {
  border: none;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.metric-label {
  color: #64748b;
  font-size: 14px;
}

.metric-value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 14px 0 10px;
}

.metric-value {
  font-size: 34px;
  font-weight: 700;
  color: #0f172a;
}

.metric-suffix,
.metric-helper,
.meta-item p {
  color: #64748b;
}

.metric-helper,
.meta-item p {
  margin: 0;
  line-height: 1.7;
}

.chart-grid,
.bottom-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-grid {
  grid-template-columns: 1.15fr 0.85fr;
}

.bottom-grid {
  grid-template-columns: 1.05fr 0.95fr;
}

.chart-canvas {
  width: 100%;
  height: 420px;
}

.meta-panel,
.meta-list {
  display: grid;
  gap: 14px;
}

.meta-panel {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-bottom: 16px;
}

.meta-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fafc;
}

.meta-item strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
}

.icon-blue {
  color: #2563eb;
}

.icon-orange {
  color: #ea580c;
}

.icon-red {
  color: #dc2626;
}

.icon-green {
  color: #059669;
}

@media (max-width: 1320px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1180px) {
  .filter-grid,
  .metric-grid,
  .chart-grid,
  .bottom-grid,
  .meta-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .academy-page {
    padding: 16px;
  }

  .hero-main,
  .hero-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
