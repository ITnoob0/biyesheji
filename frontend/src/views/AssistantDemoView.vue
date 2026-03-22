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

    <section class="assistant-grid">
      <el-card shadow="never" class="workspace-surface-card">
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
              <strong>{{ item.label }}</strong>
              <span>{{ item.value }}</span>
              <p>{{ item.note }}</p>
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
import { assistantQuestionOptions, buildAssistantFallbackAnswer, supportedQuestionTypes } from './assistant/helpers.js'
import type { AcademyOverviewResponse } from './academy-dashboard/overview'

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const answerData = ref<AssistantAnswerResponse | null>(null)
const questionType = ref<AssistantQuestionType>('portrait_summary')
const selectedGuideId = ref<number | undefined>(undefined)
const selectedDepartment = ref('')
const selectedYear = ref<number | undefined>(undefined)
const guideOptions = ref<RecommendationItem[]>([])
const academyDepartments = ref<string[]>([])
const academyYears = ref<number[]>([])
const errorNotice = ref<{ message: string; guidance: string; requestHint: string } | null>(null)

const currentTeacherId = computed(() => {
  if (currentUser.value?.is_admin && route.query.user_id) {
    return Number(route.query.user_id)
  }
  return currentUser.value?.id
})

const currentTeacherLabel = computed(() => {
  if (questionType.value === 'academy_summary') {
    return '管理员学院统计视角'
  }
  if (currentUser.value?.is_admin && route.query.user_id) {
    return `教师 ${route.query.user_id}`
  }
  return currentUser.value?.real_name || currentUser.value?.username || '当前教师'
})

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
    errorNotice.value = buildApiErrorNotice(error, {
      fallbackMessage: '问答结果已降级为基础说明模式。',
      fallbackGuidance: '当前问答链路异常不会影响画像、成果、推荐和学院看板等主链路页面。',
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

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (!currentUser.value) {
    router.replace({ name: 'login' })
    return
  }

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
})
</script>

<style scoped>
.assistant-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 24%),
    radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.12), transparent 20%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
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
  background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 62%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.14);
}

.hero-actions,
.section-head,
.answer-head {
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

.assistant-grid :deep(.el-card) {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
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
  color: #64748b;
  line-height: 1.8;
}

.form-grid,
.meta-list,
.answer-shell,
.source-detail-list {
  display: grid;
  gap: 16px;
}

.meta-item,
.source-detail-item,
.boundary-panel {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fafc;
}

.meta-item strong,
.source-detail-item strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
}

.source-detail-item span {
  display: block;
  margin-bottom: 6px;
  color: #1e293b;
  font-weight: 600;
}

.answer-text {
  margin: 0;
  color: #334155;
}

.reason-list ul,
.boundary-panel ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

@media (max-width: 1080px) {
  .assistant-grid,
  .hero-shell,
  .hero-actions {
    grid-template-columns: 1fr;
    display: grid;
  }
}

@media (max-width: 768px) {
  .assistant-page {
    padding: 16px;
  }
}
</style>
