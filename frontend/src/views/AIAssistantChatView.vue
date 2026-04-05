<template>
  <div class="assistant-chat-page workspace-page">
    <section class="hero-shell workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">AI Copilot</p>
        <h1 class="workspace-hero__title">知识增强 AI 助手</h1>
        <p class="subtitle workspace-hero__text">
          当前助手采用“系统内知识检索 + 可选大模型生成 + 安全回退”链路，管理员与教师都仅面向当前登录账号问答。
        </p>
      </div>
      <div class="hero-actions workspace-page-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button plain @click="applySuggestedPrompt('portrait_summary')">快速提问</el-button>
      </div>
    </section>

    <section v-if="linkContext" class="content-shell link-context-shell">
      <el-alert
        :title="linkContextTitle"
        type="info"
        :description="linkContextDescription"
        :closable="false"
        show-icon
      />
    </section>

    <section class="content-shell chat-shell">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>对话窗口</span>
            <el-tag type="success" effect="plain">RAG Chat</el-tag>
          </div>
        </template>

        <div ref="messageContainerRef" class="message-list">
          <div v-if="!messages.length" class="workspace-empty-state">
            <el-empty description="输入你的问题，助手会基于系统内证据给出回答。" />
          </div>

          <div
            v-for="(item, index) in messages"
            :key="`${item.role}-${index}`"
            class="message-item"
            :class="item.role === 'user' ? 'message-item--user' : 'message-item--assistant'"
          >
            <p class="message-role">{{ item.role === 'user' ? '你' : '助手' }}</p>
            <p class="message-content">{{ item.content }}</p>

            <div v-if="item.role === 'assistant' && item.payload" class="message-meta">
              <div class="tag-list">
                <el-tag :type="item.payload.status === 'ok' ? 'success' : 'warning'" effect="plain">
                  {{ item.payload.status === 'ok' ? '已生成回答' : '已回退' }}
                </el-tag>
                <el-tag type="info" effect="plain">模型 {{ item.payload.model }}</el-tag>
                <el-tag type="primary" effect="plain">{{ currentTeacherLabel }}</el-tag>
              </div>

              <div v-if="item.payload.sources.length" class="source-list">
                <div
                  v-for="source in item.payload.sources"
                  :key="`${item.payload.question}-${source.id}`"
                  class="source-item"
                >
                  <div class="source-head">
                    <strong>{{ source.title }}</strong>
                    <el-tag size="small" effect="plain">{{ source.id }} · 相关度 {{ source.score }}</el-tag>
                  </div>
                  <p>{{ source.snippet }}</p>
                  <el-button v-if="source.link" link type="primary" @click="openEvidenceLink(source.link)">
                    {{ source.link.label }}
                  </el-button>
                </div>
              </div>

              <div class="meta-list">
                <div class="meta-item">
                  <strong>答案边界</strong>
                  <p>{{ item.payload.non_coverage_note }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="suggested-row">
          <el-button size="small" plain @click="applySuggestedPrompt('portrait_summary')">画像优势与短板</el-button>
          <el-button size="small" plain @click="applySuggestedPrompt('achievement_summary')">成果结构解读</el-button>
          <el-button size="small" plain @click="applySuggestedPrompt('guide_overview')">推荐策略建议</el-button>
        </div>

        <div class="input-row">
          <el-input
            v-model="draftMessage"
            type="textarea"
            :rows="3"
            maxlength="1200"
            show-word-limit
            placeholder="例如：结合我的成果和当前推荐，给我一个本月可执行的申报准备建议。"
            @keydown.ctrl.enter.prevent="submitMessage"
          />
          <div class="input-actions">
            <el-button @click="clearConversation">清空对话</el-button>
            <el-button type="primary" :loading="loading" @click="submitMessage">发送问题</el-button>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { AssistantChatResponse, AssistantEvidenceLink, AssistantQuestionType } from '../types/assistant'
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import { parseCrossModuleLink, resolveAssistantEvidenceRoute } from '../utils/crossModuleLinking'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  payload?: AssistantChatResponse
}

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const draftMessage = ref('')
const messages = ref<ChatMessage[]>([])
const messageContainerRef = ref<HTMLElement | null>(null)
const linkContext = computed(() => parseCrossModuleLink(route.query))

const currentTeacherLabel = computed(() => currentUser.value?.real_name || currentUser.value?.username || '当前账号')

const linkContextTitle = computed(() => {
  if (linkContext.value?.source === 'recommendation') return '来自推荐模块的问答联动'
  if (linkContext.value?.source === 'portrait') return '来自画像模块的问答联动'
  if (linkContext.value?.source === 'achievement') return '来自成果模块的问答联动'
  return '问答联动入口'
})

const linkContextDescription = computed(
  () => linkContext.value?.note || '当前助手会保持证据回跳能力，回答中的来源卡片可直接返回对应业务页面核验。',
)

const questionPromptMap: Record<AssistantQuestionType, string> = {
  portrait_summary: '请总结我当前教师画像的优势、短板以及建议。',
  portrait_dimension_reason: '请解释我当前画像维度是如何形成的。',
  portrait_data_governance: '请说明我当前画像的数据口径、缺口和改进建议。',
  achievement_summary: '请总结我近三年的成果结构，并给出提升重点。',
  achievement_portrait_link: '请说明成果如何支撑我的画像分布。',
  achievement_recommendation_link: '请说明成果如何支撑当前推荐项目。',
  guide_reason: '请解释当前推荐项目的核心命中原因。',
  guide_overview: '请总结当前推荐策略与可执行建议。',
  graph_status: '请说明当前图谱链路状态和可解释边界。',
  academy_summary: '请给出学院统计概览与建议。',
}

const scrollToBottom = async () => {
  await nextTick()
  const container = messageContainerRef.value
  if (!container) return
  container.scrollTop = container.scrollHeight
}

const applySuggestedPrompt = (type: AssistantQuestionType) => {
  draftMessage.value = questionPromptMap[type]
}

const submitMessage = async () => {
  const message = draftMessage.value.trim()
  if (!message) {
    ElMessage.warning('请输入问题后再发送。')
    return
  }

  messages.value.push({ role: 'user', content: message })
  draftMessage.value = ''
  await scrollToBottom()

  loading.value = true
  try {
    const { data } = await axios.post<AssistantChatResponse>('/api/ai-assistant/chat/', {
      message,
      context_hint: linkContext.value?.source || '',
      limit: 4,
    })
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      payload: data,
    })
  } catch (error) {
    console.error(error)
    const notice = buildApiErrorNotice(error, {
      fallbackMessage: '助手响应失败，请稍后重试。',
      fallbackGuidance: '你仍可回到画像、成果或推荐页面继续核验。',
    })
    messages.value.push({
      role: 'assistant',
      content: `${notice.message} ${notice.requestHint || ''}`.trim(),
    })
    ElMessage.warning(notice.message)
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const openEvidenceLink = (link: AssistantEvidenceLink) => {
  router.push(resolveAssistantEvidenceRoute(link, currentUser.value, currentUser.value?.id))
}

const clearConversation = () => {
  messages.value = []
}

const applyRouteQueryContext = async (autoSubmit = false) => {
  const routeQuestionType = route.query.question_type as AssistantQuestionType | undefined
  if (routeQuestionType && questionPromptMap[routeQuestionType]) {
    draftMessage.value = questionPromptMap[routeQuestionType]
    if (routeQuestionType === 'guide_reason' && route.query.guide_id) {
      draftMessage.value = `${draftMessage.value} 请重点解释指南 ID ${route.query.guide_id}。`
    }
    if (autoSubmit) {
      await submitMessage()
    }
  }
}

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
    if (!currentUser.value) return
    await applyRouteQueryContext(true)
  },
)
</script>

<style scoped>
.assistant-chat-page {
  min-height: 100%;
  padding: 24px;
  background: var(--page-bg);
  color: var(--text-secondary);
}

.hero-shell,
.chat-shell {
  max-width: 1180px;
  margin: 0 auto 20px;
}

.hero-shell {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 28px 32px;
  border-radius: 26px;
  background: var(--hero-bg);
  color: var(--text-on-brand);
  box-shadow: var(--workspace-shadow-strong);
}

.hero-actions,
.section-head,
.source-head,
.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow {
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.subtitle {
  margin: 10px 0 0;
  max-width: 700px;
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.7;
}

.link-context-shell {
  max-width: 1180px;
  margin: 0 auto 20px;
}

.chat-shell :deep(.el-card) {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.message-list {
  display: grid;
  gap: 14px;
  max-height: 56vh;
  overflow: auto;
  padding-right: 4px;
}

.message-item {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
}

.message-item--user {
  background: color-mix(in srgb, var(--panel-bg) 70%, #dcfce7 30%);
}

.message-item--assistant {
  background: color-mix(in srgb, var(--panel-bg) 78%, #dbeafe 22%);
}

.message-role {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.message-content {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.7;
}

.message-meta {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}

.source-list {
  display: grid;
  gap: 10px;
}

.source-item {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color-soft);
  background: var(--card-bg);
}

.source-item p {
  margin: 8px 0 0;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.meta-list {
  display: grid;
  gap: 10px;
}

.meta-item {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color-soft);
  background: var(--card-bg);
}

.meta-item strong {
  display: block;
  margin-bottom: 6px;
}

.meta-item p {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.suggested-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.input-row {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}

@media (max-width: 900px) {
  .hero-shell {
    flex-direction: column;
  }
}
</style>
