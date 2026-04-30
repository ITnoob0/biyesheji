<template>
  <div class="dashboard-page workspace-page">
    <section v-if="showHeroSection" class="hero-shell workspace-hero workspace-hero--brand">
      <div class="hero-main">
        <div class="avatar-block">
          <div class="avatar-badge">{{ portraitInitial }}</div>
          <div class="avatar-meta">
            <p class="eyebrow workspace-hero__eyebrow">Research Portrait</p>
            <h1 class="workspace-hero__title">{{ teacherInfo.name || '教师画像' }}</h1>
            <p class="subtitle workspace-hero__text">
              {{ teacherInfo.department || '未设置学院' }} · {{ teacherInfo.title || '未设置职称' }}
            </p>
            <div class="hero-tags">
              <el-tag effect="dark" type="primary">工号 {{ userId }}</el-tag>
              <el-tag effect="plain">{{ teacherInfo.discipline || '待补充学科方向' }}</el-tag>
              <el-tag effect="plain">核心科研积分 {{ achievementOverview.total_score ?? 0 }} 分</el-tag>
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

      <div class="hero-actions workspace-page-actions">
        <el-button type="primary" icon="DocumentAdd" @click="router.push('/profile-editor/achievement-entry')">录入成果</el-button>
        <el-button icon="Promotion" @click="openRecommendationPage">项目推荐</el-button>
        <el-button icon="ChatDotRound" @click="openAssistantDemo">智能问答</el-button>
      </div>
    </section>

    <section v-if="linkContext" class="link-context-shell workspace-content-shell">
      <el-alert
        :title="linkContextTitle"
        type="info"
        :description="linkContextDescription"
        :closable="false"
        show-icon
      />
    </section>

    <section v-if="ruleVersionScope" class="rule-version-bar workspace-content-shell">
      <div class="rule-version-main">
        <div>
          <span class="rule-version-label">积分规则口径</span>
          <p>{{ ruleVersionScope.score_scope_note }}</p>
        </div>
        <el-select
          v-model="selectedRuleVersionId"
          class="rule-version-select"
          size="small"
          @change="handleRuleVersionChange"
        >
          <el-option label="全部规则版本累计" value="all" />
          <el-option
            v-for="version in ruleVersionOptions"
            :key="version.id"
            :label="`${version.name}（${version.score_total ?? 0} 分）`"
            :value="version.id"
          />
        </el-select>
      </div>
      <div class="rule-version-tags">
        <el-tag v-if="ruleVersionScope.active_version" size="small" type="success" effect="plain">
          当前启用：{{ ruleVersionScope.active_version.name }}
        </el-tag>
        <el-tag size="small" effect="plain">
          {{ ruleVersionScope.is_all_versions ? '全部版本' : '单版本查看' }}
        </el-tag>
        <span>{{ ruleVersionScope.freeze_note }}</span>
      </div>
    </section>

    <section v-if="showMetricGrid" class="metric-grid">
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
        <div v-if="item.trend !== null && item.trend !== undefined" class="metric-trend" :class="item.trend >= 0 ? 'up' : 'down'">
          <el-icon><CaretTop v-if="item.trend >= 0" /><CaretBottom v-else /></el-icon>
          <span>{{ Math.abs(item.trend) }}%</span>
        </div>
        <p v-else class="metric-helper">{{ item.helper || '基于当前数据实时聚合' }}</p>
      </el-card>
    </section>

    <section v-if="showPortraitGrid" class="portrait-grid">
      <el-card
        id="portrait-dimension-evidence-section"
        class="radar-card workspace-surface-card"
        :class="{ 'evidence-section-highlight': linkContext?.section === 'portrait-dimensions' }"
        shadow="never"
      >
        <template #header>
          <div class="section-head workspace-section-head">
            <span>科研积分结构雷达</span>
            <div class="radar-card-actions">
              <el-button link type="primary" @click="openRecommendationPage">查看推荐理由</el-button>
              <el-button link type="warning" @click="openAssistantDemo">问答说明</el-button>
              <el-button type="primary" plain :loading="reportExporting" @click="exportPortraitReport">导出报告</el-button>
            </div>
          </div>
        </template>
        <div class="radar-evaluation-layout">
          <div class="radar-visual-column">
            <div class="radar-visual-panel">
              <RadarChart :radarData="radarData" :seriesData="radarSeriesData" :teacherName="teacherInfo.name" />
            </div>
          </div>

          <div class="radar-detail-column">
            <div class="dimension-insight-grid">
              <div
                v-for="item in dimensionInsights"
                :id="dimensionEvidenceId(item.key)"
                :key="item.key"
                class="dimension-insight-item"
                :class="{ 'dimension-insight-item--active': linkContext?.dimensionKey === item.key }"
              >
                <div class="dimension-insight-head">
                  <strong>{{ item.name }}</strong>
                  <el-tag size="small" effect="plain" :type="item.level === '优势维度' ? 'success' : item.level === '稳定维度' ? 'info' : 'warning'">
                    {{ item.level }}
                  </el-tag>
                </div>
                <p class="dimension-score-text">雷达展示分 {{ item.value }} 分 · 原始积分 {{ item.raw_score ?? 0 }} 分</p>
                <div class="dimension-rule-box">
                  <div class="dimension-rule-row">
                    <span class="dimension-rule-label">纳入大类</span>
                    <span class="dimension-rule-text">{{ item.source_description }}</span>
                  </div>
                  <div class="dimension-rule-row">
                    <span class="dimension-rule-label">转换公式</span>
                    <span class="dimension-rule-text">{{ item.formula_note }}</span>
                  </div>
                </div>
                <div class="interest-tags dimension-evidence-tags">
                  <el-tag v-for="evidence in item.evidence" :key="evidence" size="small" effect="plain" type="info">
                    {{ evidence }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </section>

    <section v-if="showAnalysisGrid" class="analysis-grid">
      <el-card class="trend-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>画像维度变化趋势</span>
          </div>
        </template>
        <p class="chart-note workspace-chart-note">{{ dimensionTrendNarrative }}</p>
        <div ref="dimensionTrendChartRef" class="trend-chart"></div>
      </el-card>

      <el-card class="structure-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>近年成果结构</span>
          </div>
        </template>
        <p class="chart-note workspace-chart-note">按学术产出、科研项目、奖励转化和平台科普拆解近年成果结构，更容易观察画像重心的变化。</p>
        <div ref="structureChartRef" class="trend-chart"></div>
      </el-card>
    </section>

    <section
      v-if="showSocialGrid || showTrendTimelineCard || activeSection === 'trends'"
      class="chart-grid"
      :class="{
        'chart-grid--single':
          (showTrendTimelineCard && !showSocialGrid && activeSection !== 'trends') ||
          (showSocialGrid && !showTrendTimelineCard),
        'chart-grid--dual': showTrendTimelineCard && activeSection === 'trends' && !showSocialGrid,
      }"
    >
      <el-card
        v-if="showSocialGrid"
        id="portrait-graph-evidence-section"
        class="graph-card workspace-surface-card"
        shadow="never"
        :class="{ 'evidence-section-highlight': linkContext?.section === 'portrait-graph' }"
      >
        <template #header>
          <div class="section-head workspace-section-head">
            <span>学术社交拓扑图</span>
            <el-tag type="primary" effect="plain">实时关系网络</el-tag>
          </div>
        </template>
        <AcademicGraph :userId="userId" />
      </el-card>

      <el-card v-if="showTrendTimelineCard" class="trend-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>学术产出时间轴</span>
          </div>
        </template>
        <div ref="trendChartRef" class="trend-chart"></div>
      </el-card>

      <el-card
        v-if="activeSection === 'trends'"
        class="keyword-card keyword-card--trend workspace-surface-card"
        shadow="never"
      >
        <template #header>
          <div class="section-head workspace-section-head">
            <span>关键词演化与主题聚焦</span>
            <el-tag type="success" effect="plain">{{ themeFocusSummary.label }}</el-tag>
          </div>
        </template>

        <div class="focus-panel">
          <div class="focus-score">
            <strong>{{ themeFocusSummary.ratio }}%</strong>
            <span>Top3 关键词集中度</span>
          </div>
          <p>{{ themeFocusSummary.description }}</p>
          <div class="interest-tags">
            <el-tag v-for="item in themeFocusSummary.topKeywords" :key="item.name" type="warning" effect="plain">
              {{ item.name }} × {{ item.count }}
            </el-tag>
            <span v-if="!themeFocusSummary.topKeywords.length" class="muted">暂无关键词演化数据，补充学术产出关键词后会逐步形成。</span>
          </div>
        </div>

        <div class="keyword-evolution-list">
          <div v-for="item in keywordEvolution" :key="item.year" class="keyword-year-item">
            <div class="keyword-year-head">
              <strong>{{ item.year }} 年</strong>
              <span>{{ item.paperCount }} 项学术产出参与</span>
            </div>
            <div class="interest-tags">
              <el-tag v-for="keyword in item.keywords" :key="`${item.year}-${keyword.name}`" size="small" effect="plain" type="success">
                {{ keyword.name }} × {{ keyword.count }}
              </el-tag>
              <span v-if="!item.keywords.length" class="muted">当年暂无可用关键词。</span>
            </div>
          </div>
        </div>
      </el-card>
    </section>

    <section v-if="showExplainGrid" class="explain-grid" :class="{ 'explain-grid--single': activeSection === 'keywords' }">
      <el-card class="insight-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>画像标签</span>
            <el-tag type="warning" effect="plain">{{ achievementOverview.total_score ?? 0 }} 分成果联动</el-tag>
          </div>
        </template>

        <div class="insight-block">
          <p class="block-title">核心研究关键词</p>
          <div class="interest-tags">
            <el-tag v-for="keyword in topKeywords" :key="keyword" type="warning" effect="plain">
              {{ keyword }}
            </el-tag>
            <span v-if="!topKeywords.length" class="muted">暂无关键词，录入学术产出关键词后会自动补充。</span>
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
            <span class="mini-label">学术产出结构</span>
            <strong>{{ paperTypeSummary }}</strong>
          </div>
          <div class="mini-stat">
            <span class="mini-label">近年活跃度</span>
            <strong>{{ latestActiveYear }}</strong>
          </div>
          <div class="mini-stat">
            <span class="mini-label">核心科研积分</span>
            <strong>{{ achievementOverview.total_score ?? 0 }} 分</strong>
          </div>
          <div class="mini-stat">
            <span class="mini-label">多成果结构</span>
            <strong>{{ achievementMixSummary }}</strong>
          </div>
        </div>
      </el-card>
    </section>

    <PortraitDeepAnalysisPanel
      v-if="showDeepAnalysisPanel"
      :stage-comparison="stageComparison"
      :dimension-insights="dimensionInsights"
      :selected-year="portraitAnalysisYear"
      :available-years="portraitAnalysisAvailableYears"
      :benchmark-scope="portraitBenchmarkScopeSelection"
      :active-benchmark-scope="portraitBenchmarkActiveScope"
      :is-system-admin="isSystemAdminRole"
      @update-year="handlePortraitAnalysisYearChange"
      @update-benchmark-scope="handlePortraitBenchmarkScopeChange"
    />

    <section v-if="showRepresentativeGrid" class="bottom-grid bottom-grid--single">
      <el-card
        id="portrait-achievement-evidence-section"
        class="paper-card workspace-surface-card"
        :class="{ 'evidence-section-highlight': linkContext?.section === 'portrait-achievements' }"
        shadow="never"
      >
        <template #header>
          <div class="section-head workspace-section-head">
            <span>全部成果</span>
            <el-tag type="success" effect="plain">{{ allAchievements.length }} 条</el-tag>
          </div>
        </template>

        <TeacherAchievementListPanel
          :records="allAchievements"
          empty-description="暂无成果记录，可先前往成果录入页补充数据。"
          :resolve-item-id="item => achievementEvidenceId(item.type, item.id)"
          :is-active-record="item => linkContext?.recordType === item.type && linkContext?.recordId === item.id"
        />
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { CaretBottom, CaretTop } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AcademicGraph from './AcademicGraph.vue'
import PortraitDeepAnalysisPanel from './dashboard/PortraitDeepAnalysisPanel.vue'
import RadarChart from '../components/RadarChart.vue'
import TeacherAchievementListPanel from '../components/teacher/TeacherAchievementListPanel.vue'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import {
  focusEvidenceSection,
  parseCrossModuleLink,
} from '../utils/crossModuleLinking'
import { openFloatingAssistant } from '../utils/assistantLauncher'
import type { RuleAchievementRecord } from '../types/ruleAchievements'
import type { TeacherAccountResponse } from '../types/users'
import { buildDimensionTrendNarrative, buildKeywordEvolution, buildThemeFocusSummary } from './dashboard/portraitInsights.js'
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import { observeElementsResize } from '../utils/resizeObserver'
import { WORKSPACE_THEME_CHANGED_EVENT } from '../utils/workspaceTheme'
import { exportPortraitReportPdf } from '../utils/portraitPdfExport'
import {
  buildAchievementStructureOption,
  buildDimensionTrendOption,
  buildLatestActiveYear,
  buildPortraitUpdatedLabel,
  buildProfileHighlights,
  buildTopCollaborators,
  buildTopKeywords,
  buildTrendOption,
  type AllAchievementRecord,
  type AllAchievementResponse,
  type AchievementOverview,
  type CalculationSummary,
  type DashboardStatsResponse,
  type DimensionInsight,
  type DimensionTrendPoint,
  type DimensionSource,
  type PaperRecord,
  type PortraitDataMeta,
  type PortraitExplanation,
  type PortraitAnalysisResponse,
  type PortraitReportResponse,
  type RadarSeriesItem,
  type RadarResponse,
  type RecentStructurePoint,
  type RuleVersionOption,
  type RuleVersionScope,
  type SnapshotBoundary,
  type StageComparison,
  type StatisticItem,
  type TeacherDetail,
  type WeightSpecItem,
} from './dashboard/portrait'

type PortraitSection = 'overview' | 'dimensions' | 'trends' | 'keywords' | 'social' | 'representative'

const props = withDefaults(
  defineProps<{
    sectionMode?: PortraitSection
    userId?: number | string
  }>(),
  {
    sectionMode: 'overview',
    userId: undefined,
  },
)

const route = useRoute()
const router = useRouter()

const currentUser = ref<SessionUser | null>(null)
const userId = ref<number>(0)
const statistics = ref<StatisticItem[]>([])
const radarData = ref<Array<{ name: string; value: number }>>([])
const radarSeriesData = ref<RadarSeriesItem[]>([])
const portraitAnalysisYear = ref<number>(new Date().getFullYear())
const portraitAnalysisAvailableYears = ref<number[]>([])
const portraitBenchmarkScopeSelection = ref<'college' | 'university'>('college')
const portraitBenchmarkActiveScope = ref<'college' | 'university'>('college')
const dimensionSources = ref<DimensionSource[]>([])
const dimensionInsights = ref<DimensionInsight[]>([])
const papers = ref<PaperRecord[]>([])
const allAchievements = ref<AllAchievementRecord[]>([])
const portraitDataMeta = ref<PortraitDataMeta | null>(null)
const dimensionTrend = ref<DimensionTrendPoint[]>([])
const recentStructure = ref<RecentStructurePoint[]>([])
const portraitExplanation = ref<PortraitExplanation | null>(null)
const stageComparison = ref<StageComparison | null>(null)
const snapshotBoundary = ref<SnapshotBoundary | null>(null)
const calculationSummary = ref<CalculationSummary | null>(null)
const weightSpec = ref<WeightSpecItem[]>([])
const portraitReport = ref<PortraitReportResponse | null>(null)
const ruleVersionScope = ref<RuleVersionScope | null>(null)
const selectedRuleVersionId = ref<string | number>('all')
const reportExporting = ref(false)
const achievementOverview = ref<AchievementOverview>({
  paper_count: 0,
  project_count: 0,
  intellectual_property_count: 0,
  academic_service_count: 0,
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
  is_admin: false,
})

const trendChartRef = ref<HTMLElement | null>(null)
const dimensionTrendChartRef = ref<HTMLElement | null>(null)
const structureChartRef = ref<HTMLElement | null>(null)
let trendChartInstance: echarts.ECharts | null = null
let dimensionTrendChartInstance: echarts.ECharts | null = null
let structureChartInstance: echarts.ECharts | null = null
let chartResizeObserver: ResizeObserver | null = null

const defaultBio = '当前教师尚未完善人物简介，可前往教师基础信息页补充更加完整的研究背景和个人概况。'

const portraitInitial = computed(() => {
  const name = teacherInfo.value.name || teacherInfo.value.real_name || teacherInfo.value.username
  return name ? name.slice(0, 1) : '师'
})

const profileHighlights = computed(() => buildProfileHighlights(teacherInfo.value))
const topKeywords = computed(() => buildTopKeywords(papers.value))
const topCollaborators = computed(() => buildTopCollaborators(papers.value))
const paperTypeSummary = computed(() => {
  const articleCount = papers.value.filter(item => item.paper_type_display.includes('论文')).length
  const bookCount = papers.value.filter(item => item.paper_type_display.includes('著作')).length
  const otherCount = Math.max(papers.value.length - articleCount - bookCount, 0)
  return otherCount > 0
    ? `论文 ${articleCount} / 著作 ${bookCount} / 其他 ${otherCount}`
    : `论文 ${articleCount} / 著作 ${bookCount}`
})
const latestActiveYear = computed(() => buildLatestActiveYear(papers.value))
const portraitUpdatedLabel = computed(() => buildPortraitUpdatedLabel(portraitDataMeta.value))
const keywordEvolution = computed(() => buildKeywordEvolution(papers.value))
const themeFocusSummary = computed(() => buildThemeFocusSummary(papers.value))
const dimensionTrendNarrative = computed(() => buildDimensionTrendNarrative(dimensionTrend.value))
const linkContext = computed(() => parseCrossModuleLink(route.query))
const ruleVersionOptions = computed<RuleVersionOption[]>(() => ruleVersionScope.value?.available_versions ?? [])

const linkContextTitle = computed(() => {
  if (linkContext.value?.source === 'achievement') {
    return '当前从成果模块回跳，已定位到画像证据区。'
  }
  if (linkContext.value?.source === 'recommendation') {
    return '当前从推荐模块回跳，已定位到对应画像证据区。'
  }
  if (linkContext.value?.source === 'assistant') {
    return '当前从问答来源卡片回跳，已定位到对应画像证据区。'
  }
  return '当前已定位到画像证据区。'
})

const linkContextDescription = computed(
  () =>
    linkContext.value?.note ||
    '当前联动只基于当前权限范围内的真实画像与成果数据，不会跳到无证据支撑的占位页面。',
)

const achievementMixSummary = computed(
  () =>
    `项目 ${achievementOverview.value.project_score ?? 0} 分 / 获奖转化 ${achievementOverview.value.intellectual_property_score ?? 0} 分 / 平台科普 ${achievementOverview.value.academic_service_score ?? 0} 分`,
)

const activeSection = computed(() => props.sectionMode)
const isSystemAdminRole = computed(() => currentUser.value?.role_code === 'admin')
const showHeroSection = computed(() => activeSection.value === 'overview')
const showMetricGrid = computed(() => activeSection.value === 'overview')
const showPortraitGrid = computed(() => ['overview', 'dimensions'].includes(activeSection.value))
const showAnalysisGrid = computed(() => activeSection.value === 'trends')
const showSocialGrid = computed(() => activeSection.value === 'social')
const showTrendTimelineCard = computed(() => activeSection.value === 'trends')
const showExplainGrid = computed(() => activeSection.value === 'keywords')
const showDeepAnalysisPanel = computed(() => activeSection.value === 'trends')
const showRepresentativeGrid = computed(() => activeSection.value === 'representative')

const resolveTargetUserId = (sessionUser: SessionUser): number => {
  const routeUserId = Number(props.userId ?? route.params.id)
  if (sessionUser.is_admin && Number.isFinite(routeUserId) && routeUserId > 0) {
    return routeUserId
  }
  return sessionUser.id
}

const dimensionEvidenceId = (dimensionKey: string) => `portrait-dimension-${dimensionKey}`

const achievementEvidenceId = (type: string, id: number) => `portrait-achievement-${type}-${id}`

const isActiveAchievementEvidence = (type: string, id: number) =>
  linkContext.value?.recordType === type && linkContext.value?.recordId === id

const buildRuleVersionParams = (): Record<string, string | number> => {
  if (selectedRuleVersionId.value === 'all') {
    return {}
  }
  return { rule_version: selectedRuleVersionId.value }
}

const syncRuleVersionScope = (scope?: RuleVersionScope) => {
  if (!scope) return
  ruleVersionScope.value = scope
  const nextValue = scope.is_all_versions || !scope.selected_rule_version_id ? 'all' : scope.selected_rule_version_id
  if (String(selectedRuleVersionId.value) !== String(nextValue)) {
    selectedRuleVersionId.value = nextValue
  }
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
  if (currentUser.value?.is_admin && userId.value === currentUser.value.id) {
    const response = await axios.get<TeacherAccountResponse>('/api/users/me/')
    teacherInfo.value = {
      ...response.data,
      name: response.data.real_name || response.data.username,
    }
    return
  }

  const response = await axios.get<TeacherAccountResponse>(`/api/users/teachers/${userId.value}/`)
  teacherInfo.value = {
    ...response.data,
    name: response.data.real_name || response.data.username,
  }
}

const loadDashboardData = async () => {
  const response = await axios.get<DashboardStatsResponse>('/api/achievements/dashboard-stats/', {
    params: {
      ...(currentUser.value?.is_admin ? { user_id: userId.value } : {}),
      ...buildRuleVersionParams(),
    },
  })

  statistics.value = response.data.statistics ?? []
  dimensionTrend.value = response.data.dimension_trend ?? []
  recentStructure.value = response.data.recent_structure ?? []
  portraitExplanation.value = response.data.portrait_explanation ?? null
  dimensionInsights.value = response.data.dimension_insights ?? []
  weightSpec.value = response.data.weight_spec ?? []
  calculationSummary.value = response.data.calculation_summary ?? null
  portraitDataMeta.value = response.data.data_meta ?? null
  achievementOverview.value = response.data.achievement_overview ?? achievementOverview.value
  syncRuleVersionScope(response.data.rule_version_scope)
}

const loadAllAchievements = async () => {
  const response = await axios.get<AllAchievementResponse>(`/api/achievements/all-achievements/${userId.value}/`, {
    params: buildRuleVersionParams(),
  })
  allAchievements.value = response.data.records ?? []
  syncRuleVersionScope(response.data.rule_version_scope)
}

const loadRadarData = async () => {
  const response = await axios.get<RadarResponse>(`/api/achievements/radar/${userId.value}/`, {
    params: buildRuleVersionParams(),
  })
  dimensionSources.value = response.data.dimension_sources ?? []
  dimensionInsights.value = response.data.dimension_insights ?? dimensionInsights.value
  weightSpec.value = response.data.weight_spec ?? weightSpec.value
  calculationSummary.value = response.data.calculation_summary ?? calculationSummary.value
  syncRuleVersionScope(response.data.rule_version_scope)
}

const loadPortraitAnalysis = async () => {
  const params: Record<string, string | number> = {
    year: portraitAnalysisYear.value,
    scope: isSystemAdminRole.value ? portraitBenchmarkScopeSelection.value : 'college',
    ...buildRuleVersionParams(),
  }
  if (currentUser.value?.is_admin) {
    params.user_id = userId.value
  }

  const response = await axios.get<PortraitAnalysisResponse>('/api/achievements/portrait/analysis/', {
    params,
  })
  const payload = response.data
  portraitAnalysisYear.value = Number(payload.year || portraitAnalysisYear.value)
  portraitAnalysisAvailableYears.value = (payload.available_years || [])
    .map(item => Number(item))
    .filter(item => Number.isFinite(item))
  stageComparison.value = payload.stage_comparison ?? null
  snapshotBoundary.value = payload.snapshot_boundary ?? null
  radarData.value = payload.radar_dimensions ?? []
  radarSeriesData.value = payload.radar_series_data ?? []
  syncRuleVersionScope(payload.rule_version_scope)

  const activeScope = payload.benchmark_data?.active_scope
  portraitBenchmarkActiveScope.value = activeScope === 'university' ? 'university' : 'college'
  if (!isSystemAdminRole.value) {
    portraitBenchmarkScopeSelection.value = 'college'
  }
}

const loadPortraitReport = async () => {
  const response = await axios.get<PortraitReportResponse>(`/api/achievements/portrait-report/${userId.value}/`, {
    params: buildRuleVersionParams(),
  })
  portraitReport.value = response.data
  syncRuleVersionScope(response.data.rule_version_scope)
}

type ViewTransitionDocument = Document & {
  startViewTransition?: (callback: () => void | Promise<void>) => { finished: Promise<void> }
}

const runRadarViewTransition = async (task: () => Promise<void>): Promise<void> => {
  const transitionDocument = document as ViewTransitionDocument
  if (typeof transitionDocument.startViewTransition === 'function') {
    const transition = transitionDocument.startViewTransition(() => task())
    await transition.finished
    return
  }
  await task()
}

const mapRuleAchievementsToPaperRecords = (records: RuleAchievementRecord[]): PaperRecord[] =>
  records
    .filter(record => record.category_code === 'PAPER_BOOK' && record.status === 'APPROVED')
    .map(record => ({
      id: record.id,
      title: record.title,
      date_acquired: record.date_acquired,
      paper_type_display: record.rule_item_title || record.category_name || '学术成果',
      journal_name: record.publication_name || record.issuing_organization || '',
      keywords: (record.keywords_text || '')
        .split(/[，、,\s]+/)
        .map(item => item.trim())
        .filter(Boolean),
      coauthor_details: (record.coauthor_names || []).map((name, index) => ({
        id: index + 1,
        name,
      })),
    }))

const loadPapers = async () => {
  const response = await axios.get<RuleAchievementRecord[]>('/api/achievements/rule-achievements/', {
    params: {
      ...(currentUser.value?.is_admin ? { teacher_id: userId.value } : {}),
      status: 'APPROVED',
      ...buildRuleVersionParams(),
    },
  })
  papers.value = mapRuleAchievementsToPaperRecords(response.data ?? [])
}

const handlePortraitAnalysisYearChange = async (year: number) => {
  if (!Number.isFinite(year) || year === portraitAnalysisYear.value) {
    return
  }
  portraitAnalysisYear.value = year
  await runRadarViewTransition(loadPortraitAnalysis)
}

const handlePortraitBenchmarkScopeChange = async (scope: 'college' | 'university') => {
  if (!isSystemAdminRole.value) {
    return
  }
  if (scope === portraitBenchmarkScopeSelection.value) {
    return
  }
  portraitBenchmarkScopeSelection.value = scope
  await runRadarViewTransition(loadPortraitAnalysis)
}

const handleRuleVersionChange = async () => {
  portraitReport.value = null
  await runRadarViewTransition(async () => {
    await Promise.all([
      loadDashboardData(),
      loadRadarData(),
      loadPortraitAnalysis(),
      loadPapers(),
      loadPortraitReport(),
      loadAllAchievements(),
    ])
  })
  renderTrendChart()
  renderDimensionTrendChart()
  renderStructureChart()
}

const ensureChartInstance = (
  element: HTMLElement | null,
  instance: echarts.ECharts | null,
): echarts.ECharts | null => {
  if (!element) {
    return null
  }

  if (!instance || instance.isDisposed?.() || instance.getDom?.() !== element) {
    instance?.dispose()
    return markRaw(echarts.init(element))
  }

  return instance
}

const renderTrendChart = () => {
  if (!trendChartRef.value) return

  trendChartInstance = ensureChartInstance(trendChartRef.value, trendChartInstance)
  if (!trendChartInstance) return

  trendChartInstance.setOption(buildTrendOption(papers.value, echarts))
}

const renderDimensionTrendChart = () => {
  if (!dimensionTrendChartRef.value) return

  dimensionTrendChartInstance = ensureChartInstance(dimensionTrendChartRef.value, dimensionTrendChartInstance)
  if (!dimensionTrendChartInstance) return

  dimensionTrendChartInstance.setOption(buildDimensionTrendOption(dimensionTrend.value, echarts))
}

const renderStructureChart = () => {
  if (!structureChartRef.value) return

  structureChartInstance = ensureChartInstance(structureChartRef.value, structureChartInstance)
  if (!structureChartInstance) return

  structureChartInstance.setOption(buildAchievementStructureOption(recentStructure.value, echarts))
}

const refreshPortrait = async () => {
  const sessionUser = await ensureUser()
  if (!sessionUser) return
  portraitAnalysisYear.value = new Date().getFullYear()
  portraitBenchmarkScopeSelection.value = isSystemAdminRole.value ? portraitBenchmarkScopeSelection.value : 'college'

  try {
    await Promise.all([
      loadTeacherDetail(),
      loadDashboardData(),
      loadRadarData(),
      loadPortraitAnalysis(),
      loadPapers(),
      loadPortraitReport(),
      loadAllAchievements(),
    ])
    renderTrendChart()
    renderDimensionTrendChart()
    renderStructureChart()
    await nextTick()
    focusDashboardEvidence()
  } catch (error) {
    console.error(error)
    const errorNotice = buildApiErrorNotice(error, {
      fallbackMessage: '画像数据加载失败，请稍后重试。',
      fallbackGuidance: currentUser.value?.is_admin
        ? '管理员可返回教师管理查看指定教师画像，或继续查看当前管理员画像。'
        : '请确认当前登录状态正常，或稍后重试。',
    })

    ElMessage.error([errorNotice.message, errorNotice.guidance].filter(Boolean).join(' '))
  }
}

const focusDashboardEvidence = () => {
  if (!linkContext.value?.section) {
    return
  }

  if (linkContext.value.section === 'portrait-dimensions') {
    focusEvidenceSection(
      'portrait-dimension-evidence-section',
      linkContext.value.dimensionKey ? dimensionEvidenceId(linkContext.value.dimensionKey) : undefined,
    )
    return
  }

  if (linkContext.value.section === 'portrait-achievements') {
    focusEvidenceSection(
      'portrait-achievement-evidence-section',
      linkContext.value.recordType && linkContext.value.recordId
        ? achievementEvidenceId(linkContext.value.recordType, linkContext.value.recordId)
        : undefined,
    )
    return
  }

  if (linkContext.value.section === 'portrait-explanation') {
    focusEvidenceSection('portrait-explanation-evidence-section')
    return
  }

  if (linkContext.value.section === 'portrait-graph') {
    focusEvidenceSection('portrait-graph-evidence-section')
  }
}

const exportPortraitReport = async () => {
  reportExporting.value = true
  try {
    if (!portraitReport.value) {
      await loadPortraitReport()
    }
    if (!portraitReport.value) {
      throw new Error('portrait report unavailable')
    }
    const pdfBlob = await exportPortraitReportPdf({
      teacherName: teacherInfo.value.name || teacherInfo.value.real_name || teacherInfo.value.username || '教师',
      report: portraitReport.value,
      calculationSummary: calculationSummary.value,
      weightSpec: weightSpec.value,
      stageComparison: stageComparison.value,
    })
    const blobUrl = window.URL.createObjectURL(pdfBlob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = `teacher-portrait-report-${userId.value}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)
    ElMessage.success('教师画像 PDF 报告已导出。')
  } catch (error) {
    console.error(error)
    ElMessage.error('教师画像 PDF 报告导出失败，请稍后重试。')
  } finally {
    reportExporting.value = false
  }
}

const openRecommendationPage = () => {
  router.push({
    name: 'project-recommendations',
    query: currentUser.value?.is_admin ? { user_id: String(userId.value) } : undefined,
  })
}

const openAssistantDemo = () => {
  openFloatingAssistant({
    contextHint: 'portrait',
    draft: '请总结我当前教师画像的优势、短板以及下一步建议。',
  })
}

const handleResize = () => {
  trendChartInstance?.resize()
  dimensionTrendChartInstance?.resize()
  structureChartInstance?.resize()
}

const handleThemeChanged = () => {
  renderTrendChart()
  renderDimensionTrendChart()
  renderStructureChart()
  handleResize()
}

const ensureChartResizeObserver = () => {
  if (chartResizeObserver) {
    return
  }
  chartResizeObserver = observeElementsResize(
    [trendChartRef.value, dimensionTrendChartRef.value, structureChartRef.value],
    handleResize,
  )
}

watch(
  () => route.params.id,
  () => {
    void refreshPortrait()
  },
)

watch(
  activeSection,
  async section => {
    await nextTick()

    if (section === 'trends') {
      renderTrendChart()
      renderDimensionTrendChart()
      renderStructureChart()
      handleResize()
      ensureChartResizeObserver()
      return
    }

    if (section === 'social') {
      handleResize()
      return
    }

    if (section === 'overview') {
      handleResize()
    }
  },
)

watch(linkContext, () => {
  focusDashboardEvidence()
})

onMounted(() => {
  void refreshPortrait()
  nextTick(() => {
    ensureChartResizeObserver()
  })
  window.addEventListener(WORKSPACE_THEME_CHANGED_EVENT, handleThemeChanged)
})

onUnmounted(() => {
  window.removeEventListener(WORKSPACE_THEME_CHANGED_EVENT, handleThemeChanged)
  chartResizeObserver?.disconnect()
  chartResizeObserver = null
  trendChartInstance?.dispose()
  dimensionTrendChartInstance?.dispose()
  structureChartInstance?.dispose()
  trendChartInstance = null
  dimensionTrendChartInstance = null
  structureChartInstance = null
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100%;
  padding: 24px 24px 56px;
  background: var(--page-bg);
  color: var(--text-secondary);
}

.hero-shell {
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
  padding: 24px 28px;
  border-radius: 28px;
  background: var(--hero-bg);
  color: var(--text-on-brand);
  box-shadow: var(--workspace-shadow-strong);
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
  background: var(--hero-bg-soft);
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
  margin-bottom: 16px;
}

.link-context-shell {
  margin-bottom: 20px;
}

.rule-version-bar {
  display: grid;
  gap: 10px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid var(--border-color-soft);
  border-radius: 14px;
  background: var(--surface-1);
}

.rule-version-main,
.rule-version-tags {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.rule-version-label {
  color: var(--text-primary);
  font-weight: 600;
}

.rule-version-main p,
.rule-version-tags span {
  margin: 4px 0 0;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.rule-version-select {
  width: min(320px, 100%);
}

.metric-card,
.insight-card,
.radar-card,
.graph-card,
.trend-card,
.structure-card,
.keyword-card,
.paper-card,
.link-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 22px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
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
  color: var(--text-tertiary);
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
  color: var(--text-primary);
}

.metric-suffix {
  color: var(--text-tertiary);
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
  color: var(--text-tertiary);
  line-height: 1.6;
  font-size: 13px;
}

.radar-card-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.portrait-grid,
.analysis-grid,
.chart-grid,
.explain-grid,
.bottom-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 16px;
}

.portrait-grid {
  grid-template-columns: 1fr;
}

.chart-grid {
  grid-template-columns: 1.15fr 0.85fr;
}

.chart-grid--single {
  grid-template-columns: 1fr;
}

.chart-grid--dual {
  grid-template-columns: 1fr 1fr;
  align-items: stretch;
}

.analysis-grid,
.explain-grid {
  grid-template-columns: 1fr 1fr;
}

.explain-grid--single {
  grid-template-columns: 1fr;
}

.bottom-grid {
  grid-template-columns: 1.2fr 0.8fr;
}

.bottom-grid--single {
  grid-template-columns: 1fr;
}

.radar-evaluation-layout {
  display: grid;
  grid-template-columns: minmax(300px, 0.78fr) minmax(0, 1.22fr);
  gap: 16px;
  align-items: stretch;
}

.radar-visual-column {
  display: flex;
  align-items: center;
  justify-content: center;
}

.radar-visual-panel {
  width: 100%;
  max-width: 380px;
}

.radar-detail-column {
  min-width: 0;
}

.insight-block + .insight-block {
  margin-top: 22px;
}

.block-title {
  margin: 0 0 10px;
  color: var(--text-primary);
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
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.mini-label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.mini-stat strong {
  color: var(--text-primary);
  font-size: 18px;
}

.dimension-source-list,
.dimension-insight-grid,
.meta-panel,
.link-list {
  display: grid;
  gap: 14px;
}

.dimension-source-list {
  margin-top: 18px;
}

.dimension-insight-grid {
  margin-top: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.dimension-evidence-tags {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.dimension-evidence-tags :deep(.el-tag) {
  width: 100%;
  height: auto;
  min-height: 26px;
  justify-content: center;
  margin: 0;
  padding: 4px 8px;
  white-space: normal;
  line-height: 1.35;
  text-align: center;
}

.dimension-insight-item {
  padding: 10px 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, var(--surface-2) 0%, var(--panel-bg) 100%);
  border: 1px solid var(--border-color-soft);
  display: grid;
  gap: 6px;
}

.dimension-insight-item--active,
.achievement-item--active,
.evidence-section-highlight {
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.18);
  background: linear-gradient(180deg, color-mix(in srgb, var(--brand-primary) 12%, var(--surface-2)) 0%, var(--surface-1) 100%);
}

.dimension-insight-head,
.keyword-year-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dimension-source-item strong,
.meta-item strong,
.link-item strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.dimension-source-item p,
.chart-note,
.dimension-score-text,
.dimension-formula-text,
.meta-item p,
.link-item p,
.empty-text,
.muted,
.achievement-meta,
.achievement-highlight {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.45;
}

.dimension-insight-item p {
  font-size: 14px;
}

.dimension-formula-text {
  color: var(--text-secondary);
}

.dimension-rule-box {
  display: grid;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--brand-primary) 16%, var(--border-color-soft));
  border-radius: 10px;
  background: color-mix(in srgb, var(--brand-primary) 5%, var(--surface-1));
}

.dimension-rule-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.dimension-rule-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
}

.dimension-rule-text {
  min-width: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.55;
  word-break: break-word;
}

.chart-note {
  margin-bottom: 14px;
}

.focus-panel {
  display: grid;
  gap: 12px;
  margin-bottom: 18px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 12%, var(--surface-2)) 0%, var(--surface-2) 100%);
  border: 1px solid var(--border-color-soft);
}

.focus-score {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.focus-score strong {
  font-size: 32px;
  color: var(--text-primary);
}

.focus-score span,
.keyword-year-head span {
  color: var(--text-tertiary);
}

.keyword-evolution-list {
  display: grid;
  gap: 14px;
}

.keyword-year-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
  display: grid;
  gap: 12px;
}

.trend-chart {
  width: 100%;
  height: 440px;
}

.keyword-card--trend {
  height: 100%;
}

.achievement-item + .achievement-item {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid var(--divider-color);
}

.achievement-head h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.achievement-meta {
  margin-top: 10px;
}

.achievement-highlight {
  margin-top: 6px;
  color: var(--text-secondary);
}

.dimension-evidence-actions,
.achievement-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
  .analysis-grid,
  .chart-grid,
  .explain-grid,
  .bottom-grid,
  .radar-evaluation-layout,
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
  .insight-mini-grid,
  .dimension-insight-grid {
    grid-template-columns: 1fr;
  }

  .dimension-evidence-tags {
    grid-template-columns: 1fr;
  }

  .dimension-rule-row {
    grid-template-columns: 1fr;
  }

  .dimension-rule-label {
    width: fit-content;
  }
}
</style>
