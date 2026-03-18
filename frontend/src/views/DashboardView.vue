<template>
  <div class="dashboard-page">
    <section class="hero-shell">
      <div class="hero-main">
        <div class="avatar-block">
          <div class="avatar-badge">{{ portraitInitial }}</div>
          <div class="avatar-meta">
            <p class="eyebrow">Research Portrait</p>
            <h1>{{ teacherInfo.name || '教师画像' }}</h1>
            <p class="subtitle">
              {{ teacherInfo.department || '未设置学院' }} · {{ teacherInfo.title || '未设置职称' }}
            </p>
            <div class="hero-tags">
              <el-tag effect="dark" type="primary">工号 {{ userId }}</el-tag>
              <el-tag effect="plain">{{ teacherInfo.discipline || '待补充学科方向' }}</el-tag>
              <el-tag effect="plain">H-index {{ teacherInfo.hIndex }}</el-tag>
              <el-tag effect="plain">总成果 {{ achievementOverview.total_achievements }} 项</el-tag>
            </div>
          </div>
        </div>

        <div class="hero-summary">
          <p class="summary-title">人物摘要</p>
          <p class="summary-text">{{ teacherInfo.bio || defaultBio }}</p>
          <div class="interest-tags">
            <el-tag v-for="tag in profileHighlights" :key="tag" effect="plain" type="success">
              {{ tag }}
            </el-tag>
            <span v-if="!profileHighlights.length" class="muted">暂未维护研究兴趣</span>
          </div>
        </div>
      </div>

      <div class="hero-actions">
        <el-button type="primary" icon="DocumentAdd" @click="router.push('/entry')">录入成果</el-button>
        <el-button icon="Promotion" @click="openRecommendationPage">项目推荐</el-button>
        <el-button icon="ChatDotRound" @click="openAssistantDemo">智能问答</el-button>
        <el-button icon="Edit" @click="openTeacherProfileEditor">编辑基础档案</el-button>
        <el-button v-if="currentUser?.is_admin" icon="User" @click="router.push('/teachers')">教师管理</el-button>
        <el-button v-if="currentUser?.is_admin" icon="DataAnalysis" @click="router.push('/academy-dashboard')">学院看板</el-button>
        <el-button v-if="currentUser?.is_admin" icon="Reading" @click="router.push('/project-guides')">指南管理</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <el-card v-for="item in statistics" :key="item.title" class="metric-card" shadow="hover">
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
        <div v-if="item.trend !== null && item.trend !== undefined" class="metric-trend" :class="item.trend >= 0 ? 'up' : 'down'">
          <el-icon><CaretTop v-if="item.trend >= 0" /><CaretBottom v-else /></el-icon>
          <span>{{ Math.abs(item.trend) }}%</span>
        </div>
        <p v-else class="metric-helper">{{ item.helper || '基于当前数据实时聚合' }}</p>
      </el-card>
    </section>

    <section class="portrait-grid">
      <el-card class="insight-card" shadow="never">
        <template #header>
          <div class="section-head">
            <span>画像标签</span>
            <el-tag type="warning" effect="plain">{{ achievementOverview.total_achievements }} 项成果联动</el-tag>
          </div>
        </template>

        <div class="insight-block">
          <p class="block-title">核心研究关键词</p>
          <div class="interest-tags">
            <el-tag v-for="keyword in topKeywords" :key="keyword" type="warning" effect="plain">
              {{ keyword }}
            </el-tag>
            <span v-if="!topKeywords.length" class="muted">暂无关键词，录入论文后会自动补充。</span>
          </div>
        </div>

        <div class="insight-block">
          <p class="block-title">主要合作学者</p>
          <div class="interest-tags">
            <el-tag v-for="person in topCollaborators" :key="person" type="info" effect="plain">
              {{ person }}
            </el-tag>
            <span v-if="!topCollaborators.length" class="muted">暂未形成合作网络。</span>
          </div>
        </div>

        <div class="insight-mini-grid">
          <div class="mini-stat">
            <span class="mini-label">论文类型分布</span>
            <strong>{{ paperTypeSummary }}</strong>
          </div>
          <div class="mini-stat">
            <span class="mini-label">近年活跃度</span>
            <strong>{{ latestActiveYear }}</strong>
          </div>
          <div class="mini-stat">
            <span class="mini-label">多成果总量</span>
            <strong>{{ achievementOverview.total_achievements }} 项</strong>
          </div>
          <div class="mini-stat">
            <span class="mini-label">多成果结构</span>
            <strong>{{ achievementMixSummary }}</strong>
          </div>
        </div>
      </el-card>

      <el-card class="radar-card" shadow="never">
        <template #header>
          <div class="section-head">
            <span>综合能力雷达评估</span>
            <el-tag type="success" effect="plain">多成果联动</el-tag>
          </div>
        </template>
        <RadarChart :radarData="radarData" :teacherName="teacherInfo.name" />
        <div class="dimension-source-list">
          <div v-for="item in dimensionSources" :key="item.name" class="dimension-source-item">
            <strong>{{ item.name }}</strong>
            <p>{{ item.description }}</p>
          </div>
        </div>
      </el-card>
    </section>

    <section class="chart-grid">
      <el-card class="graph-card" shadow="never">
        <template #header>
          <div class="section-head">
            <span>学术社交拓扑图</span>
            <el-tag type="primary" effect="plain">实时关系网络</el-tag>
          </div>
        </template>
        <AcademicGraph :userId="userId" />
      </el-card>

      <el-card class="trend-card" shadow="never">
        <template #header>
          <div class="section-head">
            <span>科研产出时间轴</span>
            <el-tag type="info" effect="plain">当前仍基于论文时间序列</el-tag>
          </div>
        </template>
        <div ref="trendChartRef" class="trend-chart"></div>
      </el-card>
    </section>

    <section class="bottom-grid">
      <el-card class="paper-card" shadow="never">
        <template #header>
          <div class="section-head">
            <span>代表性成果</span>
            <el-tag type="success" effect="plain">{{ recentAchievements.length }} 条</el-tag>
          </div>
        </template>

        <div v-if="!recentAchievements.length" class="empty-text">暂无成果记录，可先前往成果录入页补充数据。</div>

        <div v-for="item in recentAchievements" :key="`${item.type}-${item.id}`" class="achievement-item">
          <div class="achievement-head">
            <h3>{{ item.title }}</h3>
            <el-tag :type="resolveAchievementTagType(item.type)" effect="plain">{{ item.type_label }}</el-tag>
          </div>
          <p class="achievement-meta">{{ item.detail }} · {{ item.date_acquired }}</p>
          <p class="achievement-highlight">{{ item.highlight }}</p>
        </div>
      </el-card>

      <el-card class="link-card" shadow="never">
        <template #header>
          <div class="section-head">
            <span>画像说明</span>
            <el-tag type="warning" effect="plain">数据透明</el-tag>
          </div>
        </template>

        <div class="meta-panel">
          <div class="meta-item">
            <strong>数据更新时间</strong>
            <p>{{ portraitUpdatedLabel }}</p>
          </div>
          <div class="meta-item">
            <strong>数据来源说明</strong>
            <p>{{ portraitDataMeta?.source_note || '教师基础档案与多成果记录实时聚合。' }}</p>
          </div>
          <div class="meta-item">
            <strong>当前阶段验收</strong>
            <p>{{ portraitDataMeta?.acceptance_scope || '本页增强纳入当前阶段验收。' }}</p>
          </div>
        </div>

        <div class="link-list">
          <div class="link-item">
            <strong>基础档案联动</strong>
            <p>教师在基础信息页维护学院、职称、学科、研究兴趣后，这里会实时更新画像摘要与标签。</p>
          </div>
          <div class="link-item">
            <strong>多成果联动</strong>
            <p>项目、知识产权、教学成果与学术服务已纳入统计卡片、雷达维度和代表性成果区，不再只从论文视角理解教师能力。</p>
          </div>
          <div class="link-item">
            <strong>论文视角保留</strong>
            <p>关键词、合作画像和时间轴仍保留论文视角，保证当前一期主页结构稳定且解释清晰。</p>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { CaretBottom, CaretTop } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AcademicGraph from './AcademicGraph.vue'
import RadarChart from '../components/RadarChart.vue'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type { TeacherAccountResponse } from '../types/users'
import {
  buildLatestActiveYear,
  buildPaperTypeSummary,
  buildPortraitUpdatedLabel,
  buildProfileHighlights,
  buildTopCollaborators,
  buildTopKeywords,
  buildTrendOption,
  type AchievementOverview,
  type DashboardStatsResponse,
  type DimensionSource,
  type PaperRecord,
  type PortraitDataMeta,
  type RadarResponse,
  type RecentAchievementRecord,
  type StatisticItem,
  type TeacherDetail,
} from './dashboard/portrait'

const route = useRoute()
const router = useRouter()

const currentUser = ref<SessionUser | null>(null)
const userId = ref<number>(0)
const statistics = ref<StatisticItem[]>([])
const radarData = ref<Array<{ name: string; value: number }>>([])
const dimensionSources = ref<DimensionSource[]>([])
const papers = ref<PaperRecord[]>([])
const recentAchievements = ref<RecentAchievementRecord[]>([])
const portraitDataMeta = ref<PortraitDataMeta | null>(null)
const achievementOverview = ref<AchievementOverview>({
  paper_count: 0,
  project_count: 0,
  intellectual_property_count: 0,
  teaching_achievement_count: 0,
  academic_service_count: 0,
  total_citations: 0,
  total_achievements: 0,
})
const teacherInfo = ref<TeacherDetail>({
  id: 0,
  username: '',
  name: '',
  real_name: '',
  department: '',
  title: '',
  discipline: '',
  research_interests: '',
  research_direction: [],
  bio: '',
  h_index: 0,
  hIndex: 0,
  is_admin: false,
})

const trendChartRef = ref<HTMLElement | null>(null)
let trendChartInstance: echarts.ECharts | null = null

const defaultBio = '当前教师尚未完善人物简介，可前往教师基础信息页补充更加完整的研究背景和个人概况。'

const portraitInitial = computed(() => {
  const name = teacherInfo.value.name || teacherInfo.value.real_name || teacherInfo.value.username
  return name ? name.slice(0, 1) : '师'
})

const profileHighlights = computed(() => buildProfileHighlights(teacherInfo.value))
const topKeywords = computed(() => buildTopKeywords(papers.value))
const topCollaborators = computed(() => buildTopCollaborators(papers.value))
const paperTypeSummary = computed(() => buildPaperTypeSummary(papers.value))
const latestActiveYear = computed(() => buildLatestActiveYear(papers.value))
const portraitUpdatedLabel = computed(() => buildPortraitUpdatedLabel(portraitDataMeta.value))

const achievementMixSummary = computed(
  () =>
    `项目 ${achievementOverview.value.project_count} / 知产 ${achievementOverview.value.intellectual_property_count} / 教学 ${achievementOverview.value.teaching_achievement_count} / 服务 ${achievementOverview.value.academic_service_count}`,
)

const resolveTargetUserId = (sessionUser: SessionUser): number => {
  const routeUserId = Number(route.params.id)
  if (sessionUser.is_admin && Number.isFinite(routeUserId) && routeUserId > 0) {
    return routeUserId
  }
  return sessionUser.id
}

const ensureUser = async (): Promise<SessionUser | null> => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return null
  }

  currentUser.value = sessionUser
  userId.value = resolveTargetUserId(sessionUser)
  return sessionUser
}

const loadTeacherDetail = async () => {
  const response = await axios.get<TeacherAccountResponse>(`/api/users/teachers/${userId.value}/`)
  teacherInfo.value = {
    ...response.data,
    name: response.data.real_name || response.data.username,
    hIndex: response.data.h_index ?? 0,
  }
}

const loadDashboardData = async () => {
  const response = await axios.get<DashboardStatsResponse>('/api/achievements/dashboard-stats/', {
    params: currentUser.value?.is_admin ? { user_id: userId.value } : undefined,
  })

  statistics.value = response.data.statistics ?? []
  recentAchievements.value = response.data.recent_achievements ?? []
  portraitDataMeta.value = response.data.data_meta ?? null
  achievementOverview.value = response.data.achievement_overview ?? achievementOverview.value
}

const loadRadarData = async () => {
  const response = await axios.get<RadarResponse>(`/api/achievements/radar/${userId.value}/`)
  radarData.value = response.data.radar_dimensions ?? []
  dimensionSources.value = response.data.dimension_sources ?? []
}

const loadPapers = async () => {
  const response = await axios.get<PaperRecord[]>('/api/achievements/papers/', {
    params: currentUser.value?.is_admin ? { teacher_id: userId.value } : undefined,
  })
  papers.value = response.data ?? []
}

const renderTrendChart = () => {
  if (!trendChartRef.value) return

  if (!trendChartInstance) {
    trendChartInstance = markRaw(echarts.init(trendChartRef.value))
  }

  trendChartInstance.setOption(buildTrendOption(papers.value, echarts))
}

const refreshPortrait = async () => {
  const sessionUser = await ensureUser()
  if (!sessionUser) return

  try {
    await Promise.all([loadTeacherDetail(), loadDashboardData(), loadRadarData(), loadPapers()])
    renderTrendChart()
  } catch (error) {
    console.error(error)
    ElMessage.error('画像数据加载失败，请检查后端接口状态。')
  }
}

const openTeacherProfileEditor = () => {
  router.push({ name: 'teacher-profile-editor' })
}

const openRecommendationPage = () => {
  router.push({
    name: 'project-recommendations',
    query: currentUser.value?.is_admin ? { user_id: String(userId.value) } : undefined,
  })
}

const openAssistantDemo = () => {
  router.push({
    name: 'assistant-demo',
    query: currentUser.value?.is_admin ? { user_id: String(userId.value) } : undefined,
  })
}

const resolveAchievementTagType = (type: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' => {
  const mapping: Record<string, 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
    paper: 'success',
    project: 'primary',
    intellectual_property: 'warning',
    teaching_achievement: 'info',
    academic_service: 'danger',
  }
  return mapping[type] || 'info'
}

const handleResize = () => {
  trendChartInstance?.resize()
}

watch(
  () => route.params.id,
  () => {
    void refreshPortrait()
  },
)

onMounted(() => {
  void refreshPortrait()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.14), transparent 28%),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
}

.hero-shell {
  display: grid;
  gap: 18px;
  margin-bottom: 22px;
  padding: 28px 32px;
  border-radius: 28px;
  background: linear-gradient(130deg, #0f172a 0%, #1d4ed8 62%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 28px 64px rgba(15, 23, 42, 0.16);
}

.hero-main {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 24px;
  align-items: center;
}

.avatar-block {
  display: flex;
  gap: 18px;
  align-items: center;
}

.avatar-badge {
  width: 88px;
  height: 88px;
  border-radius: 26px;
  display: grid;
  place-items: center;
  font-size: 34px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(12px);
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.7);
}

.avatar-meta h1 {
  margin: 0;
  font-size: 34px;
}

.subtitle {
  margin: 10px 0 0;
  color: rgba(255, 255, 255, 0.82);
}

.hero-tags,
.interest-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-tags {
  margin-top: 14px;
}

.hero-summary {
  padding: 20px 22px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.1);
}

.summary-title {
  margin: 0 0 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.72);
}

.summary-text {
  margin: 0 0 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.92);
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card,
.insight-card,
.radar-card,
.graph-card,
.trend-card,
.paper-card,
.link-card {
  border: none;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.metric-top,
.section-head,
.achievement-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
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

.metric-suffix {
  color: #64748b;
}

.metric-trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
}

.metric-trend.up {
  color: #dc2626;
  background: rgba(254, 226, 226, 0.9);
}

.metric-trend.down {
  color: #059669;
  background: rgba(220, 252, 231, 0.9);
}

.metric-helper {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
  font-size: 13px;
}

.portrait-grid,
.chart-grid,
.bottom-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 20px;
}

.portrait-grid {
  grid-template-columns: 1fr 1fr;
}

.chart-grid {
  grid-template-columns: 1.15fr 0.85fr;
}

.bottom-grid {
  grid-template-columns: 1.2fr 0.8fr;
}

.insight-block + .insight-block {
  margin-top: 22px;
}

.block-title {
  margin: 0 0 10px;
  color: #0f172a;
  font-weight: 600;
}

.insight-mini-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 22px;
}

.mini-stat,
.meta-item,
.link-item,
.dimension-source-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fafc;
}

.mini-label {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

.mini-stat strong {
  color: #0f172a;
  font-size: 18px;
}

.dimension-source-list,
.meta-panel,
.link-list {
  display: grid;
  gap: 14px;
}

.dimension-source-list {
  margin-top: 18px;
}

.dimension-source-item strong,
.meta-item strong,
.link-item strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
}

.dimension-source-item p,
.meta-item p,
.link-item p,
.empty-text,
.muted,
.achievement-meta,
.achievement-highlight {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.trend-chart {
  width: 100%;
  height: 440px;
}

.achievement-item + .achievement-item {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #e2e8f0;
}

.achievement-head h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.achievement-meta {
  margin-top: 10px;
}

.achievement-highlight {
  margin-top: 6px;
  color: #334155;
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
  .metric-grid,
  .portrait-grid,
  .chart-grid,
  .bottom-grid,
  .hero-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 16px;
  }

  .hero-shell {
    padding: 24px;
  }

  .avatar-block {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-grid,
  .insight-mini-grid {
    grid-template-columns: 1fr;
  }
}
</style>
