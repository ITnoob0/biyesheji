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

const handleLogin = async () => {
  clearSessionAuth()

  try {
    const res = await axios.post('/api/token/', {
      username: username.value,
      password: password.value,
    })

    setSessionToken(res.data.access)
    await fetchCurrentSessionUser()

    const redirectTarget =
      typeof route.query.redirect === 'string' && route.query.redirect !== '/login'
        ? route.query.redirect
        : '/dashboard'

    router.push(redirectTarget)
  } catch {
    clearSessionAuth()
    ElMessage.error('登录失败，请检查用户名和密码')
  }
}
</script>

<template>
  <div class="login-container">
    <el-input v-model="username" placeholder="用户名" />
    <el-input v-model="password" type="password" placeholder="密码" />
    <el-button @click="handleLogin">登录</el-button>
  </div>
</template>
