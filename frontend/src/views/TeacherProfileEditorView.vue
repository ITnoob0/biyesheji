<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import PasswordSecurityPanel from '../components/account/PasswordSecurityPanel.vue'
import PersonalCenterQuickLinks from '../components/account/PersonalCenterQuickLinks.vue'
import RepresentativeAchievementsPanel from '../components/account/RepresentativeAchievementsPanel.vue'
import { buildPasswordSecurityNotice, resolveApiErrorMessage, resolveRoleLabel } from '../utils/authPresentation.js'
import { ensureSessionUserContext, setSessionUser, type SessionUser } from '../utils/sessionAuth'
import type { TeacherAccountResponse } from '../types/users'
import type { AchievementOverview, DashboardStatsResponse, RecentAchievementRecord } from './dashboard/portrait'
import {
  internalManagementFieldLabels,
  internalManagementBoundaryNote,
  publicDisplayBoundaryNote,
  publicDisplayFieldLabels,
} from './personal-center/boundaries'

interface ProfileFormState {
  real_name: string
  department: string
  title: string
  email: string
  contact_phone: string
  avatar_url: string
  discipline: string
  research_direction_input: string
  research_interests: string
  bio: string
  h_index: number
}

const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const summaryLoading = ref(false)
const profileFormRef = ref<FormInstance>()
const recentAchievements = ref<RecentAchievementRecord[]>([])
const achievementOverview = ref<AchievementOverview>({
  paper_count: 0,
  project_count: 0,
  intellectual_property_count: 0,
  teaching_achievement_count: 0,
  academic_service_count: 0,
  total_citations: 0,
  total_achievements: 0,
})

const profileForm = reactive<ProfileFormState>({
  real_name: '',
  department: '',
  title: '',
  email: '',
  contact_phone: '',
  avatar_url: '',
  discipline: '',
  research_direction_input: '',
  research_interests: '',
  bio: '',
  h_index: 0,
})

const rules: FormRules<ProfileFormState> = {
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属院系', trigger: 'blur' }],
  title: [{ required: true, message: '请输入职称', trigger: 'blur' }],
}

const parseTagInput = (source: string) =>
  source
    .split(/[，,、\n]/)
    .map(item => item.trim())
    .filter(Boolean)

const profileHighlights = computed(() =>
  Array.from(
    new Set([
      ...parseTagInput(profileForm.research_direction_input),
      ...parseTagInput(profileForm.research_interests),
    ]),
  ).slice(0, 8),
)

const roleLabel = computed(() => resolveRoleLabel(currentUser.value))
const securityNotice = computed(() => buildPasswordSecurityNotice(currentUser.value))
const contactSummary = computed(() => [profileForm.email, profileForm.contact_phone].filter(Boolean).join(' · '))
const displayName = computed(() => currentUser.value?.real_name || currentUser.value?.username || '教师')
const avatarText = computed(() => displayName.value.trim().slice(0, 1).toUpperCase() || 'T')
const permissionScope = computed(() => currentUser.value?.permission_scope ?? null)
const publicDisplayFields = publicDisplayFieldLabels
const internalDisplayFields = internalManagementFieldLabels

const hydrateProfileForm = (user: SessionUser) => {
  Object.assign(profileForm, {
    real_name: user.real_name || '',
    department: user.department || '',
    title: user.title || '',
    email: user.email || '',
    contact_phone: user.contact_phone || '',
    avatar_url: user.avatar_url || '',
    discipline: user.discipline || '',
    research_direction_input: (user.research_direction || []).join('，'),
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

const loadSummary = async () => {
  summaryLoading.value = true
  try {
    const response = await axios.get<DashboardStatsResponse>('/api/achievements/dashboard-stats/')
    recentAchievements.value = response.data.recent_achievements ?? []
    achievementOverview.value = response.data.achievement_overview ?? achievementOverview.value
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '个人中心摘要加载失败'))
  } finally {
    summaryLoading.value = false
  }
}

const saveProfile = async () => {
  if (!profileFormRef.value) return
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const response = await axios.patch<TeacherAccountResponse>('/api/users/me/', {
      real_name: profileForm.real_name,
      department: profileForm.department,
      title: profileForm.title,
      email: profileForm.email,
      contact_phone: profileForm.contact_phone,
      avatar_url: profileForm.avatar_url,
      discipline: profileForm.discipline,
      research_direction: parseTagInput(profileForm.research_direction_input),
      research_interests: profileForm.research_interests,
      bio: profileForm.bio,
      h_index: profileForm.h_index,
    })
    currentUser.value = setSessionUser(response.data)
    hydrateProfileForm(currentUser.value)
    ElMessage.success('个人中心资料已更新')
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '个人中心资料保存失败'))
  } finally {
    loading.value = false
  }
}

const handlePasswordChanged = (user: SessionUser) => {
  currentUser.value = user
  hydrateProfileForm(user)
}

onMounted(async () => {
  const sessionUser = await ensureUser()
  if (!sessionUser) return
  await loadSummary()
})
</script>

<template>
  <div class="personal-center-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div class="hero-profile">
        <div class="hero-avatar">
          <img v-if="profileForm.avatar_url" :src="profileForm.avatar_url" alt="教师头像" />
          <span v-else>{{ avatarText }}</span>
        </div>
        <div class="hero-copy">
          <p class="eyebrow workspace-hero__eyebrow">Teacher Personal Center</p>
          <h1 class="workspace-hero__title">{{ displayName }}</h1>
          <p class="hero-subtitle workspace-hero__text">
            {{ profileForm.department || '待补充院系' }} · {{ profileForm.title || '待补充职称' }} · {{ roleLabel }}
          </p>
          <p class="hero-description">
            当前页面整合了个人资料、成果速览、画像入口、推荐入口和问答入口，是教师视角下的统一个人中心。
          </p>
          <div class="hero-tags">
            <el-tag type="primary" effect="dark">工号 {{ currentUser?.id || '-' }}</el-tag>
            <el-tag effect="plain">{{ profileForm.discipline || '待补充研究领域' }}</el-tag>
            <el-tag effect="plain">H-index {{ profileForm.h_index }}</el-tag>
            <el-tag effect="plain">{{ achievementOverview.total_achievements }} 项成果</el-tag>
          </div>
        </div>
      </div>

      <div class="hero-actions workspace-page-actions">
        <el-button type="primary" @click="router.push('/dashboard')">查看画像主页</el-button>
        <el-button plain @click="loadSummary" :loading="summaryLoading">刷新中心摘要</el-button>
      </div>
    </section>

    <section class="center-layout">
      <div class="main-column">
        <el-card class="profile-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="card-header workspace-section-head">
              <span>公开展示资料</span>
              <el-tag type="success" effect="plain">资料 + 展示一体化</el-tag>
            </div>
          </template>

          <el-alert :title="publicDisplayBoundaryNote" type="info" :closable="false" show-icon />

          <div class="field-tag-list">
            <el-tag v-for="item in publicDisplayFields" :key="item" effect="plain">{{ item }}</el-tag>
          </div>

          <div class="profile-preview">
            <div class="preview-avatar">
              <img v-if="profileForm.avatar_url" :src="profileForm.avatar_url" alt="教师头像预览" />
              <span v-else>{{ avatarText }}</span>
            </div>
            <div class="preview-copy">
              <strong>{{ profileForm.real_name || displayName }}</strong>
              <p>{{ profileForm.bio || '你可以在这里维护个人简介，让画像、推荐和问答输入更完整。' }}</p>
              <div class="preview-meta">
                <span>{{ contactSummary || '待补充联系方式' }}</span>
                <span>{{ profileForm.department || '待补充院系' }}</span>
                <span>{{ profileForm.title || '待补充职称' }}</span>
              </div>
            </div>
          </div>

          <el-form ref="profileFormRef" :model="profileForm" :rules="rules" label-position="top" class="profile-form">
            <div class="grid two-cols">
              <el-form-item label="姓名" prop="real_name">
                <el-input v-model="profileForm.real_name" />
              </el-form-item>
              <el-form-item label="头像地址">
                <el-input v-model="profileForm.avatar_url" placeholder="请输入头像图片 URL" />
              </el-form-item>
            </div>

            <div class="grid two-cols">
              <el-form-item label="所属院系" prop="department">
                <el-input v-model="profileForm.department" />
              </el-form-item>
              <el-form-item label="职称" prop="title">
                <el-input v-model="profileForm.title" />
              </el-form-item>
            </div>

            <div class="grid two-cols">
              <el-form-item label="联系邮箱">
                <el-input v-model="profileForm.email" placeholder="建议填写常用工作邮箱" />
              </el-form-item>
              <el-form-item label="联系电话">
                <el-input v-model="profileForm.contact_phone" placeholder="如 13800000000" />
              </el-form-item>
            </div>

            <div class="grid two-cols">
              <el-form-item label="研究领域">
                <el-input v-model="profileForm.discipline" placeholder="例如：人工智能、数据科学" />
              </el-form-item>
              <el-form-item label="H-index">
                <el-input-number v-model="profileForm.h_index" :min="0" style="width: 100%" />
              </el-form-item>
            </div>

            <el-form-item label="研究方向">
              <el-input
                v-model="profileForm.research_direction_input"
                placeholder="多个研究方向可用中文逗号分隔"
              />
            </el-form-item>

            <el-form-item label="研究兴趣">
              <el-input
                v-model="profileForm.research_interests"
                placeholder="多个研究兴趣可用中文逗号分隔"
              />
            </el-form-item>

            <div class="field-tag-list compact">
              <el-tag v-for="tag in profileHighlights" :key="tag" type="success" effect="plain">{{ tag }}</el-tag>
              <span v-if="!profileHighlights.length" class="muted">暂未维护研究方向和研究兴趣标签</span>
            </div>

            <el-form-item label="个人简介">
              <el-input v-model="profileForm.bio" type="textarea" :rows="5" />
            </el-form-item>

            <div class="actions">
              <el-button @click="ensureUser">重置内容</el-button>
              <el-button type="primary" :loading="loading" @click="saveProfile">保存公开资料</el-button>
            </div>
          </el-form>
        </el-card>

        <RepresentativeAchievementsPanel
          :loading="summaryLoading"
          :achievement-overview="achievementOverview"
          :recent-achievements="recentAchievements"
        />
      </div>

      <div class="side-column">
        <el-card class="internal-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="card-header workspace-section-head">
              <span>内部管理信息</span>
              <el-tag type="warning" effect="plain">仅本人 / 管理员可见</el-tag>
            </div>
          </template>

          <el-alert :title="internalManagementBoundaryNote" type="warning" :closable="false" show-icon />

          <div class="field-tag-list">
            <el-tag v-for="item in internalDisplayFields" :key="item" type="warning" effect="plain">{{ item }}</el-tag>
          </div>

          <div class="internal-grid">
            <div class="internal-item">
              <span>工号</span>
              <strong>{{ currentUser?.id || '-' }}</strong>
            </div>
            <div class="internal-item">
              <span>登录账号</span>
              <strong>{{ currentUser?.username || '-' }}</strong>
            </div>
            <div class="internal-item">
              <span>角色身份</span>
              <strong>{{ roleLabel }}</strong>
            </div>
            <div class="internal-item">
              <span>账户状态</span>
              <strong>{{ currentUser?.is_active ? '账户可用' : '账户停用' }}</strong>
            </div>
            <div class="internal-item">
              <span>密码状态</span>
              <strong>{{ currentUser?.password_reset_required ? '待修改密码' : '状态正常' }}</strong>
            </div>
            <div class="internal-item">
              <span>安全提示</span>
              <strong>{{ securityNotice }}</strong>
            </div>
          </div>

          <div v-if="permissionScope" class="permission-scope-panel">
            <div class="permission-scope-copy">
              <span>当前权限边界</span>
              <strong>{{ permissionScope.scope_summary }}</strong>
            </div>

            <div class="permission-scope-copy">
              <span>当前可执行操作</span>
              <div class="field-tag-list compact">
                <el-tag
                  v-for="item in permissionScope.allowed_actions"
                  :key="`allow-${item}`"
                  type="success"
                  effect="plain"
                >
                  {{ item }}
                </el-tag>
              </div>
            </div>

            <div class="permission-scope-copy">
              <span>当前受限边界</span>
              <div class="field-tag-list compact">
                <el-tag
                  v-for="item in permissionScope.restricted_actions"
                  :key="`restricted-${item}`"
                  type="warning"
                  effect="plain"
                >
                  {{ item }}
                </el-tag>
              </div>
            </div>

            <div class="permission-scope-copy">
              <span>后续多角色扩展预留</span>
              <p>{{ permissionScope.future_extension_hint }}</p>
            </div>
          </div>
        </el-card>

        <PersonalCenterQuickLinks
          :achievement-total="achievementOverview.total_achievements"
          :representative-count="recentAchievements.length"
        />
      </div>
    </section>

    <PasswordSecurityPanel :current-user="currentUser" @changed="handlePasswordChanged" />
  </div>
</template>

<style scoped>
.personal-center-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 24%),
    radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.12), transparent 20%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
}

.hero-panel {
  max-width: 1180px;
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

.hero-profile {
  display: flex;
  align-items: center;
  gap: 20px;
}

.hero-avatar,
.preview-avatar {
  width: 92px;
  height: 92px;
  border-radius: 28px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.18);
  font-size: 34px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.preview-avatar {
  width: 78px;
  height: 78px;
  border-radius: 24px;
  background: linear-gradient(145deg, rgba(124, 168, 240, 0.98), rgba(73, 112, 192, 0.96));
}

.hero-avatar img,
.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-copy {
  display: grid;
  gap: 10px;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

h1 {
  margin: 0;
}

.hero-subtitle,
.hero-description {
  margin: 0;
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.7;
}

.hero-tags,
.field-tag-list,
.preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-actions,
.card-header,
.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.center-layout {
  max-width: 1180px;
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 20px;
}

.main-column,
.side-column {
  display: grid;
  gap: 20px;
}

.profile-card,
.internal-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.field-tag-list {
  margin: 16px 0 18px;
}

.field-tag-list.compact {
  margin-top: -4px;
}

.profile-preview {
  display: flex;
  gap: 18px;
  align-items: center;
  margin-bottom: 20px;
  padding: 18px 20px;
  border-radius: 20px;
  background: #f8fbff;
}

.preview-copy {
  display: grid;
  gap: 8px;
}

.preview-copy strong {
  color: #0f172a;
  font-size: 18px;
}

.preview-copy p,
.preview-meta,
.muted {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.profile-form {
  margin-top: 4px;
}

.grid {
  display: grid;
  gap: 16px;
}

.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.actions {
  justify-content: flex-end;
  margin-top: 12px;
}

.internal-grid {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.permission-scope-panel {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.internal-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fbff;
}

.internal-item span,
.permission-scope-copy span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

.internal-item strong,
.permission-scope-copy strong {
  color: #0f172a;
  line-height: 1.7;
}

.permission-scope-copy {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fbff;
}

.permission-scope-copy p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

@media (max-width: 1180px) {
  .center-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .personal-center-page {
    padding: 16px;
  }

  .hero-panel,
  .hero-profile,
  .hero-actions,
  .profile-preview,
  .two-cols,
  .card-header,
  .actions {
    flex-direction: column;
    grid-template-columns: 1fr;
    align-items: stretch;
  }
}
</style>
