<template>
  <div class="floating-assistant-shell" :style="floatingShellStyle">
    <transition name="assistant-panel-fade">
      <section v-if="panelVisible" class="assistant-panel">
        <header class="assistant-panel__header">
          <div>
            <h3>AI 助手</h3>
            <p>已接入 Dify，默认基于当前登录账号上下文问答。</p>
          </div>
          <el-button text @click="panelVisible = false">收起</el-button>
        </header>

        <div ref="messageListRef" class="assistant-panel__messages">
          <div v-if="!messages.length" class="assistant-empty">
            <p>可以直接问：本周科研重点、申报准备、成果补强建议。</p>
          </div>
          <div
            v-for="(item, index) in messages"
            :key="`${item.role}-${index}`"
            class="assistant-message"
            :class="item.role === 'user' ? 'assistant-message--user' : 'assistant-message--assistant'"
          >
            <p class="assistant-message__role">{{ item.role === 'user' ? '你' : '助手' }}</p>
            <p class="assistant-message__content">{{ item.content }}</p>
          </div>
        </div>

        <div class="assistant-panel__suggestions">
          <el-button size="small" plain @click="applyDraft('请结合我当前成果，给出本周三条可执行任务。')">本周任务</el-button>
          <el-button size="small" plain @click="applyDraft('请结合我的画像和推荐，给出一个月申报准备计划。')">申报计划</el-button>
          <el-button size="small" plain @click="applyDraft('请指出我当前成果结构的短板，并给出补强建议。')">短板补强</el-button>
        </div>

        <div class="assistant-panel__input">
          <el-input
            v-model="draft"
            type="textarea"
            :rows="3"
            maxlength="2000"
            show-word-limit
            placeholder="输入你的问题，Ctrl + Enter 发送"
            @keydown.ctrl.enter.prevent="submit"
          />
          <div class="assistant-panel__actions">
            <el-button @click="resetConversation">重置会话</el-button>
            <el-button type="primary" :loading="loading" @click="submit">发送</el-button>
          </div>
        </div>
      </section>
    </transition>

    <button
      type="button"
      class="assistant-fab"
      :class="{ 'assistant-fab--dragging': isDragging }"
      @pointerdown="handleFabPointerDown"
      @click="togglePanel"
    >
      <el-icon><ChatDotRound /></el-icon>
      <span>AI 助手</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { DifyAssistantChatResponse } from '../../types/assistant'
import { OPEN_FLOATING_ASSISTANT_EVENT, type FloatingAssistantLaunchPayload } from '../../utils/assistantLauncher'

interface MessageItem {
  role: 'user' | 'assistant'
  content: string
}

const route = useRoute()
const panelVisible = ref(false)
const loading = ref(false)
const draft = ref('')
const conversationId = ref('')
const messages = ref<MessageItem[]>([])
const contextHint = ref('')
const messageListRef = ref<HTMLElement | null>(null)
const floatingX = ref(0)
const floatingY = ref(0)
const floatingReady = ref(false)
const isDragging = ref(false)
const suppressPanelToggle = ref(false)
const pointerOffsetX = ref(0)
const pointerOffsetY = ref(0)
const dragStartX = ref(0)
const dragStartY = ref(0)
const activePointerId = ref<number | null>(null)

const FAB_WIDTH = 124
const FAB_HEIGHT = 48
const FAB_MARGIN = 16
const DRAG_THRESHOLD = 6

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const floatingShellStyle = computed(() => {
  if (!floatingReady.value) return {}
  return {
    left: `${floatingX.value}px`,
    top: `${floatingY.value}px`,
    right: 'auto',
    bottom: 'auto',
  }
})

const placeFabToDefaultCorner = () => {
  const maxX = Math.max(FAB_MARGIN, window.innerWidth - FAB_WIDTH - FAB_MARGIN)
  const maxY = Math.max(FAB_MARGIN, window.innerHeight - FAB_HEIGHT - FAB_MARGIN)
  floatingX.value = window.innerWidth - FAB_WIDTH - FAB_MARGIN
  floatingY.value = window.innerHeight - FAB_HEIGHT - FAB_MARGIN
  floatingX.value = clamp(floatingX.value, FAB_MARGIN, maxX)
  floatingY.value = clamp(floatingY.value, FAB_MARGIN, maxY)
  floatingReady.value = true
}

const clampFabPositionInViewport = () => {
  if (!floatingReady.value) return
  const maxX = Math.max(FAB_MARGIN, window.innerWidth - FAB_WIDTH - FAB_MARGIN)
  const maxY = Math.max(FAB_MARGIN, window.innerHeight - FAB_HEIGHT - FAB_MARGIN)
  floatingX.value = clamp(floatingX.value, FAB_MARGIN, maxX)
  floatingY.value = clamp(floatingY.value, FAB_MARGIN, maxY)
}

const handleFabPointerDown = (event: PointerEvent) => {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  isDragging.value = true
  suppressPanelToggle.value = false
  activePointerId.value = event.pointerId
  dragStartX.value = event.clientX
  dragStartY.value = event.clientY
  pointerOffsetX.value = event.clientX - floatingX.value
  pointerOffsetY.value = event.clientY - floatingY.value
  ;(event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId)
}

const handleWindowPointerMove = (event: PointerEvent) => {
  if (!isDragging.value || activePointerId.value !== event.pointerId) return
  const maxX = Math.max(FAB_MARGIN, window.innerWidth - FAB_WIDTH - FAB_MARGIN)
  const maxY = Math.max(FAB_MARGIN, window.innerHeight - FAB_HEIGHT - FAB_MARGIN)
  const nextX = clamp(event.clientX - pointerOffsetX.value, FAB_MARGIN, maxX)
  const nextY = clamp(event.clientY - pointerOffsetY.value, FAB_MARGIN, maxY)
  floatingX.value = nextX
  floatingY.value = nextY

  if (
    !suppressPanelToggle.value &&
    (Math.abs(event.clientX - dragStartX.value) > DRAG_THRESHOLD ||
      Math.abs(event.clientY - dragStartY.value) > DRAG_THRESHOLD)
  ) {
    suppressPanelToggle.value = true
  }
}

const endDragging = (event: PointerEvent) => {
  if (activePointerId.value !== event.pointerId) return
  isDragging.value = false
  activePointerId.value = null
}

const scrollToBottom = async () => {
  await nextTick()
  if (!messageListRef.value) return
  messageListRef.value.scrollTop = messageListRef.value.scrollHeight
}

const applyDraft = (value: string) => {
  draft.value = value
  panelVisible.value = true
}

const togglePanel = () => {
  if (suppressPanelToggle.value) {
    suppressPanelToggle.value = false
    return
  }
  panelVisible.value = !panelVisible.value
}

const resetConversation = () => {
  messages.value = []
  conversationId.value = ''
}

const submit = async () => {
  const message = draft.value.trim()
  if (!message) {
    ElMessage.warning('请输入问题后再发送。')
    return
  }

  panelVisible.value = true
  messages.value.push({ role: 'user', content: message })
  draft.value = ''
  await scrollToBottom()

  loading.value = true
  try {
    const { data } = await axios.post<DifyAssistantChatResponse>('/api/ai-assistant/dify-chat/', {
      message,
      conversation_id: conversationId.value,
      context_hint: contextHint.value || String(route.meta.moduleKey || route.name || ''),
      route_path: route.path,
    })
    conversationId.value = data.conversation_id || ''
    messages.value.push({ role: 'assistant', content: data.answer })
    if (data.status === 'fallback') {
      ElMessage.warning('当前助手为回退模式，请检查 Dify 配置。')
    }
  } catch (error) {
    console.error(error)
    messages.value.push({ role: 'assistant', content: '助手请求失败，请稍后重试。' })
    ElMessage.warning('助手请求失败，请稍后重试。')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const handleOpenEvent = async (event: Event) => {
  const customEvent = event as CustomEvent<FloatingAssistantLaunchPayload>
  const payload = customEvent.detail || {}

  panelVisible.value = true
  contextHint.value = payload.contextHint || contextHint.value
  if (payload.draft) {
    draft.value = payload.draft
  }
  if (payload.autoSend && payload.draft) {
    await submit()
  }
}

onMounted(() => {
  placeFabToDefaultCorner()
  window.addEventListener('resize', clampFabPositionInViewport)
  window.addEventListener('pointermove', handleWindowPointerMove)
  window.addEventListener('pointerup', endDragging)
  window.addEventListener('pointercancel', endDragging)
  window.addEventListener(OPEN_FLOATING_ASSISTANT_EVENT, handleOpenEvent as EventListener)
})

onUnmounted(() => {
  window.removeEventListener('resize', clampFabPositionInViewport)
  window.removeEventListener('pointermove', handleWindowPointerMove)
  window.removeEventListener('pointerup', endDragging)
  window.removeEventListener('pointercancel', endDragging)
  window.removeEventListener(OPEN_FLOATING_ASSISTANT_EVENT, handleOpenEvent as EventListener)
})
</script>

<style scoped>
.floating-assistant-shell {
  position: fixed;
  right: auto;
  bottom: auto;
  z-index: 5000;
}

.assistant-fab {
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #0f766e 0%, #2563eb 100%);
  color: #fff;
  padding: 12px 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.22);
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.assistant-fab--dragging {
  cursor: grabbing;
}

.assistant-panel {
  position: absolute;
  right: 0;
  bottom: 58px;
  width: min(420px, calc(100vw - 28px));
  max-height: min(72vh, 760px);
  border-radius: 20px;
  border: 1px solid var(--border-color-soft);
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow-strong);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  overflow: hidden;
}

.assistant-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--divider-color);
}

.assistant-panel__header h3 {
  margin: 0;
  color: var(--text-primary);
}

.assistant-panel__header p {
  margin: 4px 0 0;
  color: var(--text-tertiary);
  font-size: 12px;
  line-height: 1.5;
}

.assistant-panel__messages {
  padding: 12px 14px;
  overflow: auto;
  display: grid;
  gap: 10px;
}

.assistant-empty {
  padding: 12px;
  border-radius: 12px;
  background: var(--panel-bg);
  color: var(--text-tertiary);
  font-size: 13px;
}

.assistant-message {
  border-radius: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border-color-soft);
}

.assistant-message--user {
  background: color-mix(in srgb, var(--panel-bg) 65%, #dcfce7 35%);
}

.assistant-message--assistant {
  background: color-mix(in srgb, var(--panel-bg) 70%, #dbeafe 30%);
}

.assistant-message__role {
  margin: 0 0 4px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.assistant-message__content {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
}

.assistant-panel__suggestions {
  padding: 0 14px 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assistant-panel__input {
  padding: 0 14px 14px;
  display: grid;
  gap: 10px;
}

.assistant-panel__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.assistant-panel-fade-enter-active,
.assistant-panel-fade-leave-active {
  transition: all 0.2s ease;
}

.assistant-panel-fade-enter-from,
.assistant-panel-fade-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@media (max-width: 768px) {
  .assistant-panel {
    right: -2px;
    width: min(410px, calc(100vw - 20px));
    bottom: 56px;
  }
}
</style>
