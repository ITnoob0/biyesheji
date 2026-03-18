<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { TeacherCreateResponse } from '../types/users'

interface RegisterFormState {
  employee_id: string
  real_name: string
  department: string
  title: string
  discipline: string
  research_interests: string
  bio: string
  password: string
  confirm_password: string
}

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const registerResult = ref<Pick<TeacherCreateResponse, 'username' | 'employee_id'> | null>(null)

const form = reactive<RegisterFormState>({
  employee_id: '',
  real_name: '',
  department: '',
  title: '',
  discipline: '',
  research_interests: '',
  bio: '',
  password: '',
  confirm_password: '',
})

const rules: FormRules<RegisterFormState> = {
  employee_id: [{ required: true, message: '请输入 6 位工号', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入教师姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属学院', trigger: 'blur' }],
  title: [{ required: true, message: '请输入职称', trigger: 'blur' }],
  password: [{ required: true, message: '请设置登录密码', trigger: 'blur' }],
  confirm_password: [{ required: true, message: '请再次输入登录密码', trigger: 'blur' }],
}

const toResearchDirection = (source: string) =>
  source
    .split(/[，,、]/)
    .map(item => item.trim())
    .filter(Boolean)

const handleRegister = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    const response = await axios.post<TeacherCreateResponse>('/api/users/register/', {
      ...form,
      research_direction: toResearchDirection(form.research_interests),
      h_index: 0,
    })

    registerResult.value = {
      username: response.data.username,
      employee_id: response.data.employee_id,
    }
    ElMessage.success('教师账号注册成功，请使用工号和刚设置的密码登录')
  } catch (error: any) {
    const detail = error?.response?.data
    if (detail && typeof detail === 'object') {
      const firstError = Object.values(detail)[0]
      ElMessage.error(Array.isArray(firstError) ? String(firstError[0]) : String(firstError))
    } else {
      ElMessage.error('注册失败，请检查输入信息')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <div class="topbar">
        <div>
          <p class="eyebrow">Teacher Registration</p>
          <h1>教师自助注册</h1>
        </div>
        <el-button @click="router.push('/login')">返回登录</el-button>
      </div>

      <el-alert
        title="注册后，工号将直接作为登录用户名。请在注册时自行设置登录密码。"
        type="info"
        :closable="false"
        show-icon
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="grid two-cols">
          <el-form-item label="六位工号" prop="employee_id">
            <el-input v-model="form.employee_id" maxlength="6" placeholder="例如 100001" />
          </el-form-item>
          <el-form-item label="教师姓名" prop="real_name">
            <el-input v-model="form.real_name" placeholder="请输入真实姓名" />
          </el-form-item>
        </div>

        <div class="grid two-cols">
          <el-form-item label="所属学院" prop="department">
            <el-input v-model="form.department" placeholder="例如 计算机学院" />
          </el-form-item>
          <el-form-item label="职称" prop="title">
            <el-input v-model="form.title" placeholder="例如 讲师、副教授、教授" />
          </el-form-item>
        </div>

        <div class="grid two-cols">
          <el-form-item label="学科方向">
            <el-input v-model="form.discipline" placeholder="例如 人工智能" />
          </el-form-item>
          <el-form-item label="研究兴趣">
            <el-input
              v-model="form.research_interests"
              placeholder="多个兴趣可用逗号分隔"
            />
          </el-form-item>
        </div>

        <el-form-item label="个人简介">
          <el-input v-model="form.bio" type="textarea" :rows="4" placeholder="请输入个人简介" />
        </el-form-item>

        <div class="grid two-cols">
          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请设置登录密码"
            />
          </el-form-item>
          <el-form-item label="确认登录密码" prop="confirm_password">
            <el-input
              v-model="form.confirm_password"
              type="password"
              show-password
              placeholder="请再次输入登录密码"
              @keyup.enter="handleRegister"
            />
          </el-form-item>
        </div>

        <el-button type="primary" :loading="loading" @click="handleRegister">创建教师账号</el-button>
      </el-form>

      <el-result
        v-if="registerResult"
        icon="success"
        title="注册完成"
        sub-title="请使用工号作为登录用户名，并使用刚刚设置的密码登录系统。"
      >
        <template #extra>
          <div class="result-box">
            <p>工号(ID)：{{ registerResult.employee_id }}</p>
            <p>登录用户名：{{ registerResult.username }}</p>
          </div>
          <el-button type="primary" @click="router.push('/login')">去登录</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.16), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.18), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.register-card {
  width: min(920px, 100%);
  margin: 0 auto;
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
  gap: 16px;
  align-items: center;
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

.grid {
  display: grid;
  gap: 16px;
}

.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.result-box {
  margin-bottom: 16px;
  padding: 16px 20px;
  border-radius: 16px;
  background: #f8fafc;
  text-align: left;
}

.result-box p {
  margin: 8px 0;
}

@media (max-width: 768px) {
  .register-page {
    padding: 16px;
  }

  .register-card {
    padding: 24px;
  }

  .topbar,
  .two-cols {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
