<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearSessionAuth, fetchCurrentSessionUser, setSessionToken } from '../utils/sessionAuth'

const username = ref('')
const password = ref('')
const route = useRoute()
const router = useRouter()
const loading = ref(false)

const handleLogin = async () => {
  clearSessionAuth()
  loading.value = true

  try {
    const response = await axios.post('/api/token/', {
      username: username.value.trim(),
      password: password.value,
    })

    setSessionToken(response.data.access)
    await fetchCurrentSessionUser()

    const redirectTarget =
      typeof route.query.redirect === 'string' && route.query.redirect !== '/login'
        ? route.query.redirect
        : '/dashboard'

    router.push(redirectTarget)
    ElMessage.success('登录成功')
  } catch {
    clearSessionAuth()
    ElMessage.error('登录失败，请检查工号和密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <p class="eyebrow">Teacher Research Profile</p>
      <h1>登录系统</h1>
      <p class="description">
        管理员使用 `admin` 登录，教师请使用 6 位工号作为登录用户名。
      </p>

      <el-input v-model="username" placeholder="工号 / 用户名" size="large" />
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
