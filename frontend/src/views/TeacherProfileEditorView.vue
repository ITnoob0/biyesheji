<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules, UploadRequestOptions } from 'element-plus'
import { useRouter } from 'vue-router'
import PasswordSecurityPanel from '../components/account/PasswordSecurityPanel.vue'
import PersonalCenterQuickLinks from '../components/account/PersonalCenterQuickLinks.vue'
import RepresentativeAchievementsPanel from '../components/account/RepresentativeAchievementsPanel.vue'
import {
  buildPasswordSecurityNotice,
  buildPublicContactSummary,
  resolveApiErrorMessage,
  resolveContactVisibilityLabel,
  resolveRoleLabel,
} from '../utils/authPresentation.js'
import { ensureSessionUserContext, setSessionUser, type SessionUser } from '../utils/sessionAuth'
import type { TeacherAccountResponse } from '../types/users'
import type { AchievementOverview, DashboardStatsResponse, RecentAchievementRecord } from './dashboard/portrait'

interface ProfileFormState {
  real_name: string
  department: string
  title: string
  email: string
  contact_phone: string
  contact_visibility: 'email_only' | 'phone_only' | 'both' | 'internal_only'
  avatar_url: string
  discipline: string
  research_direction_input: string
  research_interests: string
  bio: string
  h_index: number
}

interface AvatarUploadResponse {
  detail: string
  avatar_url: string
  user: TeacherAccountResponse
}

type PersonalCenterSection = 'public-profile' | 'security' | 'quick-links'

const props = withDefaults(
  defineProps<{
    sectionMode?: PersonalCenterSection
  }>(),
  {
    sectionMode: 'public-profile',
  },
)

const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const summaryLoading = ref(false)
const avatarUploading = ref(false)
const profileFormRef = ref<FormInstance>()
const recentAchievements = ref<RecentAchievementRecord[]>([])
const pendingClaimCount = ref(0)
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
  contact_visibility: 'email_only',
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

const contactVisibilityOptions = [
  { value: 'email_only', label: '仅公开邮箱' },
  { value: 'phone_only', label: '仅公开电话' },
  { value: 'both', label: '公开邮箱和电话' },
  { value: 'internal_only', label: '仅内部可见' },
] as const

const parseTagInput = (source: string) =>
  source
    .split(/[，、\n]/)
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
const contactSummary = computed(() => [profileForm.email, profileForm.contact_phone].filter(Boolean).join(' / '))
const displayName = computed(() => currentUser.value?.real_name || currentUser.value?.username || '教师')
const avatarText = computed(() => displayName.value.trim().slice(0, 1).toUpperCase() || 'T')
const permissionScope = computed(() => currentUser.value?.permission_scope ?? null)
const contactVisibilityLabel = computed(() => resolveContactVisibilityLabel(profileForm.contact_visibility))
const publicContactChannels = computed(() => {
  const channels = []
  if (['email_only', 'both'].includes(profileForm.contact_visibility) && profileForm.email.trim()) {
    channels.push({ key: 'email', label: '联系邮箱', value: profileForm.email.trim() })
  }
  if (['phone_only', 'both'].includes(profileForm.contact_visibility) && profileForm.contact_phone.trim()) {
    channels.push({ key: 'phone', label: '联系电话', value: profileForm.contact_phone.trim() })
  }
  return channels
})
const publicContactSummary = computed(() =>
  buildPublicContactSummary({
    contact_visibility: profileForm.contact_visibility,
    public_contact_channels: publicContactChannels.value,
  }),
)
const profileCompleteness = computed(() => {
  const checkpoints = [
    profileForm.real_name,
    profileForm.department,
    profileForm.title,
    profileForm.discipline,
    profileForm.research_direction_input,
    profileForm.research_interests,
    profileForm.bio,
    profileForm.avatar_url,
  ]
  const completed = checkpoints.filter(item => String(item || '').trim()).length
  return Math.round((completed / checkpoints.length) * 100)
})

const activeSection = computed(() => props.sectionMode)
const isPublicProfileSection = computed(() => activeSection.value === 'public-profile')
const isSecuritySection = computed(() => activeSection.value === 'security')
const isQuickLinksSection = computed(() => activeSection.value === 'quick-links')
const canAccessClaimCenter = computed(() => currentUser.value?.role_code === 'teacher')

const hydrateProfileForm = (user: SessionUser) => {
  Object.assign(profileForm, {
    real_name: user.real_name || '',
    department: user.department || '',
    title: user.title || '',
    email: user.email || '',
    contact_phone: user.contact_phone || '',
    contact_visibility: user.contact_visibility || 'email_only',
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

const loadClaimPendingCount = async () => {
  if (!canAccessClaimCenter.value) {
    pendingClaimCount.value = 0
    return
  }
  try {
    const response = await axios.get<{ pending_count: number }>('/api/achievements/claims/pending-count/')
    pendingClaimCount.value = Number(response.data.pending_count || 0)
  } catch (error: any) {
    pendingClaimCount.value = 0
    ElMessage.error(resolveApiErrorMessage(error, '待认领成果统计加载失败'))
  }
}

const refreshOverview = async () => {
  await Promise.all([loadSummary(), loadClaimPendingCount()])
}

const beforeAvatarUpload = (file: File) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isImage) {
    ElMessage.error('头像上传仅支持图片文件。')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('头像文件不能超过 2MB。')
    return false
  }
  return true
}

const uploadAvatar = async (options: UploadRequestOptions) => {
  avatarUploading.value = true
  const formData = new FormData()
  formData.append('avatar', options.file)

  try {
    const response = await axios.post<AvatarUploadResponse>('/api/users/me/avatar/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    currentUser.value = setSessionUser(response.data.user)
    hydrateProfileForm(currentUser.value)
    ElMessage.success(response.data.detail)
    options.onSuccess?.(response.data)
  } catch (error: any) {
    const message = resolveApiErrorMessage(error, '头像上传失败')
    ElMessage.error(message)
    options.onError?.(error)
  } finally {
    avatarUploading.value = false
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
      contact_visibility: profileForm.contact_visibility,
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
  await refreshOverview()
})
</script>

<template>
  <div class="personal-center-page workspace-page">
    <section v-if="isPublicProfileSection" class="single-layout">
      <el-card class="profile-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="card-header workspace-section-head">
            <div class="card-title-block">
              <span>公开资料</span>
              <p>{{ profileCompleteness }}% 完整度 / {{ publicContactSummary }}</p>
            </div>
            <div class="header-actions">
              <el-badge v-if="canAccessClaimCenter" :value="pendingClaimCount" :hidden="pendingClaimCount <= 0">
                <el-button plain type="primary" @click="router.push('/profile-editor/achievement-claims')">待认领成果</el-button>
              </el-badge>
              <el-button plain :loading="summaryLoading" @click="refreshOverview">刷新资料</el-button>
            </div>
          </div>
        </template>

        <div class="profile-preview">
          <div class="preview-avatar">
            <img v-if="profileForm.avatar_url" :src="profileForm.avatar_url" alt="教师头像预览" />
            <span v-else>{{ avatarText }}</span>
          </div>
          <div class="preview-copy">
            <strong>{{ profileForm.real_name || displayName }}</strong>
            <p>{{ profileForm.bio || '暂未维护个人简介。' }}</p>
            <div class="preview-meta">
              <span>{{ profileForm.department || '待补充院系' }}</span>
              <span>{{ profileForm.title || '待补充职称' }}</span>
              <span>{{ roleLabel }}</span>
            </div>
            <div class="field-tag-list compact">
              <el-tag v-if="profileForm.discipline" effect="plain">{{ profileForm.discipline }}</el-tag>
              <el-tag v-if="profileForm.h_index > 0" effect="plain">H-index {{ profileForm.h_index }}</el-tag>
              <el-tag v-for="item in publicContactChannels" :key="item.key" type="primary" effect="plain">
                {{ item.label }}：{{ item.value }}
              </el-tag>
              <el-tag v-for="tag in profileHighlights" :key="tag" type="success" effect="plain">{{ tag }}</el-tag>
            </div>
          </div>
        </div>

        <el-form ref="profileFormRef" :model="profileForm" :rules="rules" label-position="top" class="profile-form">
          <div class="grid two-cols">
            <el-form-item label="姓名" prop="real_name">
              <el-input v-model="profileForm.real_name" />
            </el-form-item>
            <el-form-item label="头像上传">
              <div class="avatar-upload-panel">
                <el-upload
                  :show-file-list="false"
                  :http-request="uploadAvatar"
                  :before-upload="beforeAvatarUpload"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                >
                  <el-button type="primary" plain :loading="avatarUploading">上传本地头像</el-button>
                </el-upload>
                <span class="field-helper">支持 JPG / PNG / WEBP / GIF，单文件不超过 2MB。</span>
              </div>
            </el-form-item>
          </div>

          <el-form-item label="头像地址备用方式">
            <el-input v-model="profileForm.avatar_url" placeholder="也可直接填写头像图片 URL" />
          </el-form-item>

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

          <el-form-item label="联系方式公开策略">
            <el-radio-group v-model="profileForm.contact_visibility" class="contact-visibility-group">
              <el-radio-button v-for="item in contactVisibilityOptions" :key="item.value" :label="item.value">
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

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
    </section>

    <section v-else-if="isSecuritySection" class="split-layout">
      <el-card class="internal-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="card-header workspace-section-head">
            <span>内部管理信息</span>
            <el-tag type="warning" effect="plain">仅本人 / 管理员可见</el-tag>
          </div>
        </template>

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
          <div class="internal-item">
            <span>联系方式展示策略</span>
            <strong>{{ contactVisibilityLabel }}</strong>
          </div>
          <div class="internal-item">
            <span>内部联系方式总览</span>
            <strong>{{ contactSummary || '待补充联系方式' }}</strong>
          </div>
        </div>

      </el-card>

      <PasswordSecurityPanel :current-user="currentUser" @changed="handlePasswordChanged" />
    </section>

    <section v-else-if="isQuickLinksSection" class="split-layout">
      <RepresentativeAchievementsPanel
        :loading="summaryLoading"
        :achievement-overview="achievementOverview"
        :recent-achievements="recentAchievements"
      />

      <PersonalCenterQuickLinks
        :achievement-total="achievementOverview.total_achievements"
        :representative-count="recentAchievements.length"
      />
    </section>
  </div>
</template>

<style scoped>
.personal-center-page {
  min-height: 100%;
  padding: 28px;
  background: var(--page-bg);
  color: var(--text-secondary);
}

.single-layout,
.split-layout {
  max-width: 1180px;
  margin: 0 auto 20px;
}

.split-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.profile-card,
.internal-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.card-header,
.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-title-block {
  display: grid;
  gap: 4px;
}

.card-title-block p {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.field-tag-list,
.preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.field-tag-list {
  margin: 14px 0 0;
}

.field-tag-list.compact {
  margin-top: 0;
}

.profile-preview {
  display: flex;
  gap: 18px;
  align-items: center;
  padding: 18px 20px;
  border-radius: 20px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.preview-avatar {
  width: 78px;
  height: 78px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(124, 168, 240, 0.98), rgba(73, 112, 192, 0.96));
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-copy {
  display: grid;
  gap: 8px;
}

.preview-copy strong {
  color: var(--text-primary);
  font-size: 18px;
}

.preview-copy p,
.preview-meta,
.muted {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.profile-form {
  margin-top: 24px;
}

.avatar-upload-panel {
  display: grid;
  gap: 10px;
}

.field-helper {
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.6;
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

.contact-visibility-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.internal-grid {
  display: grid;
  gap: 14px;
}

.permission-scope-panel {
  display: grid;
  gap: 18px;
  margin-top: 22px;
  padding-top: 22px;
  border-top: 1px solid var(--divider-color);
}

.permission-scope-section {
  display: grid;
  gap: 8px;
}

.permission-scope-title {
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.6;
}

.permission-scope-text {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.8;
}

.internal-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.internal-item span {
  display: block;
  margin-bottom: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.internal-item strong {
  color: var(--text-primary);
  line-height: 1.8;
  font-size: 18px;
  font-weight: 600;
}

@media (max-width: 1180px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .personal-center-page {
    padding: 16px;
  }

  .profile-preview,
  .two-cols,
  .card-header,
  .header-actions,
  .actions {
    flex-direction: column;
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .permission-scope-text,
  .internal-item strong {
    font-size: 16px;
  }
}
</style>
