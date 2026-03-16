<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const username = ref('')
const password = ref('')
const router = useRouter()

const handleLogin = async () => {
  try {
    // 调用后端在 core/urls.py 定义的 api/token/ 接口
    const res = await axios.post('/api/token/', {
      username: username.value,
      password: password.value
    })
    // 关键：将获取到的 access 令牌保存到 LocalStorage
    localStorage.setItem('token', res.data.access)

    // 获取当前用户信息（假设有/api/users/me/接口返回{id, is_admin, ...}）
    const userRes = await axios.get('/api/users/me/', {
      headers: { Authorization: 'Bearer ' + res.data.access }
    })
    localStorage.setItem('user_id', userRes.data.id)
    localStorage.setItem('is_admin', userRes.data.is_admin ? 'true' : 'false')

    // 登录成功后跳转到首页
    router.push('/')
  } catch (err) {
    alert('登录失败，请检查用户名密码')
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