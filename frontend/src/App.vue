<template>
  <div class="app-shell" :class="{ 'app-shell--with-header': showAuthBar }">
    <header v-if="showAuthBar" class="workspace-header">
      <div class="workspace-header__inner">
        <button type="button" class="workspace-brand" @click="goTo(homePath)">
          <span class="workspace-brand__mark">
            <img class="workspace-brand__image" :src="appLogo" alt="系统 Logo" />
          </span>
          <span class="workspace-brand__text">高校教师科研画像与智能辅助系统</span>
        </button>

        <nav class="workspace-nav" aria-label="主导航">
          <button
            v-for="item in primaryNavItems"
            :key="item.path"
            type="button"
            class="workspace-nav__item"
            :class="{ 'workspace-nav__item--active': isCurrentRoute(item.path) }"
            @click="goTo(item.path)"
          >
            <el-icon class="workspace-nav__icon">
              <component :is="item.icon" />
            </el-icon>
            <span>{{ item.label }}</span>
          </button>
        </nav>

        <div class="workspace-header__actions">
          <el-dropdown
            trigger="click"
            placement="bottom-end"
            popper-class="workspace-profile-dropdown"
            :popper-style="{ width: `${profileMenuWidth}px` }"
            @command="handleHeaderCommand"
          >
            <button ref="profileTriggerRef" type="button" class="workspace-profile">
              <span class="workspace-profile__avatar">{{ profileInitial }}</span>
              <span class="workspace-profile__content">
                <span class="workspace-profile__role">{{ roleLabel }}</span>
                <span class="workspace-profile__name">{{ displayName }}</span>
              </span>
              <el-icon class="workspace-profile__chevron">
                <ArrowDown />
              </el-icon>
            </button>

            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="item in roleMenuItems"
                  :key="item.command"
                  :command="item.command"
                >
                  {{ item.label }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <main class="app-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  ChatDotRound,
  DataAnalysis,
  Document,
  Histogram,
  MagicStick,
  Odometer,
  Reading,
  User,
} from '@element-plus/icons-vue'
import {
  consumeSessionNotice,
  getSessionUser,
  logoutSession,
  SESSION_AUTH_CHANGED_EVENT,
  type SessionUser,
} from './utils/sessionAuth'
import { resolveRoleLabel } from './utils/authPresentation.js'
import { resolveWorkspaceHomePath } from './utils/workspaceNavigation.js'
import appLogo from '../logo.webp'

type PrimaryNavItem = {
  label: string
  path: string
  icon: Component
}

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(getSessionUser())
const profileTriggerRef = ref<HTMLElement | null>(null)
const profileMenuWidth = ref(220)
let profileResizeObserver: ResizeObserver | null = null

const refreshCurrentUser = () => {
  currentUser.value = getSessionUser()
}

const flushSessionNotice = () => {
  const notice = consumeSessionNotice()
  if (notice) {
    ElMessage.warning(notice)
  }
}

const syncProfileMenuWidth = () => {
  const width = profileTriggerRef.value?.offsetWidth
  if (width) {
    profileMenuWidth.value = width
  }
}

watch(
  () => route.fullPath,
  refreshCurrentUser,
  { immediate: true },
)

onMounted(() => {
  window.addEventListener(SESSION_AUTH_CHANGED_EVENT, refreshCurrentUser)
  window.addEventListener('resize', syncProfileMenuWidth)
  flushSessionNotice()

  nextTick(() => {
    syncProfileMenuWidth()

    if (typeof ResizeObserver !== 'undefined' && profileTriggerRef.value) {
      profileResizeObserver = new ResizeObserver(syncProfileMenuWidth)
      profileResizeObserver.observe(profileTriggerRef.value)
    }
  })
})

onUnmounted(() => {
  window.removeEventListener(SESSION_AUTH_CHANGED_EVENT, refreshCurrentUser)
  window.removeEventListener('resize', syncProfileMenuWidth)
  profileResizeObserver?.disconnect()
  profileResizeObserver = null
})

const showAuthBar = computed(() => {
  const hiddenRoutes = new Set(['login', 'teacher-register', 'forgot-password'])
  return !hiddenRoutes.has(String(route.name || '')) && Boolean(currentUser.value)
})

const homePath = computed(() => resolveWorkspaceHomePath(currentUser.value))

const primaryNavItems = computed<PrimaryNavItem[]>(() => {
  if (currentUser.value?.is_admin) {
    return [
      { label: '画像主页', path: '/dashboard', icon: Odometer },
      { label: '教师管理', path: '/teachers', icon: User },
      { label: '学院看板', path: '/academy-dashboard', icon: DataAnalysis },
      { label: '项目指南', path: '/project-guides', icon: Reading },
      { label: '推荐结果', path: '/project-recommendations', icon: MagicStick },
      { label: '智能问答', path: '/assistant-demo', icon: ChatDotRound },
      { label: '个人中心', path: '/profile-editor', icon: Document },
    ]
  }

  return [
    { label: '个人中心', path: '/profile-editor', icon: Document },
    { label: '画像主页', path: '/dashboard', icon: Odometer },
    { label: '成果管理', path: '/entry', icon: Histogram },
    { label: '智能问答', path: '/assistant-demo', icon: ChatDotRound },
    { label: '推荐结果', path: '/project-recommendations', icon: MagicStick },
  ]
})

const displayName = computed(() => {
  const user = currentUser.value
  if (!user) return ''
  return user.real_name || user.username
})

watch(displayName, () => {
  nextTick(syncProfileMenuWidth)
})

watch(
  () => route.fullPath,
  () => {
    flushSessionNotice()
  },
)

const profileInitial = computed(() => {
  const name = displayName.value.trim()
  return name ? name.charAt(0).toUpperCase() : 'U'
})

const roleLabel = computed(() => resolveRoleLabel(currentUser.value))

const roleMenuItems = computed(() => {
  if (!currentUser.value?.is_admin) {
    return []
  }

  return [
    { label: '教师管理', command: 'teachers' },
    { label: '项目指南', command: 'project-guides' },
    { label: '学院看板', command: 'academy-dashboard' },
  ]
})

const goTo = (path: string) => {
  if (route.path !== path) {
    router.push(path)
  }
}

const isCurrentRoute = (path: string) => route.path === path

const handleHeaderCommand = async (command: string) => {
  if (command === 'logout') {
    await handleLogout()
    return
  }

  const routeMap: Record<string, string> = {
    teachers: '/teachers',
    'project-guides': '/project-guides',
    'academy-dashboard': '/academy-dashboard',
  }

  const targetPath = routeMap[command]
  if (targetPath) {
    goTo(targetPath)
  }
}

const handleLogout = async () => {
  await logoutSession(router)
  currentUser.value = null
  ElMessage.success('已退出登录')
}
</script>

<style>
html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
}

body {
  color: #0f172a;
}

#app,
.app-shell {
  min-height: 100vh;
}

.app-shell--with-header {
  padding-top: 92px;
}

.workspace-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1200;
  background:
    radial-gradient(circle at top left, rgba(120, 164, 255, 0.16), transparent 34%),
    radial-gradient(circle at top right, rgba(146, 171, 219, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(18, 32, 67, 0.985), rgba(22, 39, 78, 0.965));
  border-bottom: 1px solid rgba(214, 224, 243, 0.1);
  box-shadow: 0 12px 38px rgba(7, 16, 36, 0.28);
  backdrop-filter: blur(18px);
}

.workspace-header__inner {
  display: grid;
  grid-template-columns: 220px 1fr auto;
  align-items: center;
  gap: 28px;
  max-width: 1520px;
  min-height: 92px;
  margin: 0 auto;
  padding: 0 32px;
}

.workspace-brand {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  border: 0;
  padding: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
  justify-self: start;
}

.workspace-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: transparent;
  border: 0;
  box-shadow: none;
  overflow: hidden;
  flex-shrink: 0;
}

.workspace-brand__image {
  width: 52px;
  height: 52px;
  object-fit: cover;
  display: block;
  border-radius: 50%;
}

.workspace-brand__text {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(236, 241, 250, 0.92);
}

.workspace-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  min-width: 0;
}

.workspace-nav__item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 16px;
  padding: 14px 18px;
  background: transparent;
  color: rgba(231, 237, 247, 0.9);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  cursor: pointer;
  appearance: none;
  transition:
    background-color 0.22s ease,
    color 0.22s ease,
    box-shadow 0.22s ease,
    transform 0.22s ease;
}

.workspace-nav__item:hover {
  color: #ffffff;
  background: rgba(201, 218, 246, 0.08);
  transform: translateY(-1px);
}

.workspace-nav__item--active {
  color: #f8fbff;
  background: linear-gradient(180deg, rgba(92, 142, 228, 0.34), rgba(78, 122, 198, 0.2));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.12),
    0 10px 26px rgba(38, 72, 140, 0.24);
}

.workspace-nav__icon {
  font-size: 18px;
  color: rgba(214, 224, 243, 0.92);
}

.workspace-header__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.workspace-profile {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  border: 0;
  border-radius: 20px;
  padding: 12px 16px 12px 12px;
  background: linear-gradient(180deg, rgba(213, 224, 244, 0.08), rgba(155, 177, 219, 0.04));
  color: #f7faff;
  cursor: pointer;
  appearance: none;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 8px 20px rgba(7, 11, 24, 0.24);
  transition:
    background-color 0.22s ease,
    box-shadow 0.22s ease,
    transform 0.22s ease;
}

.workspace-profile:hover {
  background: linear-gradient(180deg, rgba(220, 230, 247, 0.12), rgba(164, 186, 226, 0.06));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 12px 24px rgba(19, 30, 56, 0.28);
  transform: translateY(-1px);
}

.workspace-profile__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(145deg, rgba(124, 168, 240, 0.98), rgba(73, 112, 192, 0.96));
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
  box-shadow: 0 10px 18px rgba(54, 103, 204, 0.24);
}

.workspace-profile__content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
}

.workspace-profile__role {
  font-size: 14px;
  font-weight: 700;
  color: #f5f8ff;
}

.workspace-profile__name {
  font-size: 12px;
  color: rgba(214, 223, 239, 0.74);
}

.workspace-profile__chevron {
  font-size: 14px;
  color: rgba(214, 223, 239, 0.72);
}

.app-content {
  min-height: 100vh;
}

.workspace-profile-dropdown.el-popper {
  border: 1px solid rgba(184, 202, 236, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at top left, rgba(120, 164, 255, 0.14), transparent 42%),
    linear-gradient(180deg, rgba(18, 32, 67, 0.985), rgba(22, 39, 78, 0.97));
  box-shadow: 0 18px 40px rgba(7, 16, 36, 0.38);
  backdrop-filter: blur(18px);
}

.workspace-profile-dropdown .el-popper__arrow::before {
  border: 1px solid rgba(184, 202, 236, 0.16);
  background: rgba(20, 36, 71, 0.98);
}

.workspace-profile-dropdown .el-dropdown-menu {
  padding: 8px;
  background: transparent;
}

.workspace-profile-dropdown .el-dropdown-menu__item {
  border-radius: 12px;
  color: rgba(236, 241, 250, 0.92);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  padding: 12px 14px;
}

.workspace-profile-dropdown .el-dropdown-menu__item:not(.is-disabled):hover {
  background: rgba(92, 142, 228, 0.2);
  color: #ffffff;
}

.workspace-profile-dropdown .el-dropdown-menu__item--divided {
  border-top-color: rgba(184, 202, 236, 0.14);
}

@media (max-width: 1260px) {
  .workspace-header__inner {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 16px 20px;
  }

  .workspace-brand,
  .workspace-header__actions {
    justify-self: stretch;
  }

  .workspace-nav {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 6px;
    scrollbar-width: thin;
  }

  .workspace-header__actions {
    justify-content: flex-end;
  }

  .app-shell--with-header {
    padding-top: 152px;
  }
}

@media (max-width: 720px) {
  .workspace-header__inner {
    padding: 14px 16px;
    min-height: 84px;
  }

  .workspace-brand__text {
    font-size: 12px;
    letter-spacing: 0.12em;
  }

  .workspace-nav {
    gap: 12px;
  }

  .workspace-nav__item {
    padding: 12px 14px;
    font-size: 14px;
  }

  .workspace-profile {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
