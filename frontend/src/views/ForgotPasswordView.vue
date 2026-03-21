<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { resolveApiErrorMessage } from '../utils/authPresentation.js'

interface ForgotPasswordFormState {
  employee_id: string
  real_name: string
  new_password: string
  confirm_password: string
}

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive<ForgotPasswordFormState>({
  employee_id: '',
  real_name: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules<ForgotPasswordFormState> = {
  employee_id: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirm_password: [{ required: true, message: '请再次输入新密码', trigger: 'blur' }],
}

const handleResetPassword = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    await axios.post('/api/users/forgot-password/', form)
    ElMessage.success('密码已重置，请使用工号和新密码重新登录。')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '密码重置失败，请检查工号和姓名。'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="forgot-page">
    <div class="forgot-card">
      <div class="topbar">
        <div>
          <p class="eyebrow">Password Recovery</p>
          <h1>忘记密码</h1>
          <p class="description">请输入工号和真实姓名完成身份校验，然后设置新的登录密码。</p>
        </div>
        <el-button @click="router.push('/login')">返回登录</el-button>
      </div>

      <el-alert
        title="教师账号可通过工号和真实姓名自助重置密码；管理员账号请联系系统负责人处理。"
        type="info"
        :closable="false"
        show-icon
      />

      <el-alert
        title="如果密码曾被管理员初始化或重置，建议通过安全渠道确认身份后再告知教师处理结果。"
        type="warning"
        :closable="false"
        show-icon
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="grid two-cols">
          <el-form-item label="工号" prop="employee_id">
            <el-input v-model="form.employee_id" placeholder="例如 100001" />
          </el-form-item>
          <el-form-item label="真实姓名" prop="real_name">
            <el-input v-model="form.real_name" placeholder="请输入注册时填写的真实姓名" />
          </el-form-item>
        </div>

        <div class="grid two-cols">
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="form.new_password" type="password" show-password placeholder="请设置新密码" />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input
              v-model="form.confirm_password"
              type="password"
              show-password
              placeholder="请再次输入新密码"
              @keyup.enter="handleResetPassword"
            />
          </el-form-item>
        </div>

        <div class="actions">
          <el-button type="primary" :loading="loading" @click="handleResetPassword">重置密码</el-button>
          <el-button @click="router.push('/register')">去注册教师账号</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.forgot-page {
  min-height: 100vh;
  padding: 24px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.16), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.18), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.forgot-card {
  width: min(760px, 100%);
  display: grid;
  gap: 20px;
  padding: 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #2563eb;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-size: 12px;
}

h1 {
  margin: 0;
  color: #0f172a;
}

.description {
  margin: 8px 0 0;
  color: #64748b;
}

.grid {
  display: grid;
  gap: 16px;
}

.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 768px) {
  .forgot-page {
    padding: 16px;
  }

  .forgot-card {
    padding: 24px;
  }

  .topbar,
  .two-cols,
  .actions {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
