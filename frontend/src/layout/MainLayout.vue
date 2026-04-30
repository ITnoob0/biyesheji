<template>
  <div class="main-layout">
    <aside class="main-layout__aside">
      <div class="layout-sidebar__brand" @click="navigateTo(homePath)">
        <span class="layout-sidebar__brand-mark">
          <img :src="systemLogo" alt="系统 Logo" />
        </span>
        <div class="layout-sidebar__brand-copy">
          <strong>高校教师科研画像系统</strong>
          <span>Portrait Workspace</span>
        </div>
      </div>

      <el-scrollbar class="layout-sidebar__scroll">
        <nav class="layout-sidebar__nav" aria-label="主导航">
          <section
            v-for="module in layoutModules"
            :key="module.key"
            class="layout-sidebar__group"
            :class="{
              'layout-sidebar__group--active': currentModule?.key === module.key,
              'layout-sidebar__group--expanded': expandedModuleKey === module.key,
            }"
          >
            <button
              type="button"
              class="layout-sidebar__module"
              :class="{ 'layout-sidebar__module--active': currentModule?.key === module.key }"
              @click="handleModuleToggle(module.key, module.homePath)"
            >
              <span class="layout-sidebar__module-icon">
                <el-icon v-if="module.icon"><component :is="module.icon" /></el-icon>
              </span>
              <span class="layout-sidebar__module-label">{{ module.title }}</span>
              <el-icon class="layout-sidebar__module-chevron">
                <ArrowDown />
              </el-icon>
            </button>

            <transition name="layout-sidebar-expand">
              <div
                v-if="module.children.length && expandedModuleKey === module.key"
                class="layout-sidebar__children"
              >
                <button
                  v-for="item in module.children"
                  :key="item.path"
                  type="button"
                  class="layout-sidebar__child"
                  :class="{ 'layout-sidebar__child--active': activeMenuPath === item.path }"
                  @click="handleMenuSelect(item.path)"
                >
                  <span class="layout-sidebar__child-dot"></span>
                  <span class="layout-sidebar__child-label">{{ item.title }}</span>
                </button>
              </div>
            </transition>
          </section>
        </nav>
      </el-scrollbar>

      <div class="layout-sidebar__footer">
        <span class="layout-sidebar__footer-tag">{{ roleLabel }}</span>
        <span class="layout-sidebar__footer-text">
          {{ currentModule?.description || '当前页面已进入模块化工作台视图。' }}
        </span>
      </div>
    </aside>

    <div class="main-layout__workspace">
      <header class="main-layout__header">
        <div class="layout-context">
          <p class="layout-context__eyebrow">{{ currentModule?.title || '工作台' }}</p>
          <div class="layout-context__headline">
            <h1>{{ currentPageTitle }}</h1>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item v-for="item in breadcrumbItems" :key="item">{{ item }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>

        <div class="layout-toolbar">
          <button
            ref="themeToggleRef"
            type="button"
            class="layout-toolbar__ghost layout-toolbar__ghost--theme"
            :aria-label="themeButtonLabel"
            @click="toggleTheme"
          >
            <el-icon><component :is="themeIcon" /></el-icon>
            <span>{{ themeButtonLabel }}</span>
          </button>
          <el-dropdown
            trigger="click"
            placement="bottom-end"
            popper-class="layout-notification-dropdown"
            @visible-change="handleNotificationDropdownVisible"
          >
            <button type="button" class="layout-toolbar__icon" aria-label="消息通知">
              <el-badge :value="notificationUnreadCount" :hidden="notificationUnreadCount <= 0" :max="99">
                <el-icon><Bell /></el-icon>
              </el-badge>
            </button>
            <template #dropdown>
              <div class="layout-notification-menu">
                <div class="layout-notification-menu__head">
                  <strong>消息通知</strong>
                  <el-button
                    link
                    type="primary"
                    :disabled="notificationUnreadCount <= 0"
                    @click.stop="markAllNotificationsRead"
                  >
                    全部已读
                  </el-button>
                </div>
                <div v-loading="notificationLoading" class="layout-notification-menu__body">
                  <el-empty v-if="!notifications.length" description="暂无消息" :image-size="56" />
                  <button
                    v-for="item in notifications"
                    :key="item.id"
                    type="button"
                    class="layout-notification-menu__item"
                    :class="{ 'layout-notification-menu__item--unread': !item.is_read }"
                    @click="handleNotificationClick(item)"
                  >
                    <div class="layout-notification-menu__item-head">
                      <strong>{{ item.title }}</strong>
                      <span>{{ formatNotificationTime(item.created_at) }}</span>
                    </div>
                    <p>{{ item.content }}</p>
                    <div class="layout-notification-menu__item-meta">
                      <el-tag size="small" effect="plain">{{ item.category_label }}</el-tag>
                      <el-tag v-if="isLegacyAchievementClaimNotification(item)" size="small" type="warning" effect="plain">
                        历史协作
                      </el-tag>
                      <el-tag v-if="!item.is_read" size="small" type="danger" effect="plain">未读</el-tag>
                      <span v-if="item.sender_name">来自：{{ item.sender_name }}</span>
                    </div>
                  </button>
                </div>
              </div>
            </template>
          </el-dropdown>

          <el-dropdown trigger="click" placement="bottom-end" popper-class="layout-profile-dropdown">
            <button type="button" class="layout-profile">
              <span class="layout-profile__avatar-shell">
                <span v-if="currentUser?.avatar_url" class="layout-profile__avatar layout-profile__avatar--image">
                  <img :src="currentUser.avatar_url" :alt="displayName" />
                </span>
                <span v-else class="layout-profile__avatar">{{ profileInitial }}</span>
                <span class="layout-profile__status"></span>
              </span>
            </button>

            <template #dropdown>
              <div class="layout-profile-menu">
                <div class="layout-profile-menu__summary">
                  <span class="layout-profile-menu__avatar-shell">
                    <span
                      v-if="currentUser?.avatar_url"
                      class="layout-profile-menu__avatar layout-profile-menu__avatar--image"
                    >
                      <img :src="currentUser.avatar_url" :alt="displayName" />
                    </span>
                    <span v-else class="layout-profile-menu__avatar">{{ profileInitial }}</span>
                    <span class="layout-profile-menu__status"></span>
                  </span>
                  <div class="layout-profile-menu__copy">
                    <div class="layout-profile-menu__headline">
                      <strong>{{ displayName }}</strong>
                      <span class="layout-profile-menu__badge">{{ profileBadge }}</span>
                    </div>
                    <span class="layout-profile-menu__subline">{{ profileSecondaryLine }}</span>
                  </div>
                </div>

                <div class="layout-profile-menu__section">
                  <button type="button" class="layout-profile-menu__action" @click="handleHeaderCommand('logout')">
                    <span class="layout-profile-menu__action-main">
                      <el-icon><SwitchButton /></el-icon>
                      <span>退出登录</span>
                    </span>
                    <span class="layout-profile-menu__action-shortcut"></span>
                  </button>
                </div>
              </div>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="main-layout__main">
        <div class="main-layout__scroll">
          <router-view v-slot="{ Component }">
            <div class="main-layout__page-view">
              <component :is="Component" />
            </div>
          </router-view>
        </div>
      </main>
    </div>

    <FloatingDifyAssistant v-if="currentUser" />
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ArrowDown, Bell, Moon, Sunny, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import type { UserNotificationListResponse, UserNotificationRecord } from '../types/users'
import { resolveApiErrorMessage } from '../utils/apiFeedback.js'
import {
  consumeSessionNotice,
  getSessionUser,
  logoutSession,
  SESSION_AUTH_CHANGED_EVENT,
  type SessionUser,
} from '../utils/sessionAuth'
import { resolveRoleLabel } from '../utils/authPresentation.js'
import { resolveWorkspaceHomePath } from '../utils/workspaceNavigation.js'
import {
  applyWorkspaceTheme,
  getStoredWorkspaceTheme,
  setWorkspaceThemeToggleOrigin,
  transitionWorkspaceTheme,
  type WorkspaceTheme,
} from '../utils/workspaceTheme'
import { workspaceChildrenRoutes } from '../router/workspaceRoutes'
import { buildLayoutModules, findCurrentModule } from './layoutMenu'
import FloatingDifyAssistant from '../components/assistant/FloatingDifyAssistant.vue'
import systemLogo from '../../logo2.png'

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(getSessionUser())
const workspaceTheme = ref<WorkspaceTheme>(getStoredWorkspaceTheme())
const expandedModuleKey = ref<string | null>(null)
const themeToggleRef = ref<HTMLButtonElement | null>(null)
const notifications = ref<UserNotificationRecord[]>([])
const notificationUnreadCount = ref(0)
const notificationLoading = ref(false)
let notificationPollTimer: number | null = null

const refreshCurrentUser = () => {
  currentUser.value = getSessionUser()
}

const flushSessionNotice = () => {
  const notice = consumeSessionNotice()
  if (notice) {
    ElMessage.warning(notice)
  }
}

const layoutModules = computed(() => buildLayoutModules(workspaceChildrenRoutes, currentUser.value))
const currentModule = computed(() =>
  findCurrentModule(layoutModules.value, String(route.meta.moduleKey || ''), route.path),
)
const homePath = computed(() => resolveWorkspaceHomePath(currentUser.value))

const activeMenuPath = computed(() => {
  const routeActiveMenu = typeof route.meta.activeMenu === 'string' ? route.meta.activeMenu : ''
  return routeActiveMenu || route.path
})

const currentPageTitle = computed(() => String(route.meta.title || currentModule.value?.title || '工作台'))

const breadcrumbItems = computed(() => {
  const items = [currentModule.value?.title || '工作台']
  if (currentPageTitle.value && currentPageTitle.value !== items[0]) {
    items.push(currentPageTitle.value)
  }
  return items
})

const displayName = computed(() => {
  const user = currentUser.value
  if (!user) return ''
  return user.real_name || user.username
})

const profileInitial = computed(() => {
  const name = displayName.value.trim()
  return name ? name.charAt(0).toUpperCase() : 'U'
})

const roleLabel = computed(() => resolveRoleLabel(currentUser.value))
const profileBadge = computed(() => {
  if (currentUser.value?.role_code === 'admin') {
    return 'System Admin'
  }
  if (currentUser.value?.role_code === 'college_admin') {
    return 'College Admin'
  }
  return 'Teacher'
})
const profileSecondaryLine = computed(() => {
  const user = currentUser.value
  if (!user) {
    return ''
  }

  return user.email || user.username || user.department || '当前登录账户'
})
const themeButtonLabel = computed(() => (workspaceTheme.value === 'dark' ? '切换浅色' : '切换深色'))
const themeIcon = computed(() => (workspaceTheme.value === 'dark' ? Sunny : Moon))

const navigateTo = (path: string) => {
  if (route.path !== path) {
    router.push(path)
  }
}

const handleModuleToggle = (moduleKey: string, homePath: string) => {
  if (expandedModuleKey.value === moduleKey) {
    expandedModuleKey.value = null
    return
  }

  expandedModuleKey.value = moduleKey

  if (currentModule.value?.key !== moduleKey) {
    navigateTo(homePath)
  }
}

const handleMenuSelect = (path: string) => {
  navigateTo(path)
}

const toggleTheme = async () => {
  const buttonRect = themeToggleRef.value?.getBoundingClientRect()
  if (buttonRect) {
    setWorkspaceThemeToggleOrigin({
      x: buttonRect.left + buttonRect.width / 2,
      y: buttonRect.top + buttonRect.height / 2,
    })
  }

  const nextTheme: WorkspaceTheme = workspaceTheme.value === 'dark' ? 'light' : 'dark'
  workspaceTheme.value = await transitionWorkspaceTheme(nextTheme)
}

const normalizeActionQuery = (raw: Record<string, any> | null | undefined): Record<string, string> => {
  if (!raw || typeof raw !== 'object') {
    return {}
  }
  return Object.entries(raw).reduce<Record<string, string>>((acc, [key, value]) => {
    if (value === undefined || value === null || value === '') {
      return acc
    }
    acc[key] = String(value)
    return acc
  }, {})
}

const CLAIM_NOTIFICATION_CATEGORIES = new Set(['ACHIEVEMENT_CLAIM', 'CLAIM_REMINDER'])

const isLegacyAchievementClaimNotification = (item: UserNotificationRecord): boolean =>
  CLAIM_NOTIFICATION_CATEGORIES.has(item.category) || (item.action_path || '').includes('achievement-claims')

const resolveAchievementClaimFallbackPath = (): string => {
  if (currentUser.value?.role_code === 'college_admin') {
    return '/teachers/achievement-review'
  }
  if (currentUser.value?.role_code === 'admin') {
    return '/academy-dashboard'
  }
  return '/dashboard/representative-achievements'
}

const loadNotifications = async ({ silent = false }: { silent?: boolean } = {}) => {
  if (!currentUser.value) {
    notifications.value = []
    notificationUnreadCount.value = 0
    return
  }
  if (!silent) {
    notificationLoading.value = true
  }
  try {
    const { data } = await axios.get<UserNotificationListResponse>('/api/users/notifications/', { params: { limit: 20 } })
    notifications.value = data.records || []
    notificationUnreadCount.value = Number(data.unread_count || 0)
  } catch (error: any) {
    if (!silent) {
      ElMessage.warning(resolveApiErrorMessage(error, '消息通知加载失败'))
    }
  } finally {
    if (!silent) {
      notificationLoading.value = false
    }
  }
}

const markNotificationRead = async (notificationId: number) => {
  await axios.post(`/api/users/notifications/${notificationId}/read/`, {})
  const target = notifications.value.find(item => item.id === notificationId)
  if (target) {
    target.is_read = true
  }
  notificationUnreadCount.value = Math.max(
    notifications.value.filter(item => !item.is_read).length,
    0,
  )
}

const markAllNotificationsRead = async () => {
  if (!notifications.value.length) return
  await axios.post('/api/users/notifications/read-all/', {})
  notifications.value = notifications.value.map(item => ({
    ...item,
    is_read: true,
  }))
  notificationUnreadCount.value = 0
  ElMessage.success('已将消息全部标记为已读')
}

const handleNotificationClick = async (item: UserNotificationRecord) => {
  try {
    if (!item.is_read) {
      await markNotificationRead(item.id)
    }
  } catch (error: any) {
    ElMessage.warning(resolveApiErrorMessage(error, '消息已读状态更新失败'))
  }

  if (isLegacyAchievementClaimNotification(item)) {
    ElMessage.info('成果认领属于历史论文合著协作通知；当前规则化成果请通过成果录入与学院审核处理。')
    await router.push(resolveAchievementClaimFallbackPath())
    return
  }
  if (!item.action_path) {
    return
  }
  const query = normalizeActionQuery(item.action_query)
  await router.push({
    path: item.action_path,
    query,
  })
}

const handleNotificationDropdownVisible = (visible: boolean) => {
  if (visible) {
    void loadNotifications()
  }
}

const formatNotificationTime = (raw: string) => {
  if (!raw) return ''
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) {
    return raw
  }
  return parsed.toLocaleString()
}

const handleHeaderCommand = async (command: string) => {
  if (command === 'logout') {
    await logoutSession(router)
    currentUser.value = null
    ElMessage.success('已退出登录')
    return
  }

  navigateTo(command)
}

watch(
  () => route.fullPath,
  () => {
    refreshCurrentUser()
    if (currentModule.value?.key && currentModule.value.key !== expandedModuleKey.value) {
      expandedModuleKey.value = currentModule.value.key
    }
    flushSessionNotice()
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener(SESSION_AUTH_CHANGED_EVENT, refreshCurrentUser)
  workspaceTheme.value = applyWorkspaceTheme(workspaceTheme.value)
  if (currentModule.value?.key) {
    expandedModuleKey.value = currentModule.value.key
  }
  flushSessionNotice()
  void loadNotifications()
  notificationPollTimer = window.setInterval(() => {
    void loadNotifications({ silent: true })
  }, 45000)
})

onUnmounted(() => {
  window.removeEventListener(SESSION_AUTH_CHANGED_EVENT, refreshCurrentUser)
  if (notificationPollTimer !== null) {
    window.clearInterval(notificationPollTimer)
    notificationPollTimer = null
  }
})
</script>

<style scoped>
.main-layout {
  display: grid;
  grid-template-columns: 284px minmax(0, 1fr);
  height: 100vh;
  width: 100%;
  overflow: hidden;
  background: var(--app-bg);
  transition: background 0.24s ease;
}

.main-layout__aside {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-width: 0;
  background: var(--workspace-sidebar-bg);
  border-right: 1px solid var(--workspace-sidebar-border);
  transition:
    background 0.24s ease,
    border-color 0.24s ease;
}

.layout-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 20px 16px;
  cursor: pointer;
}

.layout-sidebar__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  overflow: hidden;
}

.layout-sidebar__brand-mark img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 14px;
}

.layout-sidebar__brand-copy {
  display: grid;
  gap: 2px;
}

.layout-sidebar__brand-copy strong {
  color: var(--workspace-title);
  font-size: 15px;
  font-weight: 700;
}

.layout-sidebar__brand-copy span {
  color: var(--workspace-sidebar-brand-subtitle);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.layout-sidebar__scroll {
  min-height: 0;
  padding: 0 12px 14px;
}

.layout-sidebar__nav {
  display: grid;
  gap: 6px;
}

.layout-sidebar__group {
  display: grid;
  gap: 4px;
}

.layout-sidebar__module,
.layout-sidebar__child {
  all: unset;
  box-sizing: border-box;
  cursor: pointer;
}

.layout-sidebar__module {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 12px;
  border-radius: 14px;
  color: var(--workspace-sidebar-text);
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.layout-sidebar__module:hover {
  background: var(--workspace-sidebar-hover);
  color: var(--workspace-sidebar-text-strong);
}

.layout-sidebar__module--active {
  background: var(--workspace-sidebar-active);
  color: var(--workspace-sidebar-text-strong);
}

.layout-sidebar__module-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: currentColor;
}

.layout-sidebar__module-label {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.5;
}

.layout-sidebar__module-chevron {
  justify-self: end;
  font-size: 14px;
  transition: transform 0.18s ease;
}

.layout-sidebar__group--expanded .layout-sidebar__module-chevron {
  transform: rotate(180deg);
}

.layout-sidebar__children {
  display: grid;
  gap: 4px;
  padding: 0 0 8px 14px;
}

.layout-sidebar__child {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 12px;
  color: var(--workspace-sidebar-text);
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.layout-sidebar__child:hover {
  background: var(--workspace-sidebar-hover);
  color: var(--workspace-sidebar-text-strong);
  transform: translateX(2px);
}

.layout-sidebar__child--active {
  background: var(--workspace-sidebar-child-active);
  color: var(--workspace-sidebar-text-strong);
}

.layout-sidebar__child-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.9);
  transition: background 0.18s ease, transform 0.18s ease;
}

.layout-sidebar__child--active .layout-sidebar__child-dot {
  background: #60a5fa;
  transform: scale(1.1);
}

.layout-sidebar__child-label {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
}

.layout-sidebar__footer {
  display: grid;
  gap: 10px;
  padding: 16px 20px 20px;
  border-top: 1px solid var(--workspace-sidebar-border);
  background: var(--workspace-sidebar-footer-bg);
}

.layout-sidebar__footer-tag {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.12);
  color: #86efac;
  font-size: 12px;
  font-weight: 700;
}

.layout-sidebar__footer-text {
  color: var(--workspace-sidebar-footnote);
  font-size: 12px;
  line-height: 1.7;
}

.main-layout__workspace {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
}

.main-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 28px;
  border-bottom: 1px solid var(--divider-color);
  background: color-mix(in srgb, var(--workspace-surface) 86%, transparent);
  backdrop-filter: blur(20px);
  transition:
    background 0.24s ease,
    border-color 0.24s ease;
}

.layout-context {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.layout-context__eyebrow {
  margin: 0;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.layout-context__headline {
  display: grid;
  gap: 6px;
}

.layout-context__headline h1 {
  margin: 0;
  color: var(--workspace-title);
  font-size: 28px;
}

.layout-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.layout-toolbar__ghost,
.layout-toolbar__icon,
.layout-profile {
  border: 0;
  background: transparent;
}

.layout-toolbar__ghost {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 16px;
  background: var(--workspace-toolbar-surface);
  color: var(--workspace-muted);
  cursor: pointer;
  transition:
    background 0.24s ease,
    color 0.24s ease,
    transform 0.18s ease;
}

.layout-toolbar__ghost:hover,
.layout-toolbar__icon:hover {
  transform: translateY(-1px);
}

.layout-toolbar__ghost--theme {
  min-width: 120px;
  justify-content: center;
}

.layout-toolbar__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: var(--workspace-toolbar-surface);
  color: var(--workspace-muted);
  cursor: pointer;
  transition:
    background 0.24s ease,
    color 0.24s ease,
    transform 0.18s ease;
}

.layout-profile {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 20px;
  background: var(--workspace-toolbar-surface);
  cursor: pointer;
  box-shadow: inset 0 0 0 1px var(--border-color-soft);
  transition:
    background 0.24s ease,
    box-shadow 0.24s ease;
}

.layout-profile__avatar-shell {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.layout-profile__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: linear-gradient(135deg, #fb7185 0%, #f9a8d4 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
}

.layout-profile__avatar--image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.layout-profile__status {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: #4ade80;
  border: 2px solid var(--workspace-surface);
}

.main-layout__main {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.main-layout__scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 36px;
  box-sizing: border-box;
}

.main-layout__page-view {
  min-height: 100%;
  padding-bottom: 40px;
}

.layout-sidebar-expand-enter-active,
.layout-sidebar-expand-leave-active {
  transition:
    max-height 0.26s ease,
    opacity 0.22s ease,
    transform 0.22s ease,
    padding 0.22s ease;
  overflow: hidden;
}

.layout-sidebar-expand-enter-from,
.layout-sidebar-expand-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-6px);
  padding-top: 0;
  padding-bottom: 0;
}

.layout-sidebar-expand-enter-to,
.layout-sidebar-expand-leave-from {
  max-height: 320px;
  opacity: 1;
  transform: translateY(0);
}

:deep(.layout-profile-dropdown) {
  padding: 0 !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 18px !important;
  background: var(--workspace-surface) !important;
  box-shadow: var(--workspace-shadow-strong) !important;
  overflow: hidden;
}

:deep(.layout-profile-dropdown .el-popper__arrow::before) {
  background: var(--workspace-surface) !important;
  border-color: var(--border-color) !important;
}

:deep(.layout-notification-dropdown) {
  padding: 0 !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
  background: var(--workspace-surface) !important;
  box-shadow: var(--workspace-shadow-strong) !important;
  overflow: hidden;
}

:deep(.layout-notification-dropdown .el-popper__arrow::before) {
  background: var(--workspace-surface) !important;
  border-color: var(--border-color) !important;
}

.layout-notification-menu {
  width: 360px;
  background: var(--workspace-surface);
}

.layout-notification-menu__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid var(--divider-color);
}

.layout-notification-menu__head strong {
  color: var(--workspace-title);
  font-size: 14px;
}

.layout-notification-menu__body {
  max-height: 440px;
  overflow-y: auto;
  padding: 8px;
  display: grid;
  gap: 8px;
}

.layout-notification-menu__item {
  all: unset;
  box-sizing: border-box;
  cursor: pointer;
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
  transition: background 0.18s ease, border-color 0.18s ease;
}

.layout-notification-menu__item:hover {
  background: var(--menu-hover-bg);
}

.layout-notification-menu__item--unread {
  border-color: color-mix(in srgb, #2563eb 32%, var(--border-color-soft));
}

.layout-notification-menu__item-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}

.layout-notification-menu__item-head strong {
  color: var(--workspace-title);
  font-size: 13px;
}

.layout-notification-menu__item-head span,
.layout-notification-menu__item p,
.layout-notification-menu__item-meta {
  color: var(--workspace-muted);
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
}

.layout-notification-menu__item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.layout-profile-menu {
  width: 298px;
  background: var(--workspace-surface);
}

.layout-profile-menu__summary {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 18px 16px;
}

.layout-profile-menu__avatar-shell {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.layout-profile-menu__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  border-radius: 18px;
  background: linear-gradient(135deg, #fb7185 0%, #f9a8d4 100%);
  color: #ffffff;
  font-size: 18px;
  font-weight: 800;
  overflow: hidden;
}

.layout-profile-menu__avatar--image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.layout-profile-menu__status {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 14px;
  height: 14px;
  border-radius: 999px;
  background: #4ade80;
  border: 2px solid var(--workspace-surface);
}

.layout-profile-menu__copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.layout-profile-menu__headline {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.layout-profile-menu__headline strong {
  color: var(--workspace-title);
  font-size: 16px;
  font-weight: 700;
}

.layout-profile-menu__badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
  font-size: 12px;
  font-weight: 700;
}

.layout-profile-menu__subline {
  color: var(--workspace-muted);
  font-size: 14px;
  line-height: 1.5;
  word-break: break-all;
}

.layout-profile-menu__section {
  border-top: 1px solid var(--divider-color);
}

.layout-profile-menu__action {
  all: unset;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 58px;
  padding: 0 18px;
  cursor: pointer;
  color: var(--workspace-title);
  transition: background 0.18s ease;
}

.layout-profile-menu__action:hover {
  background: var(--menu-hover-bg);
}

.layout-profile-menu__action-main {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  font-weight: 500;
}

.layout-profile-menu__action-shortcut {
  color: var(--workspace-muted);
  font-size: 13px;
}

@media (max-width: 1280px) {
  .main-layout {
    grid-template-columns: 264px minmax(0, 1fr);
  }
}

@media (max-width: 960px) {
  .main-layout {
    grid-template-columns: 1fr;
  }

  .main-layout__aside {
    display: none;
  }

  .main-layout__header {
    flex-direction: column;
    align-items: stretch;
  }

  .layout-toolbar {
    justify-content: space-between;
  }

  .layout-toolbar__ghost {
    flex: 1;
    justify-content: center;
  }
}

@media (max-width: 640px) {
  .layout-toolbar {
    flex-wrap: wrap;
  }

  .layout-profile {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
