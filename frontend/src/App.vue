<template>
  <div class="app-shell">
    <header v-if="showAuthBar" class="session-bar">
      <div class="session-meta">
        <span class="session-name">{{ displayName }}</span>
        <span class="session-id">工号 {{ currentUser?.id }}</span>
      </div>

      <div class="session-actions">
        <el-button text @click="router.push('/dashboard')">画像主页</el-button>
        <el-button text @click="router.push('/profile-editor')">基础档案</el-button>
        <el-button
          v-if="currentUser?.is_admin"
          text
          @click="router.push('/teachers')"
        >
          教师管理
        </el-button>
        <el-button type="danger" plain @click="handleLogout">退出登录</el-button>
      </div>
    </header>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getSessionUser,
  logoutSession,
  SESSION_AUTH_CHANGED_EVENT,
  type SessionUser,
} from './utils/sessionAuth'

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(getSessionUser())

const refreshCurrentUser = () => {
  currentUser.value = getSessionUser()
}

watch(
  () => route.fullPath,
  refreshCurrentUser,
  { immediate: true },
)

onMounted(() => {
  window.addEventListener(SESSION_AUTH_CHANGED_EVENT, refreshCurrentUser)
})

onUnmounted(() => {
  window.removeEventListener(SESSION_AUTH_CHANGED_EVENT, refreshCurrentUser)
})

const showAuthBar = computed(() => {
  const hiddenRoutes = new Set(['login', 'teacher-register', 'forgot-password'])
  return !hiddenRoutes.has(String(route.name || '')) && Boolean(currentUser.value)
})

const displayName = computed(() => {
  const user = currentUser.value
  if (!user) return ''
  return user.real_name || user.username
})

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
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  background-color: #f5f7fa;
}

body {
  color: #0f172a;
}

#app,
.app-shell {
  min-height: 100vh;
}

.session-bar {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1200;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(16px);
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.session-name {
  font-weight: 600;
}

.session-id {
  color: #64748b;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 768px) {
  .session-bar {
    left: 12px;
    right: 12px;
    top: 12px;
    justify-content: space-between;
    border-radius: 20px;
  }

  .session-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .session-actions {
    gap: 4px;
  }
}
</style>
