<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { PasswordChangeResponse } from '../../types/users'
import {
  buildAccountLifecycleHint,
  buildPasswordSecurityNotice,
  formatPasswordUpdatedAt,
  resolveApiErrorMessage,
  resolveRoleLabel,
} from '../../utils/authPresentation.js'
import { setSessionUser, type SessionUser } from '../../utils/sessionAuth'

interface PasswordFormState {
  current_password: string
  new_password: string
  confirm_password: string
}

const props = defineProps<{
  currentUser: SessionUser | null
}>()

const emit = defineEmits<{
  changed: [user: SessionUser]
}>()

const formRef = ref<FormInstance>()
const loading = ref(false)
const passwordForm = reactive<PasswordFormState>({
  current_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules<PasswordFormState> = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirm_password: [{ required: true, message: '请再次输入新密码', trigger: 'blur' }],
}

const securityNotice = computed(() => buildPasswordSecurityNotice(props.currentUser))
const lifecycleHint = computed(() => buildAccountLifecycleHint(props.currentUser))
const roleLabel = computed(() => resolveRoleLabel(props.currentUser))
const passwordUpdatedAtLabel = computed(() => formatPasswordUpdatedAt(props.currentUser?.password_updated_at))
const accountStatusLabel = computed(() =>
  props.currentUser?.account_status_label || (props.currentUser?.is_active ? '账户可用' : '账户停用'),
)
const passwordStatusLabel = computed(() =>
  props.currentUser?.password_status_label ||
  (props.currentUser?.password_reset_required ? '待修改密码' : '状态正常'),
)
const passwordFormDisabled = computed(() => props.currentUser?.is_active === false)

const resetForm = () => {
  Object.assign(passwordForm, {
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  formRef.value?.clearValidate()
}

const changePassword = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    const response = await axios.post<PasswordChangeResponse>('/api/users/me/change-password/', passwordForm)
    const sessionUser = setSessionUser(response.data.user)
    emit('changed', sessionUser)
    ElMessage.success(response.data.detail || '密码修改成功')
    resetForm()
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '密码修改失败，请稍后重试。'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-card class="security-card workspace-surface-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span>账户安全</span>
        <div class="header-tags">
          <el-tag effect="plain" type="primary">{{ roleLabel }}</el-tag>
          <el-tag :type="currentUser?.password_reset_required ? 'warning' : 'success'" effect="plain">
            {{ currentUser?.password_reset_required ? '待修改密码' : '密码状态正常' }}
          </el-tag>
        </div>
      </div>
    </template>

    <div class="security-summary">
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">当前身份</span>
          <strong>{{ roleLabel }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">密码更新时间</span>
          <strong>{{ passwordUpdatedAtLabel }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">账户状态</span>
          <strong>{{ accountStatusLabel }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">密码状态</span>
          <strong>{{ passwordStatusLabel }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">安全提示</span>
          <p>{{ securityNotice }}</p>
        </div>
        <div class="meta-item">
          <span class="meta-label">账户周期</span>
          <p>{{ lifecycleHint }}</p>
        </div>
      </div>
    </div>

    <el-form ref="formRef" :model="passwordForm" :rules="rules" label-position="top" class="security-form">
      <div class="form-grid">
        <el-form-item label="当前密码" prop="current_password" required>
          <el-input
            v-model="passwordForm.current_password"
            type="password"
            show-password
            :disabled="passwordFormDisabled"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password" required>
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
            :disabled="passwordFormDisabled"
          />
        </el-form-item>
      </div>

      <el-form-item label="确认新密码" prop="confirm_password" required>
        <el-input
          v-model="passwordForm.confirm_password"
          type="password"
          show-password
          :disabled="passwordFormDisabled"
          @keyup.enter="changePassword"
        />
      </el-form-item>

      <div class="panel-actions">
        <el-button @click="resetForm" :disabled="passwordFormDisabled">重置</el-button>
        <el-button type="primary" :loading="loading" :disabled="passwordFormDisabled" @click="changePassword">修改密码</el-button>
      </div>
    </el-form>
  </el-card>
</template>

<style scoped>
.security-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.card-header,
.header-tags,
.panel-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-header {
  justify-content: space-between;
}

.header-tags {
  flex-wrap: wrap;
}

.security-summary {
  display: grid;
  gap: 16px;
  margin-bottom: 22px;
}

.meta-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.meta-item {
  padding: 18px 20px;
  border-radius: 20px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.meta-label {
  display: block;
  margin-bottom: 10px;
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.6;
}

.meta-item strong {
  display: block;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.4;
}

.meta-item p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.8;
}

.security-form :deep(.el-form-item__label) {
  color: var(--text-secondary) !important;
  font-weight: 600;
}

.form-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel-actions {
  justify-content: flex-end;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .card-header,
  .header-tags,
  .panel-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .meta-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .meta-item strong {
    font-size: 18px;
  }
}
</style>
