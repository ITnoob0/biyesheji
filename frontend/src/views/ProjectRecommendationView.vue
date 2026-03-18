<template>
  <div class="recommendation-page">
    <section class="hero-panel">
      <div>
        <p class="eyebrow">Guide Recommendation</p>
        <h1>项目指南推荐</h1>
        <p class="hero-text">
          面向
          <strong>{{ recommendationData?.teacher_snapshot.teacher_name || currentUser?.real_name || currentUser?.username || '当前教师' }}</strong>
          的轻量推荐结果，强调可解释规则，不依赖 RAG 或复杂模型。
        </p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button plain @click="openAssistantDemo">问答说明</el-button>
        <el-button type="primary" :loading="loading" @click="loadRecommendations">刷新推荐</el-button>
      </div>
    </section>

    <section class="content-shell control-shell">
      <el-card shadow="never">
        <template #header>
          <div class="section-head">
            <span>推荐筛选与排序</span>
            <el-tag type="success" effect="plain">第三轮展示增强</el-tag>
          </div>
        </template>

        <div class="control-grid">
          <el-select
            v-if="currentUser?.is_admin"
            v-model="selectedTeacherId"
            clearable
            filterable
            placeholder="管理员可切换教师视角"
            @change="handleTeacherChanged"
          >
            <el-option
              v-for="teacher in teacherOptions"
              :key="teacher.id"
              :label="`${teacher.real_name || teacher.username}（${teacher.department || '未填写院系'}）`"
              :value="teacher.id"
            />
          </el-select>

          <el-input
            v-model="searchKeyword"
            clearable
            placeholder="按指南标题 / 发布单位 / 摘要搜索"
          />

          <el-select v-model="selectedFocusTag" clearable placeholder="按推荐类型筛选">
            <el-option v-for="tag in focusTagOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>

          <el-select v-model="selectedSort" placeholder="排序方式">
            <el-option v-for="item in sortOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </div>

        <div class="tag-list">
          <el-tag type="info" effect="plain">{{ recommendationData?.data_meta.current_strategy || '规则增强型推荐' }}</el-tag>
          <el-tag type="warning" effect="plain">{{ recommendationData?.data_meta.sorting_note || '默认按推荐分数排序' }}</el-tag>
          <el-tag type="success" effect="plain">结果数 {{ recommendationItems.length }}</el-tag>
        </div>
      </el-card>
    </section>

    <section class="snapshot-grid content-shell">
      <el-card shadow="never">
        <template #header>
          <div class="section-head">
            <span>教师画像摘要</span>
            <el-tag type="primary" effect="plain">推荐输入</el-tag>
          </div>
        </template>
        <div class="snapshot-block">
          <strong>研究标签</strong>
          <div class="tag-list">
            <el-tag v-for="tag in recommendationData?.teacher_snapshot.keywords || []" :key="tag" effect="plain">{{ tag }}</el-tag>
            <span v-if="!(recommendationData?.teacher_snapshot.keywords || []).length" class="muted">暂无研究标签，可先完善教师档案或论文关键词。</span>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>学科/院系</strong>
          <div class="tag-list">
            <el-tag v-for="tag in recommendationData?.teacher_snapshot.disciplines || []" :key="tag" type="success" effect="plain">{{ tag }}</el-tag>
            <span v-if="!(recommendationData?.teacher_snapshot.disciplines || []).length" class="muted">暂无学科信息。</span>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>近三年成果活跃度</strong>
          <p class="muted">{{ recommendationData?.teacher_snapshot.recent_activity_count ?? 0 }} 项</p>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="section-head">
            <span>推荐说明</span>
            <el-tag type="warning" effect="plain">可解释规则</el-tag>
          </div>
        </template>
        <div class="meta-list">
          <div class="meta-item">
            <strong>规则来源</strong>
            <p>{{ recommendationData?.data_meta.source_note || '基于研究方向、关键词、学科与活跃度的轻量推荐。' }}</p>
          </div>
          <div class="meta-item">
            <strong>当前阶段说明</strong>
            <p>{{ recommendationData?.data_meta.acceptance_scope || '本能力属于当前阶段扩展方向。' }}</p>
          </div>
          <div class="meta-item">
            <strong>后续扩展接口预留</strong>
            <p>{{ recommendationData?.data_meta.future_extension_hint || '后续可在本接口基础上扩展智能推荐能力。' }}</p>
          </div>
          <div class="meta-item">
            <strong>当前路线说明</strong>
            <p>{{ recommendationData?.data_meta.current_strategy || '当前仍以规则增强路线为主，未进入复杂模型推荐。' }}</p>
          </div>
        </div>
      </el-card>
    </section>

    <div v-if="!loading && !recommendationItems.length" class="content-shell empty-shell">
      <el-empty :description="recommendationData?.empty_state || '当前暂无匹配的项目指南推荐。'" />
    </div>

    <section v-else class="recommendation-list content-shell">
      <el-card v-for="item in recommendationItems" :key="item.id" class="recommendation-card" shadow="hover">
        <div class="recommendation-head">
          <div>
            <div class="title-row">
              <h2>{{ item.title }}</h2>
              <div class="tag-list compact-row">
                <el-tag type="success" effect="plain">匹配度 {{ item.recommendation_score }}</el-tag>
                <el-tag type="primary" effect="plain">{{ item.priority_label }}</el-tag>
              </div>
            </div>
            <p class="subline">
              {{ item.issuing_agency }} · {{ item.guide_level_display }} · {{ item.status_display }}
              <span v-if="item.application_deadline"> · 截止 {{ item.application_deadline }}</span>
            </p>
          </div>
          <div class="compact-row">
            <el-button link type="success" @click="openAssistantDemo(item.id)">智能解读</el-button>
            <el-button v-if="item.source_url" link type="primary" @click="openGuide(item.source_url)">查看来源</el-button>
          </div>
        </div>

        <p class="summary">{{ item.summary }}</p>

        <div class="tag-section">
          <span class="tag-label">推荐概括</span>
          <p class="summary">{{ item.recommendation_summary }}</p>
        </div>

        <div class="tag-section">
          <span class="tag-label">推荐类型</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.match_category_tags" :key="tag" type="primary" effect="plain">{{ tag }}</el-tag>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">主题关键词</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.target_keywords" :key="tag" effect="plain">{{ tag }}</el-tag>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">推荐理由</span>
          <ul class="reason-list">
            <li v-for="reason in item.recommendation_reasons" :key="reason">{{ reason }}</li>
          </ul>
        </div>

        <div class="tag-section">
          <span class="tag-label">匹配命中</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.matched_keywords" :key="`kw-${tag}`" type="warning" effect="plain">{{ tag }}</el-tag>
            <el-tag v-for="tag in item.matched_disciplines" :key="`dis-${tag}`" type="success" effect="plain">{{ tag }}</el-tag>
            <span v-if="!item.matched_keywords.length && !item.matched_disciplines.length" class="muted">当前推荐更多基于成果活跃度与申报窗口判断。</span>
          </div>
        </div>

        <div class="footer-line">
          <span v-if="item.support_amount">资助强度：{{ item.support_amount }}</span>
          <span v-if="item.eligibility_notes">申报要求：{{ item.eligibility_notes }}</span>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type { TeacherAccountResponse } from '../types/users'
import { buildRecommendationSortOptions, filterRecommendationItems, sortRecommendationItems } from './project-guides/recommendationHelpers.js'
import type { RecommendationItem, RecommendationResponse } from './project-guides/types'

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const recommendationData = ref<RecommendationResponse | null>(null)
const teacherOptions = ref<TeacherAccountResponse[]>([])
const selectedTeacherId = ref<number | undefined>(undefined)
const searchKeyword = ref('')
const selectedFocusTag = ref('')
const selectedSort = ref('score')

const sortOptions = buildRecommendationSortOptions()

const focusTagOptions = computed(() => {
  const tags = new Set<string>()
  ;(recommendationData.value?.recommendations || []).forEach(item => {
    ;(item.match_category_tags || []).forEach(tag => tags.add(tag))
  })
  return [...tags]
})

const recommendationItems = computed<RecommendationItem[]>(() => {
  const filtered = filterRecommendationItems(
    recommendationData.value?.recommendations || [],
    searchKeyword.value,
    selectedFocusTag.value,
  )
  return sortRecommendationItems(filtered, selectedSort.value)
})

const loadTeacherOptions = async () => {
  if (!currentUser.value?.is_admin) return

  const { data } = await axios.get<TeacherAccountResponse[]>('/api/users/teachers/')
  teacherOptions.value = data || []
}

const loadRecommendations = async () => {
  loading.value = true
  try {
    const params =
      currentUser.value?.is_admin && (selectedTeacherId.value || route.query.user_id)
        ? { user_id: Number(selectedTeacherId.value || route.query.user_id) }
        : undefined

    const { data } = await axios.get<RecommendationResponse>('/api/project-guides/recommendations/', { params })
    recommendationData.value = data
  } catch (error) {
    console.error(error)
    ElMessage.error('项目指南推荐加载失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

const openGuide = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

const handleTeacherChanged = async () => {
  await loadRecommendations()
}

const openAssistantDemo = (guideId?: number) => {
  const query: Record<string, string> = {}

  const targetTeacherId = selectedTeacherId.value || Number(route.query.user_id) || currentUser.value?.id
  if (targetTeacherId) {
    query.user_id = String(targetTeacherId)
  }
  if (guideId) {
    query.guide_id = String(guideId)
    query.question_type = 'guide_reason'
  }

  router.push({
    name: 'assistant-demo',
    query,
  })
}

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (currentUser.value?.is_admin && route.query.user_id) {
    selectedTeacherId.value = Number(route.query.user_id)
  }
  await loadTeacherOptions()
  await loadRecommendations()
})
</script>

<style scoped>
.recommendation-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.12), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.1), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.hero-panel {
  max-width: 1180px;
  margin: 0 auto 22px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 28px 32px;
  border-radius: 26px;
  background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 62%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.14);
}

.snapshot-grid :deep(.el-card),
.recommendation-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.hero-actions,
.section-head,
.recommendation-head,
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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

h1 {
  color: #fff;
}

h2 {
  color: #16362c;
}

.hero-text {
  margin: 12px 0 0;
  max-width: 720px;
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.8;
}

.subline,
.summary,
.muted,
.meta-item p,
.footer-line,
.reason-list {
  color: #557068;
  line-height: 1.7;
}

.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.control-shell {
  margin-bottom: 20px;
}

.control-shell :deep(.el-card) {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.snapshot-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 20px;
}

.empty-shell {
  padding: 32px 0 8px;
}

.snapshot-block + .snapshot-block {
  margin-top: 18px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.meta-list {
  display: grid;
  gap: 14px;
}

.meta-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f7faf9;
}

.meta-item strong {
  display: block;
  margin-bottom: 8px;
  color: #16362c;
}

.recommendation-list {
  display: grid;
  gap: 18px;
  margin-top: 20px;
}

.recommendation-card :deep(.el-card__body) {
  display: grid;
  gap: 14px;
}

.subline,
.summary,
.footer-line,
.reason-list {
  margin: 0;
}

.tag-section {
  display: grid;
  gap: 8px;
}

.tag-label {
  font-weight: 600;
  color: #16362c;
}

.reason-list {
  padding-left: 18px;
}

.footer-line {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}

.compact-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 1080px) {
  .control-grid,
  .snapshot-grid,
  .hero-panel,
  .hero-actions,
  .recommendation-head,
  .title-row {
    grid-template-columns: 1fr;
    display: grid;
  }
}

@media (max-width: 768px) {
  .recommendation-page {
    padding: 16px;
  }
}
</style>
