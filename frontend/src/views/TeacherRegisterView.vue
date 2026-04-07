<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <p class="eyebrow">Account Governance</p>
      <h1>自助注册已关闭</h1>
      <p class="description">
        当前系统不再开放教师自助注册。教师账号请联系本学院管理员统一创建，学院管理员账号请联系系统管理员创建。
      </p>

      <el-alert
        title="如忘记密码，请返回登录页使用“忘记密码”提交重置申请。"
        type="info"
        :closable="false"
        show-icon
      />

      <div class="actions">
        <el-button type="primary" @click="router.push('/login')">返回登录</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  padding: 24px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.16), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.18), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.register-card {
  width: min(680px, 100%);
  display: grid;
  gap: 18px;
  padding: 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
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
  line-height: 1.75;
}

.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
