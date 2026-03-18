<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, setSessionUser, type SessionUser } from '../utils/sessionAuth'
import type { TeacherAccountResponse } from '../types/users'

interface ProfileFormState {
  real_name: string
  department: string
  title: string
  discipline: string
  research_interests: string
  bio: string
  h_index: number
}

const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const profileFormRef = ref<FormInstance>()

const profileForm = reactive<ProfileFormState>({
  real_name: '',
  department: '',
  title: '',
  discipline: '',
  research_interests: '',
  bio: '',
  h_index: 0,
})

const rules: FormRules<ProfileFormState> = {
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属学院', trigger: 'blur' }],
  title: [{ required: true, message: '请输入职称', trigger: 'blur' }],
}

const profileHighlights = computed(() =>
  profileForm.research_interests
    .split(/[，,、]/)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 6),
)

const toResearchDirection = (source: string) =>
  source
    .split(/[，,、]/)
    .map(item => item.trim())
    .filter(Boolean)

const hydrateProfileForm = (user: SessionUser) => {
  Object.assign(profileForm, {
    real_name: user.real_name || '',
    department: user.department || '',
    title: user.title || '',
    discipline: user.discipline || '',
    research_interests: user.research_interests || '',
    bio: user.bio || '',
    h_index: user.h_index || 0,
  })
}

const ensureUser = async (): Promise<SessionUser | null> => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return null
  }

  currentUser.value = sessionUser
  hydrateProfileForm(sessionUser)
  return sessionUser
}

const saveProfile = async () => {
  if (!profileFormRef.value) return
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const response = await axios.patch<TeacherAccountResponse>('/api/users/me/', {
      ...profileForm,
      research_direction: toResearchDirection(profileForm.research_interests),
    })
    setSessionUser(response.data)
    await ensureUser()
    ElMessage.success('基础档案已更新')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '基础档案保存失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void ensureUser()
})
</script>

<template>
  <div class="profile-editor-page">
    <section class="hero-panel">
      <div class="hero-copy">
        <p class="eyebrow">Profile Editor</p>
        <h1>编辑基础档案</h1>
        <p>
          这里仅维护当前登录账号的基础信息、研究方向和个人简介，不再与教师管理入口混合展示。
        </p>
      </div>

      <div class="hero-actions">
        <el-button type="primary" @click="router.push('/dashboard')">返回画像主页</el-button>
      </div>
    </section>

    <section class="editor-shell">
      <el-card class="editor-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>我的基础档案</span>
            <el-tag type="primary" effect="plain">{{ currentUser?.username || '未登录' }}</el-tag>
          </div>
        </template>

        <div class="profile-banner">
          <div class="identity-chip">
            <strong>{{ currentUser?.real_name || currentUser?.username || '教师' }}</strong>
            <span>工号 {{ currentUser?.id || '-' }}</span>
          </div>
          <div class="tag-list">
            <el-tag v-for="tag in profileHighlights" :key="tag" effect="plain" type="success">{{ tag }}</el-tag>
            <span v-if="!profileHighlights.length" class="muted">暂未维护研究兴趣标签</span>
          </div>
        </div>

        <el-form ref="profileFormRef" :model="profileForm" :rules="rules" label-position="top">
          <div class="grid two-cols">
            <el-form-item label="工号(ID)">
              <el-input :model-value="currentUser?.id" disabled />
            </el-form-item>
            <el-form-item label="登录账号">
              <el-input :model-value="currentUser?.username" disabled />
            </el-form-item>
          </div>

          <div class="grid two-cols">
            <el-form-item label="姓名" prop="real_name">
              <el-input v-model="profileForm.real_name" />
            </el-form-item>
            <el-form-item label="职称" prop="title">
              <el-input v-model="profileForm.title" />
            </el-form-item>
          </div>

          <div class="grid two-cols">
            <el-form-item label="所属学院" prop="department">
              <el-input v-model="profileForm.department" />
            </el-form-item>
            <el-form-item label="学科方向">
              <el-input v-model="profileForm.discipline" />
            </el-form-item>
          </div>

          <div class="grid two-cols">
            <el-form-item label="H-index">
              <el-input-number v-model="profileForm.h_index" :min="0" style="width: 100%" />
            </el-form-item>
            <el-form-item label="研究兴趣">
              <el-input v-model="profileForm.research_interests" placeholder="多个兴趣可用逗号分隔" />
            </el-form-item>
          </div>

          <el-form-item label="个人简介">
            <el-input v-model="profileForm.bio" type="textarea" :rows="5" />
          </el-form-item>

          <div class="actions">
            <el-button @click="ensureUser">重置内容</el-button>
            <el-button type="primary" :loading="loading" @click="saveProfile">保存基础档案</el-button>
          </div>
        </el-form>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.profile-editor-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
}

.hero-panel {
  max-width: 1080px;
  margin: 0 auto 22px;
  padding: 28px 32px;
  border-radius: 26px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 65%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.14);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

h1 {
  margin: 0;
}

.hero-copy p:last-child {
  margin: 12px 0 0;
  max-width: 720px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.88);
}

.editor-shell {
  max-width: 980px;
  margin: 0 auto;
}

.editor-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.card-header,
.actions,
.profile-banner {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.profile-banner {
  margin-bottom: 20px;
  padding: 18px 20px;
  border-radius: 20px;
  background: #f8fbff;
}

.identity-chip {
  display: grid;
  gap: 6px;
}

.identity-chip strong {
  color: #0f172a;
  font-size: 18px;
}

.identity-chip span,
.muted {
  color: #64748b;
}

.grid {
  display: grid;
  gap: 16px;
}

.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.actions {
  margin-top: 12px;
  justify-content: center;
}

@media (max-width: 768px) {
  .profile-editor-page {
    padding: 16px;
  }

  .hero-panel,
  .profile-banner,
  .two-cols {
    flex-direction: column;
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .tag-list {
    justify-content: flex-start;
  }
}
</style>
