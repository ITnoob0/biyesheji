<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { resolveApiErrorMessage } from '../utils/authPresentation.js'

type ResetVia = 'phone' | 'email'

interface ForgotPasswordCodeResponse {
  detail: string
  employee_id: string
  reset_via: ResetVia
  ttl_seconds: number
  contact_masked: string
  delivery_hint: string
}

interface ForgotPasswordResetResponse {
  detail: string
  security_notice: string
}

interface ForgotPasswordFormState {
  employee_id: string
  reset_via: ResetVia
  verification_code: string
  new_password: string
  confirm_password: string
}

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const sendingCode = ref(false)
const lastCodePayload = ref<ForgotPasswordCodeResponse | null>(null)

const form = reactive<ForgotPasswordFormState>({
  employee_id: '',
  reset_via: 'phone',
  verification_code: '',
  new_password: '',
  confirm_password: '',
})

const phoneOrEmailLabel = computed(() => (form.reset_via === 'phone' ? '手机号验证码' : '邮箱验证码'))
const contactHint = computed(() =>
  form.reset_via === 'phone'
    ? '系统会校验该账号已绑定手机号，并仅在页面展示脱敏手机号。'
    : '系统会校验该账号已绑定个人邮箱，并仅在页面展示脱敏邮箱。',
)

const rules: FormRules<ForgotPasswordFormState> = {
  employee_id: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  reset_via: [{ required: true, message: '请选择找回方式', trigger: 'change' }],
  verification_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirm_password: [{ required: true, message: '请再次输入新密码', trigger: 'blur' }],
}

const sendCode = async () => {
  const employeeId = form.employee_id.trim()
  if (!employeeId) {
    ElMessage.warning('请先输入工号')
    return
  }

  sendingCode.value = true
  try {
    const { data } = await axios.post<ForgotPasswordCodeResponse>('/api/users/forgot-password/code/', {
      employee_id: employeeId,
      reset_via: form.reset_via,
    })
    lastCodePayload.value = data
    form.verification_code = ''
    ElMessage.success(data.detail || '验证码已生成')
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '验证码获取失败'))
  } finally {
    sendingCode.value = false
  }
}

const handleResetPassword = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const { data } = await axios.post<ForgotPasswordResetResponse>('/api/users/forgot-password/reset/', {
      employee_id: form.employee_id.trim(),
      reset_via: form.reset_via,
      verification_code: form.verification_code.trim(),
      new_password: form.new_password,
      confirm_password: form.confirm_password,
    })
    ElMessage.success(data.detail || '密码已重置成功')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '密码重置失败'))
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
          <p class="description">教师可通过“工号 + 手机验证码”或“工号 + 邮箱验证码”重置密码。</p>
        </div>
        <el-button @click="router.push('/login')">返回登录</el-button>
      </div>

      <el-alert
        title="当前为本地验证码模式，系统会把 6 位验证码输出到后端运行终端，前端不会显示验证码。"
        type="info"
        :closable="false"
        show-icon
      />

      <el-alert
        title="管理员账号不支持在这里自助找回密码。教师如不便自助重置，也可以私下联系管理员代为重置。"
        type="warning"
        :closable="false"
        show-icon
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="grid two-cols">
          <el-form-item label="工号" prop="employee_id" required>
            <el-input v-model="form.employee_id" maxlength="6" placeholder="例如 100001" />
          </el-form-item>
          <el-form-item label="找回方式" prop="reset_via" required>
            <el-radio-group v-model="form.reset_via">
              <el-radio-button label="phone">手机号验证码</el-radio-button>
              <el-radio-button label="email">邮箱验证码</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>

        <el-alert :title="contactHint" type="success" :closable="false" show-icon />

        <div class="grid code-row">
          <el-form-item :label="phoneOrEmailLabel" prop="verification_code" required>
            <el-input v-model="form.verification_code" maxlength="6" placeholder="请输入 6 位验证码" @keyup.enter="handleResetPassword" />
          </el-form-item>
          <el-form-item label="获取验证码">
            <el-button type="primary" plain :loading="sendingCode" @click="sendCode">生成验证码</el-button>
          </el-form-item>
        </div>

        <el-alert
          v-if="lastCodePayload"
          title="验证码已生成"
          :description="`${lastCodePayload.delivery_hint} 绑定信息：${lastCodePayload.contact_masked}，${lastCodePayload.ttl_seconds} 秒内有效。`"
          type="success"
          :closable="false"
          show-icon
        />

        <div class="grid two-cols">
          <el-form-item label="新密码" prop="new_password" required>
            <el-input v-model="form.new_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password" required>
            <el-input v-model="form.confirm_password" type="password" show-password @keyup.enter="handleResetPassword" />
          </el-form-item>
        </div>

        <div class="actions">
          <el-button type="primary" :loading="loading" @click="handleResetPassword">重置密码</el-button>
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

.two-cols,
.code-row {
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
  .code-row,
  .actions {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
