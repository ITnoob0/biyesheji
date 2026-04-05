<template>
  <div class="assistant-page workspace-page">
    <section class="hero-shell workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">AI Assistant Demo</p>
        <h1 class="workspace-hero__title">智能辅助与问答说明</h1>
        <p class="subtitle workspace-hero__text">
          当前问答只基于系统内真实教师资料、成果聚合、推荐结果和学院统计做受控模板化回答，不包装为通用知识平台。
        </p>
      </div>
      <div class="hero-actions workspace-page-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button type="primary" :loading="loading" @click="submitQuestion">生成说明</el-button>
      </div>
    </section>

    <section v-if="linkContext" class="link-context-shell">
      <el-alert
        :title="linkContextTitle"
        type="info"
        :description="linkContextDescription"
        :closable="false"
        show-icon
      />
    </section>

    <section v-if="showFaqGuide || showSourceGuide" class="assistant-guide-grid">
      <el-card v-if="showFaqGuide" shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>常见问题入口</span>
            <el-tag type="success" effect="plain">摘要优先</el-tag>
          </div>
        </template>
        <div class="reason-list">
          <strong>推荐先从这些模板开始</strong>
          <ul>
            <li v-for="item in faqPrompts" :key="item.title">
              <button type="button" class="assistant-link-button" @click="applyPresetQuestion(item.type)">
                {{ item.title }}
              </button>
            </li>
          </ul>
        </div>
      </el-card>

      <el-card v-if="showSourceGuide" shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>来源说明与证据入口</span>
            <el-tag type="warning" effect="plain">真实系统数据</el-tag>
          </div>
        </template>
        <div class="meta-list">
          <div v-for="item in sourceGuideItems" :key="item.title" class="meta-item">
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
          </div>
        </div>
      </el-card>
    </section>

    <section class="assistant-grid">
      <el-card id="assistant-answer-section" shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>问答输入</span>
            <el-tag type="primary" effect="plain">受控模板</el-tag>
          </div>
        </template>

        <div class="form-grid">
          <el-select v-model="questionType">
            <el-option v-for="item in assistantQuestionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-select
            v-if="questionType === 'guide_reason'"
            v-model="selectedGuideId"
            clearable
            filterable
            placeholder="选择一个推荐项目指南"
          >
            <el-option v-for="item in guideOptions" :key="item.id" :label="item.title" :value="item.id" />
          </el-select>

          <el-select
            v-if="questionType === 'academy_summary'"
            v-model="selectedDepartment"
            clearable
            filterable
            placeholder="管理员可选择院系范围"
          >
            <el-option v-for="item in academyDepartments" :key="item" :label="item" :value="item" />
          </el-select>

          <el-select
            v-if="questionType === 'academy_summary'"
            v-model="selectedYear"
            clearable
            placeholder="管理员可选择年份范围"
          >
            <el-option v-for="item in academyYears" :key="item" :label="`${item} 年`" :value="item" />
          </el-select>
        </div>

        <div class="meta-list">
          <div class="meta-item">
            <strong>当前教师</strong>
            <p>{{ currentTeacherLabel }}</p>
          </div>
          <div class="meta-item">
            <strong>当前数据来源</strong>
            <p>教师资料、成果聚合、推荐规则结果、画像评分与学院实时统计。</p>
          </div>
          <div class="meta-item">
            <strong>当前边界</strong>
            <p>这是模板化、可解释、受控的系统内智能辅助，不是完整知识问答平台。</p>
          </div>
          <div class="meta-item">
            <strong>失败回退</strong>
            <p>问答异常时会回退为基础说明模式，不影响画像、成果、推荐和学院看板等主链路页面。</p>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>问答结果</span>
            <el-tag :type="answerData?.status === 'fallback' ? 'warning' : 'success'" effect="plain">
              {{ answerData?.status === 'fallback' ? '回退说明' : '可解释输出' }}
            </el-tag>
          </div>
        </template>

        <div v-if="!answerData && !loading" class="workspace-empty-state">
          <el-empty description="选择问答场景后，点击“生成说明”即可查看结果。" />
        </div>

        <div v-else-if="answerData" class="answer-shell">
          <el-alert
            v-if="errorNotice"
            :title="errorNotice.message"
            type="warning"
            :description="[errorNotice.guidance, errorNotice.requestHint].filter(Boolean).join(' ')"
            :closable="false"
            show-icon
          />

          <div class="answer-head">
            <div>
              <h2>{{ answerData.title }}</h2>
              <p class="muted">
                <template v-if="answerData.teacher_snapshot">
                  {{ answerData.teacher_snapshot.teacher_name }} · {{ answerData.teacher_snapshot.department || '未填写院系' }}
                </template>
                <template v-else-if="answerData.academy_snapshot">
                  {{ answerData.academy_snapshot.department || '全校' }} · {{ answerData.academy_snapshot.year || '全量时间范围' }}
                </template>
              </p>
            </div>
            <el-tag :type="answerData.status === 'fallback' ? 'warning' : 'primary'" effect="plain">
              {{ answerData.status === 'fallback' ? '问答已降级' : '基于系统数据生成' }}
            </el-tag>
          </div>

          <p class="answer-text">{{ answerData.answer }}</p>

          <el-alert
            v-if="answerData.failure_notice"
            :title="answerData.failure_notice"
            type="warning"
            :closable="false"
            show-icon
          />

          <div v-if="answerData.related_reasons?.length" class="reason-list">
            <strong>依据摘要</strong>
            <ul>
              <li v-for="item in answerData.related_reasons" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="meta-list">
            <div class="meta-item">
              <strong>数据来源</strong>
              <p>{{ answerData.data_sources.join('、') }}</p>
            </div>
            <div class="meta-item">
              <strong>答案边界</strong>
              <p>{{ answerData.non_coverage_note }}</p>
            </div>
            <div class="meta-item">
              <strong>当前验收说明</strong>
              <p>{{ answerData.acceptance_scope }}</p>
            </div>
          </div>

          <div class="source-detail-list">
            <div v-for="item in answerData.source_details" :key="`${item.label}-${item.value}`" class="source-detail-item">
              <div class="source-detail-head">
                <strong>{{ item.label }}</strong>
                <div class="source-detail-tags">
                  <el-tag v-if="resolveSourceModuleLabel(item)" size="small" effect="plain">
                    {{ resolveSourceModuleLabel(item) }}
                  </el-tag>
                  <el-tag v-if="resolveSourcePageLabel(item)" size="small" type="info" effect="plain">
                    {{ resolveSourcePageLabel(item) }}
                  </el-tag>
                  <el-tag size="small" :type="resolveAvailabilityTagType(item.availability_status)" effect="plain">
                    {{ resolveAvailabilityLabel(item) }}
                  </el-tag>
                </div>
              </div>
              <span>{{ item.value }}</span>
              <p>{{ item.note }}</p>
              <p v-if="item.verification_text" class="source-verification-text">{{ item.verification_text }}</p>
              <el-button v-if="item.link" link type="primary" @click="openEvidenceLink(item.link)">
                {{ item.link.label }}
              </el-button>
            </div>
          </div>

          <div v-if="answerData.source_governance" class="governance-panel">
            <strong>来源治理与可验证范围</strong>
            <div class="governance-grid">
              <div class="meta-item">
                <strong>回答模式</strong>
                <p>{{ answerData.source_governance.answer_mode }}</p>
              </div>
              <div class="meta-item">
                <strong>适用范围</strong>
                <p>{{ answerData.source_governance.scope_label }}</p>
              </div>
              <div class="meta-item governance-full">
                <strong>核验方式</strong>
                <p>{{ answerData.source_governance.verification_note }}</p>
              </div>
            </div>

            <div
              v-if="
                answerData.source_governance.degraded_flags?.length ||
                answerData.source_governance.unavailable_flags?.length
              "
              class="governance-flag-grid"
            >
              <div v-if="answerData.source_governance.degraded_flags?.length" class="meta-item">
                <strong>当前降级提示</strong>
                <ul>
                  <li v-for="item in answerData.source_governance.degraded_flags" :key="item">{{ item }}</li>
                </ul>
              </div>
              <div v-if="answerData.source_governance.unavailable_flags?.length" class="meta-item">
                <strong>当前不可用范围</strong>
                <ul>
                  <li v-for="item in answerData.source_governance.unavailable_flags" :key="item">{{ item }}</li>
                </ul>
              </div>
            </div>
          </div>

          <div v-if="answerData.boundary_notes?.length" class="boundary-panel">
            <strong>使用边界提示</strong>
            <ul>
              <li v-for="item in answerData.boundary_notes" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { AssistantAnswerResponse, AssistantQuestionType } from '../types/assistant'
import type { RecommendationItem, RecommendationResponse } from './project-guides/types'
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import { focusEvidenceSection, parseCrossModuleLink, resolveAssistantEvidenceRoute } from '../utils/crossModuleLinking'
import { assistantQuestionOptions, buildAssistantFallbackAnswer, supportedQuestionTypes } from './assistant/helpers.js'
import type { AcademyOverviewResponse } from './academy-dashboard/overview'

type AssistantSection = 'overview' | 'faq' | 'sources'

const props = withDefaults(
  defineProps<{
    sectionMode?: AssistantSection
  }>(),
  {
    sectionMode: 'overview',
  },
)

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const answerData = ref<AssistantAnswerResponse | null>(null)
const questionType = ref<AssistantQuestionType>('portrait_summary')
const selectedGuideId = ref<number | undefined>(undefined)
const selectedDepartment = ref('')
const selectedYear = ref<number | undefined>(undefined)
const activeSection = computed(() => props.sectionMode)
const showFaqGuide = computed(() => activeSection.value === 'faq')
const showSourceGuide = computed(() => activeSection.value === 'sources')
const guideOptions = ref<RecommendationItem[]>([])
const academyDepartments = ref<string[]>([])
const academyYears = ref<number[]>([])
const errorNotice = ref<{ message: string; guidance: string; requestHint: string } | null>(null)
const linkContext = computed(() => parseCrossModuleLink(route.query))

const sourceModuleLabels: Record<string, string> = {
  portrait: '画像模块',
  achievement: '成果模块',
  recommendation: '推荐模块',
  assistant: '问答模块',
  'academy-dashboard': '看板模块',
  graph: '图谱模块',
}

const sourcePageLabels: Record<string, string> = {
  portrait: '教师画像主页',
  recommendations: '项目指南推荐页',
  'achievement-entry': '教师成果录入中心',
  assistant: '智能问答页',
  'academy-dashboard': '学院级统计看板',
}

const currentTeacherId = computed(() => {
  if (currentUser.value?.is_admin && route.query.user_id) {
    return Number(route.query.user_id)
  }
  return currentUser.value?.id
})

const linkContextTitle = computed(() => {
  if (linkContext.value?.source === 'recommendation') {
    return '当前从推荐模块进入，问答会继续保留推荐证据回跳。'
  }
  if (linkContext.value?.source === 'portrait') {
    return '当前从画像模块进入，问答会继续保留画像证据回跳。'
  }
  if (linkContext.value?.source === 'achievement') {
    return '当前从成果模块进入，问答会继续保留成果证据回跳。'
  }
  return '当前问答结果支持回跳到证据页面。'
})

const linkContextDescription = computed(
  () => linkContext.value?.note || '当前问答只基于系统内真实数据生成，来源卡片会回跳到可访问的真实证据区。',
)

const currentTeacherLabel = computed(() => {
  if (questionType.value === 'academy_summary') {
    return '管理员学院统计视角'
  }
  if (currentUser.value?.is_admin && route.query.user_id) {
    return `教师 ${route.query.user_id}`
  }
  return currentUser.value?.real_name || currentUser.value?.username || '当前教师'
})

const faqPrompts = [
  { title: '我的画像主要优势来自哪里？', type: 'portrait_summary' as AssistantQuestionType },
  { title: '哪些成果最能支撑当前画像？', type: 'achievement_portrait_link' as AssistantQuestionType },
  { title: '为什么会推荐这些项目？', type: 'guide_reason' as AssistantQuestionType },
]

const sourceGuideItems = [
  { title: '来源范围', description: '当前问答只使用系统内真实资料、成果、画像、推荐和学院统计，不接入外部知识库。' },
  { title: '失败回退', description: '无数据、权限不足、推荐降级、图谱降级或画像快照缺失时，会给出结构化边界说明，而不是伪装成确定答案。' },
  { title: '证据回跳', description: '当来源卡片提供证据链接时，可以直接回到画像维度区、成果证据区、推荐证据区或学院看板区核验。' },
]

const resolveSourceModuleLabel = (item: NonNullable<AssistantAnswerResponse>['source_details'][number]) =>
  item.module_label || (item.module ? sourceModuleLabels[item.module] || item.module : '')

const resolveSourcePageLabel = (item: NonNullable<AssistantAnswerResponse>['source_details'][number]) =>
  item.page_label || (item.link?.page ? sourcePageLabels[item.link.page] || item.link.page : '')

const resolveAvailabilityLabel = (item: NonNullable<AssistantAnswerResponse>['source_details'][number]) => {
  if (item.availability_label) {
    return item.availability_label
  }
  if (item.availability_status === 'fallback') {
    return '已降级'
  }
  if (item.availability_status === 'limited') {
    return '信息有限'
  }
  return '可验证'
}

const resolveAvailabilityTagType = (status?: 'ok' | 'limited' | 'fallback') => {
  if (status === 'fallback') {
    return 'warning'
  }
  if (status === 'limited') {
    return 'info'
  }
  return 'success'
}

const loadGuideOptions = async () => {
  const params = currentUser.value?.is_admin && currentTeacherId.value ? { user_id: currentTeacherId.value } : undefined
  const { data } = await axios.get<RecommendationResponse>('/api/project-guides/recommendations/', { params })
  guideOptions.value = data.recommendations || []
}

const loadAcademyOptions = async () => {
  if (!currentUser.value?.is_admin) return
  const { data } = await axios.get<AcademyOverviewResponse>('/api/achievements/academy-overview/')
  academyDepartments.value = data.filter_options?.departments || []
  academyYears.value = data.filter_options?.years || []
}

const submitQuestion = async () => {
  loading.value = true
  errorNotice.value = null
  try {
    const payload: Record<string, unknown> = {
      question_type: questionType.value,
    }

    if (questionType.value !== 'academy_summary' && currentUser.value?.is_admin && currentTeacherId.value) {
      payload.user_id = currentTeacherId.value
    }

    if (questionType.value === 'guide_reason') {
      if (!selectedGuideId.value) {
        ElMessage.warning('请选择要解读的项目指南')
        return
      }
      payload.guide_id = selectedGuideId.value
    }

    if (questionType.value === 'academy_summary') {
      payload.department = selectedDepartment.value
      payload.year = selectedYear.value
    }

    const { data } = await axios.post<AssistantAnswerResponse>('/api/ai-assistant/portrait-qa/', payload)
    answerData.value = data
    focusEvidenceSection('assistant-answer-section')
    if (data.status === 'fallback') {
      const sourceReason = data.source_details?.[0]?.value || '当前问答链路已降级。'
      errorNotice.value = {
        message: data.failure_notice || '问答结果已降级为说明模式。',
        guidance: sourceReason,
        requestHint: '',
      }
    }
  } catch (error) {
    console.error(error)
    const isForbidden = axios.isAxiosError(error) && error.response?.status === 403
    const isValidationError = axios.isAxiosError(error) && error.response?.status === 400
    errorNotice.value = buildApiErrorNotice(error, {
      fallbackMessage: isForbidden ? '当前账号无权访问该问答范围。' : '问答结果已降级为基础说明模式。',
      fallbackGuidance: isForbidden
        ? '你仍可继续使用当前账号有权限访问的画像、成果、推荐或看板页面。'
        : isValidationError
          ? '当前问答参数无效，系统已回退为边界说明模式。'
          : '当前问答链路异常不会影响画像、成果、推荐和学院看板等主链路页面。',
    })
    answerData.value = buildAssistantFallbackAnswer(
      questionType.value,
      errorNotice.value.requestHint
        ? `${errorNotice.value.message}（${errorNotice.value.requestHint}）`
        : errorNotice.value.message,
    )
    ElMessage.warning(errorNotice.value.message)
  } finally {
    loading.value = false
  }
}

const openEvidenceLink = (link: NonNullable<AssistantAnswerResponse['source_details'][number]['link']>) => {
  router.push(resolveAssistantEvidenceRoute(link, currentUser.value, answerData.value?.teacher_snapshot?.user_id || currentTeacherId.value))
}

const applyPresetQuestion = (type: AssistantQuestionType) => {
  questionType.value = type
}

const applyRouteQueryContext = async (shouldAutoSubmit = false) => {
  if (route.query.question_type && supportedQuestionTypes.includes(route.query.question_type as AssistantQuestionType)) {
    questionType.value = route.query.question_type as AssistantQuestionType
  }
  if (route.query.guide_id) {
    selectedGuideId.value = Number(route.query.guide_id)
  }
  if (route.query.department) {
    selectedDepartment.value = String(route.query.department)
  }
  if (route.query.year) {
    selectedYear.value = Number(route.query.year)
  }

  if (questionType.value === 'guide_reason') {
    await loadGuideOptions()
  }
  if (questionType.value === 'academy_summary' && currentUser.value?.is_admin) {
    await loadAcademyOptions()
  }
  if (shouldAutoSubmit && route.query.question_type) {
    await submitQuestion()
  }
}

watch(questionType, async nextType => {
  answerData.value = null
  errorNotice.value = null
  if (nextType === 'guide_reason' && !guideOptions.value.length) {
    await loadGuideOptions()
  }
  if (nextType === 'academy_summary' && !academyDepartments.value.length && currentUser.value?.is_admin) {
    await loadAcademyOptions()
  }
})

watch(
  activeSection,
  value => {
    if (value === 'faq' && !answerData.value) {
      questionType.value = 'portrait_summary'
      return
    }

    if (value === 'sources' && !answerData.value) {
      questionType.value = 'portrait_data_governance'
    }
  },
  { immediate: true },
)

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (!currentUser.value) {
    router.replace({ name: 'login' })
    return
  }

  await applyRouteQueryContext(true)
})

watch(
  () => route.query,
  async () => {
    if (!currentUser.value) {
      return
    }
    await applyRouteQueryContext(true)
  },
)
</script>

<style scoped>
.assistant-page {
  min-height: 100%;
  padding: 24px;
  background: var(--page-bg);
  color: var(--text-secondary);
}

.hero-shell {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  max-width: 1180px;
  margin: 0 auto 20px;
  padding: 28px 32px;
  border-radius: 26px;
  background: var(--hero-bg);
  color: var(--text-on-brand);
  box-shadow: var(--workspace-shadow-strong);
}

.assistant-guide-grid {
  max-width: 1180px;
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.assistant-link-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--brand-primary);
  font: inherit;
  cursor: pointer;
}

.assistant-link-button:hover {
  text-decoration: underline;
}

.hero-actions,
.section-head,
.answer-head,
.source-detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.assistant-grid {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  gap: 20px;
}

.link-context-shell {
  max-width: 1180px;
  margin: 0 auto 20px;
}

.assistant-grid :deep(.el-card) {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.eyebrow {
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

h1,
h2 {
  margin: 0;
}

.subtitle,
.muted,
.answer-text,
.meta-item p,
.reason-list ul,
.source-detail-item p,
.boundary-panel ul {
  color: var(--text-tertiary);
  line-height: 1.8;
}

.form-grid,
.meta-list,
.answer-shell,
.source-detail-list,
.governance-grid,
.governance-flag-grid {
  display: grid;
  gap: 16px;
}

.meta-item,
.source-detail-item,
.governance-panel,
.boundary-panel {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.meta-item strong,
.source-detail-item strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.source-detail-item span {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-weight: 600;
}

.source-detail-head {
  align-items: flex-start;
}

.source-detail-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.source-verification-text {
  margin-top: -2px;
  color: var(--brand-primary);
}

.answer-text {
  margin: 0;
  color: var(--text-secondary);
}

.reason-list ul,
.boundary-panel ul,
.governance-panel ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.governance-full {
  grid-column: 1 / -1;
}

@media (max-width: 1080px) {
  .assistant-guide-grid,
  .assistant-grid,
  .hero-shell,
  .hero-actions,
  .source-detail-head {
    grid-template-columns: 1fr;
    display: grid;
  }
}

@media (max-width: 768px) {
  .assistant-page {
    padding: 16px;
  }

  .assistant-guide-grid {
    gap: 16px;
  }
}
</style>
