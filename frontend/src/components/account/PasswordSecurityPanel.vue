<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { PasswordChangeResponse } from '../../types/users'
import {
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
const roleLabel = computed(() => resolveRoleLabel(props.currentUser))
const passwordUpdatedAtLabel = computed(() => formatPasswordUpdatedAt(props.currentUser?.password_updated_at))

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
  <el-card class="security-card" shadow="never">
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
      <el-alert
        :title="securityNotice"
        :type="currentUser?.password_reset_required ? 'warning' : 'info'"
        :closable="false"
        show-icon
      />

      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">当前身份</span>
          <strong>{{ roleLabel }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">密码更新时间</span>
          <strong>{{ passwordUpdatedAtLabel }}</strong>
        </div>
      </div>
    </div>

    <el-form ref="formRef" :model="passwordForm" :rules="rules" label-position="top">
      <div class="form-grid">
        <el-form-item label="当前密码" prop="current_password">
          <el-input v-model="passwordForm.current_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
      </div>

      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input
          v-model="passwordForm.confirm_password"
          type="password"
          show-password
          @keyup.enter="changePassword"
        />
      </el-form-item>

      <div class="panel-actions">
        <el-button @click="resetForm">重置</el-button>
        <el-button type="primary" :loading="loading" @click="changePassword">修改密码</el-button>
      </div>
    </el-form>
  </el-card>
</template>

<style scoped>
.security-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
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
  margin-bottom: 20px;
}

.meta-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.meta-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fbff;
}

.meta-label {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

.form-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel-actions {
  justify-content: flex-end;
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
}
</style>
