<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { TokenObtainPairResponse } from '../types/auth'
import { resolvePostLoginRedirect } from '../utils/sessionFlow.js'
import { buildPasswordSecurityNotice, resolveLoginFailureMessage } from '../utils/authPresentation.js'
import {
  clearSessionAuth,
  consumeAuthRedirectTarget,
  consumeSessionExpiredReason,
  fetchCurrentSessionUser,
  setSessionToken,
} from '../utils/sessionAuth'

const username = ref('')
const password = ref('')
const route = useRoute()
const router = useRouter()
const loading = ref(false)

const redirectHint = computed(() =>
  typeof route.query.redirect === 'string' && route.query.redirect.trim()
    ? '登录成功后将回到你刚才访问的受保护页面。'
    : '',
)

const handleLogin = async () => {
  clearSessionAuth()
  loading.value = true

  try {
    const response = await axios.post<TokenObtainPairResponse>('/api/token/', {
      username: username.value.trim(),
      password: password.value,
    })

    setSessionToken(response.data.access, response.data.refresh)
    const sessionUser = await fetchCurrentSessionUser()

    if (sessionUser.password_reset_required) {
      ElMessage.warning(buildPasswordSecurityNotice(sessionUser))
    }

    const redirectTarget = resolvePostLoginRedirect(
      typeof route.query.redirect === 'string' ? route.query.redirect : '',
      consumeAuthRedirectTarget(),
    )

    router.push(redirectTarget)
    ElMessage.success('登录成功')
  } catch (error: any) {
    clearSessionAuth()
    ElMessage.error(resolveLoginFailureMessage(error))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const expiredReason = consumeSessionExpiredReason()
  if (expiredReason) {
    ElMessage.warning(expiredReason)
  }
})
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <p class="eyebrow">Teacher Research Profile</p>
      <h1>登录系统</h1>
      <p class="description">
        管理员继续使用 <code>admin</code> 登录，教师继续使用 6 位工号作为登录用户名。
      </p>

      <el-alert
        v-if="redirectHint"
        :title="redirectHint"
        type="info"
        :closable="false"
        show-icon
      />

      <el-alert
        title="若密码由管理员初始化或重置，登录后请尽快在“基础档案”页修改密码。"
        type="warning"
        :closable="false"
        show-icon
      />

      <el-input v-model="username" placeholder="工号 / 管理员账号" size="large" />
      <el-input
        v-model="password"
        type="password"
        placeholder="密码"
        size="large"
        show-password
        @keyup.enter="handleLogin"
      />

      <el-button type="primary" size="large" :loading="loading" @click="handleLogin">登录</el-button>

      <div class="secondary-actions">
        <el-button size="large" @click="router.push('/register')">教师注册</el-button>
        <el-button size="large" @click="router.push('/forgot-password')">忘记密码</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(31, 111, 235, 0.18), transparent 28%),
    radial-gradient(circle at bottom right, rgba(15, 118, 110, 0.18), transparent 26%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
}

.login-card {
  width: min(420px, 100%);
  display: grid;
  gap: 16px;
  padding: 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
}

.eyebrow {
  margin: 0;
  color: #2563eb;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 12px;
}

h1 {
  margin: 0;
  color: #0f172a;
}

.description {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
}

.secondary-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
</style>
