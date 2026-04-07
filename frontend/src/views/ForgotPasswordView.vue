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
  department: string
}

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive<ForgotPasswordFormState>({
  employee_id: '',
  real_name: '',
  department: '',
})

const rules: FormRules<ForgotPasswordFormState> = {
  employee_id: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属学院', trigger: 'blur' }],
}

const handleResetPassword = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    await axios.post('/api/users/forgot-password/', form)
    ElMessage.success('申请已提交，学院管理员将处理你的密码重置请求。')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '申请提交失败，请检查工号、姓名和所属学院。'))
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
          <p class="description">请输入工号、姓名和所属学院，向本学院管理员提交密码重置申请。</p>
        </div>
        <el-button @click="router.push('/login')">返回登录</el-button>
      </div>

      <el-alert
        title="系统不再支持自助找回密码，申请提交后将由本学院管理员审核并重置。"
        type="info"
        :closable="false"
        show-icon
      />

      <el-alert
        title="管理员账号请联系系统管理员处理密码问题，本入口仅用于教师账号重置申请。"
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
            <el-input v-model="form.real_name" placeholder="请输入姓名" />
          </el-form-item>
        </div>
        <el-form-item label="所属学院" prop="department">
          <el-input v-model="form.department" placeholder="例如 计算机学院" @keyup.enter="handleResetPassword" />
        </el-form-item>

        <div class="actions">
          <el-button type="primary" :loading="loading" @click="handleResetPassword">提交重置申请</el-button>
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
