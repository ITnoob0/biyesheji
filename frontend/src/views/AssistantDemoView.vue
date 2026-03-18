<template>
  <div class="assistant-page">
    <section class="hero-shell">
      <div>
        <p class="eyebrow">AI Assistant Demo</p>
        <h1>轻量智能问答演示</h1>
        <p class="subtitle">
          当前演示仅基于系统内真实教师资料、成果聚合与推荐结果生成说明，不依赖外部知识库或复杂多轮问答。
        </p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button type="primary" :loading="loading" @click="submitQuestion">生成说明</el-button>
      </div>
    </section>

    <section class="assistant-grid">
      <el-card shadow="never">
        <template #header>
          <div class="section-head">
            <span>问答输入</span>
            <el-tag type="primary" effect="plain">单场景演示</el-tag>
          </div>
        </template>

        <div class="form-grid">
          <el-select v-model="questionType">
            <el-option label="教师科研画像总结" value="portrait_summary" />
            <el-option label="教师近年成果结构概括" value="achievement_summary" />
            <el-option label="项目指南推荐原因说明" value="guide_reason" />
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
        </div>

        <div class="meta-list">
          <div class="meta-item">
            <strong>当前教师</strong>
            <p>{{ currentTeacherLabel }}</p>
          </div>
          <div class="meta-item">
            <strong>数据来源</strong>
            <p>教师资料、成果聚合、推荐结果和画像评分。</p>
          </div>
          <div class="meta-item">
            <strong>当前边界</strong>
            <p>这是轻量、可解释、单场景问答，不是完整知识问答平台。</p>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="section-head">
            <span>问答结果</span>
            <el-tag type="success" effect="plain">可解释输出</el-tag>
          </div>
        </template>

        <el-empty v-if="!answerData && !loading" description="选择问答场景后，点击“生成说明”即可查看结果。" />

        <div v-else-if="answerData" class="answer-shell">
          <div class="answer-head">
            <div>
              <h2>{{ answerData.title }}</h2>
              <p class="muted">{{ answerData.teacher_snapshot.teacher_name }} · {{ answerData.teacher_snapshot.department || '未填写院系' }}</p>
            </div>
            <el-tag type="warning" effect="plain">基于系统数据生成</el-tag>
          </div>

          <p class="answer-text">{{ answerData.answer }}</p>

          <div v-if="answerData.related_reasons?.length" class="reason-list">
            <strong>推荐依据</strong>
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
              <strong>使用边界</strong>
              <p>{{ answerData.non_coverage_note }}</p>
            </div>
            <div class="meta-item">
              <strong>当前验收说明</strong>
              <p>{{ answerData.acceptance_scope }}</p>
            </div>
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
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const answerData = ref<AssistantAnswerResponse | null>(null)
const questionType = ref<AssistantQuestionType>('portrait_summary')
const selectedGuideId = ref<number | undefined>(undefined)
const guideOptions = ref<RecommendationItem[]>([])

const currentTeacherId = computed(() => {
  if (currentUser.value?.is_admin && route.query.user_id) {
    return Number(route.query.user_id)
  }
  return currentUser.value?.id
})

const currentTeacherLabel = computed(() => {
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

const submitQuestion = async () => {
  loading.value = true
  try {
    const payload: Record<string, unknown> = {
      question_type: questionType.value,
    }

    if (currentUser.value?.is_admin && currentTeacherId.value) {
      payload.user_id = currentTeacherId.value
    }

    if (questionType.value === 'guide_reason') {
      if (!selectedGuideId.value) {
        ElMessage.warning('请选择要解读的项目指南')
        return
      }
      payload.guide_id = selectedGuideId.value
    }

    const { data } = await axios.post<AssistantAnswerResponse>('/api/ai-assistant/portrait-qa/', payload)
    answerData.value = data
  } catch (error) {
    console.error(error)
    ElMessage.error('智能问答结果生成失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

watch(questionType, async nextType => {
  if (nextType === 'guide_reason' && !guideOptions.value.length) {
    await loadGuideOptions()
  }
})

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (!currentUser.value) {
    router.replace({ name: 'login' })
    return
  }

  if (route.query.question_type && ['portrait_summary', 'achievement_summary', 'guide_reason'].includes(String(route.query.question_type))) {
    questionType.value = route.query.question_type as AssistantQuestionType
  }
  if (route.query.guide_id) {
    selectedGuideId.value = Number(route.query.guide_id)
  }
  if (questionType.value === 'guide_reason') {
    await loadGuideOptions()
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
  grid-template-columns: 0.9fr 1.1fr;
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
.reason-list ul {
  color: #64748b;
  line-height: 1.8;
}

.form-grid,
.meta-list,
.answer-shell {
  display: grid;
  gap: 16px;
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

.answer-text {
  margin: 0;
  color: #334155;
}

.reason-list ul {
  margin: 8px 0 0;
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
