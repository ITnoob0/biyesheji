<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules, TableInstance } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import TeacherRadarPreviewDialog from '../components/teacher/TeacherRadarPreviewDialog.vue'
import {
  buildAccountLifecycleHint,
  buildAdminRouteNotice,
  buildPasswordSecurityNotice,
  resolveApiErrorMessage,
  resolvePermissionDeniedMessage,
  resolveRoleLabel,
} from '../utils/authPresentation.js'
import { ensureSessionUserContext, setSessionUser, setSessionNotice, type SessionUser } from '../utils/sessionAuth'
import type {
  TeacherAccountResponse,
  TeacherBulkActionResponse,
  TeacherCreateResponse,
  TeacherManagementSummaryResponse,
  TeacherPasswordResetResponse,
} from '../types/users'

type TeacherManagementSection = 'overview' | 'create-college-admin' | 'create-teacher'

interface TeacherRecord extends TeacherAccountResponse {
  initial_password?: string
}

interface CreateTeacherFormState {
  employee_id: string
  real_name: string
  department: string
  title: string
  discipline: string
  research_interests: string
  bio: string
  h_index: number
  password: string
  confirm_password: string
}

type TeacherMoreAction = 'profile' | 'toggle-status' | 'reset-password'

const router = useRouter()
const route = useRoute()
const teacherTableRef = ref<TableInstance>()

const currentUser = ref<SessionUser | null>(null)
const teachers = ref<TeacherRecord[]>([])
const createLoading = ref(false)
const listLoading = ref(false)
const resetLoadingId = ref<number | null>(null)
const bulkLoading = ref(false)
const selectedTeacherIds = ref<number[]>([])
const keywordFilter = ref('')
const accountStatusFilter = ref<'all' | 'active' | 'inactive'>('all')
const passwordStatusFilter = ref<'all' | 'pending' | 'stable'>('all')
const lastCreatedAccount = ref<Pick<TeacherCreateResponse, 'employee_id' | 'username' | 'initial_password'> | null>(
  null,
)
const lastBulkResult = ref<TeacherBulkActionResponse | null>(null)
const editDialogVisible = ref(false)
const radarPreviewVisible = ref(false)
const previewTeacherId = ref<number | null>(null)
const previewTeacherName = ref('')
const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()
const managementSummary = ref<TeacherManagementSummaryResponse>({
  total_count: 0,
  active_count: 0,
  inactive_count: 0,
  password_reset_required_count: 0,
  stable_password_count: 0,
  recovery_guidance: '',
  future_extension_hint: '',
})

const createTeacherForm = reactive<CreateTeacherFormState>({
  employee_id: '',
  real_name: '',
  department: '',
  title: '',
  discipline: '',
  research_interests: '',
  bio: '',
  h_index: 0,
  password: '',
  confirm_password: '',
})

const editTeacher = reactive<TeacherRecord>({
  id: 0,
  employee_id: 0,
  username: '',
  real_name: '',
  department: '',
  title: '',
  email: '',
  contact_phone: '',
  contact_visibility: 'email_only',
  contact_visibility_label: '仅公开邮箱',
  public_contact_channels: [],
  avatar_url: '',
  research_direction: [],
  bio: '',
  discipline: '',
  research_interests: '',
  h_index: 0,
  is_active: true,
  is_admin: false,
  role_code: 'teacher',
  role_label: '教师账户',
  password_reset_required: false,
  password_updated_at: null,
  security_notice: '',
  account_status_label: '账户可用',
  password_status_label: '状态正常',
  next_action_hint: '当前账户状态正常，可继续维护资料、成果和密码。',
  permission_scope: {
    entry_role: 'teacher',
    scope_summary: '教师账号当前可维护自己的资料、密码和成果，并查看自己的画像、推荐、图谱和问答结果。',
    allowed_actions: [],
    restricted_actions: [],
    future_extension_hint: '如后续引入更多角色，可继续沿用统一权限入口扩展。',
  },
})

const createRules: FormRules<CreateTeacherFormState> = {
  employee_id: [{ required: true, message: '请输入六位工号', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入教师姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属学院', trigger: 'blur' }],
  title: [{ required: true, message: '请输入职称', trigger: 'blur' }],
  password: [{ required: true, message: '请输入登录密码', trigger: 'blur' }],
  confirm_password: [{ required: true, message: '请再次输入登录密码', trigger: 'blur' }],
}

const editRules: FormRules = {
  real_name: [{ required: true, message: '请输入教师姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属学院', trigger: 'blur' }],
  title: [{ required: true, message: '请输入职称', trigger: 'blur' }],
}

const props = withDefaults(
  defineProps<{
    sectionMode?: TeacherManagementSection
  }>(),
  {
    sectionMode: 'overview',
  },
)

const checkedAdmin = computed(() => Boolean(currentUser.value?.is_admin))
const isSystemAdmin = computed(() => currentUser.value?.role_code === 'admin')
const isCollegeAdmin = computed(() => currentUser.value?.role_code === 'college_admin')
const canManageTeacherAccounts = computed(() => isSystemAdmin.value || isCollegeAdmin.value)
const activeSection = computed(() => props.sectionMode)
const showSummaryGrid = computed(() => activeSection.value === 'overview' && isSystemAdmin.value)
const showCreateCard = computed(() => activeSection.value !== 'overview')
const showListCard = computed(() => activeSection.value === 'overview')
const showManagementShell = computed(() => showCreateCard.value || showListCard.value)
const createTargetRoleCode = computed(() => (activeSection.value === 'create-college-admin' ? 'college_admin' : 'teacher'))
const createCardTitle = computed(() =>
  activeSection.value === 'create-college-admin' ? '创建学院管理员' : '创建教师账号',
)
const createButtonText = computed(() =>
  activeSection.value === 'create-college-admin' ? '创建学院管理员' : '创建教师账号',
)
const createRuleNotice = computed(() => {
  if (activeSection.value === 'create-college-admin') {
    return '规则：工号必须是 6 位数字，工号会直接作为学院管理员登录账号；系统管理员创建后的密码会被视为临时密码。'
  }
  return '规则：工号必须是 6 位数字，工号会直接作为教师登录账号；学院管理员仅可创建本学院教师，创建后的密码会被视为临时密码。'
})
const createDepartmentLabel = computed(() => (activeSection.value === 'create-college-admin' ? '所属学院' : '所属学院（固定为本学院）'))
const createResultTitle = computed(() => (activeSection.value === 'create-college-admin' ? '最新创建的学院管理员账号' : '最新创建的教师账号'))
const createResultSubtitle = computed(() =>
  activeSection.value === 'create-college-admin' ? '以下登录信息可通过安全渠道交付给对应学院管理员。' : '以下登录信息可通过安全渠道交付给对应教师。',
)
const focusTeacherId = computed(() => Number(route.query.focus || 0))
const hasSelection = computed(() => selectedTeacherIds.value.length > 0)
const filteredTeachers = computed(() =>
  teachers.value.filter(teacher => {
    const keyword = keywordFilter.value.trim()
    if (keyword) {
      const haystack = [teacher.employee_id, teacher.username, teacher.real_name, teacher.department, teacher.title]
        .filter(Boolean)
        .join(' ')
      if (!haystack.includes(keyword)) {
        return false
      }
    }

    if (accountStatusFilter.value === 'active' && !teacher.is_active) {
      return false
    }
    if (accountStatusFilter.value === 'inactive' && teacher.is_active) {
      return false
    }
    if (passwordStatusFilter.value === 'pending' && !teacher.password_reset_required) {
      return false
    }
    if (passwordStatusFilter.value === 'stable' && teacher.password_reset_required) {
      return false
    }
    return true
  }),
)

const toResearchDirection = (source: string) =>
  source
    .split(/[，,、]/)
    .map(item => item.trim())
    .filter(Boolean)

const resetCreateForm = () => {
  Object.assign(createTeacherForm, {
    employee_id: '',
    real_name: '',
    department: '',
    title: '',
    discipline: '',
    research_interests: '',
    bio: '',
    h_index: 0,
    password: '',
    confirm_password: '',
  })
  createFormRef.value?.clearValidate()
  if (isCollegeAdmin.value) {
    createTeacherForm.department = currentUser.value?.department || ''
  }
}

const ensureAdminUser = async (): Promise<SessionUser | null> => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return null
  }

  if (!sessionUser.is_admin) {
    setSessionNotice(buildAdminRouteNotice('教师管理入口'))
    router.replace({ name: 'dashboard' })
    return null
  }

  currentUser.value = sessionUser
  if (sessionUser.role_code === 'college_admin' && activeSection.value === 'create-teacher') {
    createTeacherForm.department = sessionUser.department || ''
  }
  return sessionUser
}

const loadTeachers = async () => {
  listLoading.value = true
  try {
    const response = await axios.get<TeacherAccountResponse[]>('/api/users/teachers/')
    teachers.value = response.data
    await nextTick()
    focusTeacherRow()
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '教师列表加载失败'))
  } finally {
    listLoading.value = false
  }
}

const loadManagementSummary = async () => {
  try {
    const response = await axios.get<TeacherManagementSummaryResponse>('/api/users/teachers/summary/')
    managementSummary.value = response.data
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '账户生命周期摘要加载失败'))
  }
}

const createTeacher = async () => {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  createLoading.value = true
  try {
    const response = await axios.post<TeacherCreateResponse>('/api/users/teachers/', {
      ...createTeacherForm,
      role_code: createTargetRoleCode.value,
      research_direction: toResearchDirection(createTeacherForm.research_interests),
    })

    lastCreatedAccount.value = {
      employee_id: response.data.employee_id,
      username: response.data.username,
      initial_password: response.data.initial_password,
    }

    ElMessage.success(activeSection.value === 'create-college-admin' ? '学院管理员账号创建成功' : '教师账号创建成功')
    resetCreateForm()
    await Promise.all([loadTeachers(), loadManagementSummary()])
  } catch (error: any) {
    ElMessage.error(
      resolveApiErrorMessage(error, activeSection.value === 'create-college-admin' ? '学院管理员账号创建失败' : '教师账号创建失败'),
    )
  } finally {
    createLoading.value = false
  }
}

const openEditDialog = (teacher: TeacherRecord) => {
  Object.assign(editTeacher, teacher)
  editDialogVisible.value = true
}

const saveTeacherEdit = async () => {
  if (!editFormRef.value) return
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    const response = await axios.patch<TeacherAccountResponse>(`/api/users/teachers/${editTeacher.id}/`, {
      real_name: editTeacher.real_name,
      department: editTeacher.department,
      title: editTeacher.title,
      discipline: editTeacher.discipline,
      research_interests: editTeacher.research_interests,
      bio: editTeacher.bio,
      h_index: editTeacher.h_index,
      is_active: editTeacher.is_active,
      research_direction: toResearchDirection(editTeacher.research_interests || ''),
    })

    if (currentUser.value?.id === editTeacher.id) {
      currentUser.value = setSessionUser(response.data)
    }

    ElMessage.success('教师资料已更新')
    editDialogVisible.value = false
    await Promise.all([loadTeachers(), loadManagementSummary()])
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '教师资料更新失败'))
  }
}

const handleSelectionChange = (rows: TeacherRecord[]) => {
  selectedTeacherIds.value = rows.map(item => item.id)
}

const toggleTeacherStatus = async (teacher: TeacherRecord, nextActive: boolean) => {
  try {
    const response = await axios.patch<TeacherAccountResponse>(`/api/users/teachers/${teacher.id}/`, {
      is_active: nextActive,
    })
    if (currentUser.value?.id === teacher.id) {
      currentUser.value = setSessionUser(response.data)
    }
    ElMessage.success(nextActive ? '教师账户已恢复启用' : '教师账户已停用')
    await Promise.all([loadTeachers(), loadManagementSummary()])
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '账户状态更新失败'))
  }
}

const executeBulkAction = async (action: 'activate' | 'deactivate' | 'reset_password') => {
  if (!hasSelection.value) {
    ElMessage.warning('请先勾选至少一条教师账户记录。')
    return
  }

  const confirmTitle =
    action === 'activate'
      ? '批量恢复启用'
      : action === 'deactivate'
        ? '批量停用'
        : '批量重置密码'
  const confirmMessage =
    action === 'activate'
      ? `确认批量恢复 ${selectedTeacherIds.value.length} 个教师账户吗？`
      : action === 'deactivate'
        ? `确认批量停用 ${selectedTeacherIds.value.length} 个教师账户吗？停用后这些教师将无法继续登录。`
        : `确认批量重置 ${selectedTeacherIds.value.length} 个教师账户密码吗？重置后系统会提示教师尽快修改临时密码。`

  await ElMessageBox.confirm(confirmMessage, confirmTitle, { type: action === 'deactivate' ? 'warning' : 'info' })

  bulkLoading.value = true
  try {
    const response = await axios.post<TeacherBulkActionResponse>('/api/users/teachers/bulk-actions/', {
      action,
      user_ids: selectedTeacherIds.value,
    })
    lastBulkResult.value = response.data
    managementSummary.value = response.data.management_summary
    ElMessage.success(response.data.detail)

    if (action === 'reset_password' && response.data.temporary_password) {
      await ElMessageBox.alert(
        [
          `本次处理账户数：${response.data.processed_count}`,
          `临时密码：${response.data.temporary_password}`,
          `恢复提示：${response.data.recovery_notice}`,
        ].join('<br />'),
        '批量密码重置完成',
        {
          confirmButtonText: '我知道了',
          dangerouslyUseHTMLString: true,
        },
      )
    }

    selectedTeacherIds.value = []
    teacherTableRef.value?.clearSelection()
    await loadTeachers()
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '批量账户操作失败'))
  } finally {
    bulkLoading.value = false
  }
}

const resetPassword = async (teacher: TeacherRecord) => {
  await ElMessageBox.confirm(
    `确认将 ${teacher.real_name || teacher.username} 的密码重置为默认密码吗？重置后系统会提示该教师尽快修改密码。`,
    '重置确认',
    {
      type: 'warning',
    },
  )

  resetLoadingId.value = teacher.id
  try {
    const response = await axios.post<TeacherPasswordResetResponse>(`/api/users/teachers/${teacher.id}/reset-password/`)
    await ElMessageBox.alert(
      [
        `临时密码：${response.data.temporary_password}`,
        `账户角色：${response.data.role_label}`,
        `安全提示：${response.data.security_notice}`,
      ].join('<br />'),
      '密码已重置',
      {
        confirmButtonText: '我知道了',
        dangerouslyUseHTMLString: true,
      },
    )
    await Promise.all([loadTeachers(), loadManagementSummary()])
  } catch (error: any) {
    const detail = error?.response?.status === 403
      ? resolvePermissionDeniedMessage(error?.response?.data?.detail)
      : resolveApiErrorMessage(error, '密码重置失败')
    ElMessage.error(detail)
  } finally {
    resetLoadingId.value = null
  }
}

const handleMoreAction = async (teacher: TeacherRecord, action: TeacherMoreAction) => {
  if (action === 'profile') {
    previewTeacherId.value = teacher.id
    previewTeacherName.value = teacher.real_name || teacher.username
    radarPreviewVisible.value = true
    return
  }

  if (action === 'toggle-status') {
    await toggleTeacherStatus(teacher, !teacher.is_active)
    return
  }

  await resetPassword(teacher)
}

const handleMoreCommand = async (teacher: TeacherRecord, command: string | number | object) => {
  if (command === 'profile' || command === 'toggle-status' || command === 'reset-password') {
    await handleMoreAction(teacher, command)
  }
}

const rowClassName = ({ row }: { row: TeacherRecord }) => {
  if (focusTeacherId.value && row.id === focusTeacherId.value) {
    return 'focus-row'
  }
  return ''
}

const focusTeacherRow = () => {
  if (!focusTeacherId.value) return
  const target = teachers.value.find(item => item.id === focusTeacherId.value)
  if (!target) return

  teacherTableRef.value?.setCurrentRow(target)

  if (route.query.action === 'edit') {
    openEditDialog(target)
  }
}

watch(
  () => route.query.focus,
  async () => {
    await nextTick()
    focusTeacherRow()
  },
)

onMounted(async () => {
  const adminUser = await ensureAdminUser()
  if (!adminUser) return
  await loadTeachers()
  if (isSystemAdmin.value) {
    await loadManagementSummary()
  }
})
</script>

<template>
  <div class="teacher-management-page workspace-page">
    <section class="hero-shell">
      <div class="hero-main workspace-hero workspace-hero--brand">
        <div class="hero-copy-block">
          <p class="eyebrow workspace-hero__eyebrow">Teacher Management</p>
          <h1 class="workspace-hero__title">教师管理</h1>
          <p class="hero-copy workspace-hero__text">
            面向管理员统一维护教师账号、角色身份、启停状态、密码生命周期和批量账户操作，保持账户生命周期清晰可控。
          </p>
        </div>
      </div>
    </section>

    <div
      v-if="currentUser && !checkedAdmin"
      class="workspace-status-result workspace-content-shell"
    >
      <el-result
        icon="warning"
        title="当前页面仅限管理员使用"
        sub-title="教师个人基础档案请前往“基础档案”页面维护。"
      />
    </div>

    <template v-else>
      <section v-if="showSummaryGrid" class="summary-grid">
        <el-card class="summary-card workspace-surface-card" shadow="never">
          <span class="summary-label">教师账户总量</span>
          <strong class="summary-value">{{ managementSummary.total_count }}</strong>
        </el-card>
        <el-card class="summary-card workspace-surface-card" shadow="never">
          <span class="summary-label">当前启用</span>
          <strong class="summary-value">{{ managementSummary.active_count }}</strong>
        </el-card>
        <el-card class="summary-card workspace-surface-card" shadow="never">
          <span class="summary-label">当前停用</span>
          <strong class="summary-value">{{ managementSummary.inactive_count }}</strong>
        </el-card>
        <el-card class="summary-card workspace-surface-card" shadow="never">
          <span class="summary-label">待修改密码</span>
          <strong class="summary-value">{{ managementSummary.password_reset_required_count }}</strong>
        </el-card>
      </section>

      <section
        v-if="showManagementShell"
        class="management-shell"
        :class="{ 'management-shell--single': !showCreateCard || !showListCard }"
      >
        <el-card v-if="showCreateCard" class="create-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="card-header workspace-section-head">
              <span>{{ createCardTitle }}</span>
              <el-tag type="warning" effect="plain">{{ isSystemAdmin ? '系统管理员入口' : '学院管理员入口' }}</el-tag>
            </div>
          </template>

          <el-alert
            :title="createRuleNotice"
            type="info"
            :closable="false"
            show-icon
          />

          <el-form ref="createFormRef" :model="createTeacherForm" :rules="createRules" label-position="top" class="form-block">
            <div class="grid two-cols">
              <el-form-item label="六位工号" prop="employee_id">
                <el-input v-model="createTeacherForm.employee_id" maxlength="6" />
              </el-form-item>
              <el-form-item label="教师姓名" prop="real_name">
                <el-input v-model="createTeacherForm.real_name" />
              </el-form-item>
            </div>

            <div class="grid two-cols">
              <el-form-item :label="createDepartmentLabel" prop="department">
                <el-input v-model="createTeacherForm.department" :disabled="isCollegeAdmin" />
              </el-form-item>
              <el-form-item label="职称" prop="title">
                <el-input v-model="createTeacherForm.title" />
              </el-form-item>
            </div>

            <div class="grid two-cols">
              <el-form-item label="学科方向">
                <el-input v-model="createTeacherForm.discipline" />
              </el-form-item>
              <el-form-item label="H-index">
                <el-input-number v-model="createTeacherForm.h_index" :min="0" style="width: 100%" />
              </el-form-item>
            </div>

            <el-form-item label="研究兴趣">
              <el-input v-model="createTeacherForm.research_interests" placeholder="多个兴趣可用逗号分隔" />
            </el-form-item>

            <el-form-item label="个人简介">
              <el-input v-model="createTeacherForm.bio" type="textarea" :rows="4" />
            </el-form-item>

            <div class="grid two-cols">
              <el-form-item label="登录密码" prop="password">
                <el-input v-model="createTeacherForm.password" type="password" show-password />
              </el-form-item>
              <el-form-item label="确认密码" prop="confirm_password">
                <el-input
                  v-model="createTeacherForm.confirm_password"
                  type="password"
                  show-password
                  @keyup.enter="createTeacher"
                />
              </el-form-item>
            </div>

            <div class="actions">
              <el-button @click="resetCreateForm">重置</el-button>
              <el-button type="primary" :loading="createLoading" @click="createTeacher">{{ createButtonText }}</el-button>
            </div>
          </el-form>

          <el-result
            v-if="lastCreatedAccount"
            icon="success"
            :title="createResultTitle"
            :sub-title="createResultSubtitle"
          >
            <template #extra>
              <div class="result-box">
                <p>工号(ID)：{{ lastCreatedAccount.employee_id }}</p>
                <p>登录账号：{{ lastCreatedAccount.username }}</p>
                <p>初始密码：{{ lastCreatedAccount.initial_password }}</p>
              </div>
            </template>
          </el-result>
        </el-card>

        <el-card v-if="showListCard" class="list-card workspace-surface-card" shadow="never">
          <template #header>
            <div class="card-header workspace-section-head">
              <span>教师账户总览</span>
              <el-tag type="success" effect="plain">{{ teachers.length }} 条记录</el-tag>
            </div>
          </template>

          <el-alert v-if="isSystemAdmin" :title="managementSummary.recovery_guidance" type="info" :closable="false" show-icon />
          <el-alert
            v-if="isSystemAdmin"
            :title="managementSummary.future_extension_hint"
            type="warning"
            :closable="false"
            show-icon
            class="summary-guidance"
          />
          <el-alert
            v-else
            title="当前仅展示本学院范围内的教师账户信息。"
            type="info"
            :closable="false"
            show-icon
          />

          <div class="toolbar-row">
            <div class="toolbar-filters">
              <el-input v-model="keywordFilter" placeholder="按工号、姓名、院系筛选" clearable />
              <el-select v-model="accountStatusFilter">
                <el-option label="全部账户状态" value="all" />
                <el-option label="仅看已启用" value="active" />
                <el-option label="仅看已停用" value="inactive" />
              </el-select>
              <el-select v-model="passwordStatusFilter">
                <el-option label="全部密码状态" value="all" />
                <el-option label="仅看待修改密码" value="pending" />
                <el-option label="仅看状态正常" value="stable" />
              </el-select>
            </div>

            <div v-if="canManageTeacherAccounts" class="toolbar-actions">
              <el-button :disabled="!hasSelection" :loading="bulkLoading" @click="executeBulkAction('activate')">批量恢复</el-button>
              <el-button :disabled="!hasSelection" :loading="bulkLoading" @click="executeBulkAction('deactivate')">批量停用</el-button>
              <el-button type="warning" :disabled="!hasSelection" :loading="bulkLoading" @click="executeBulkAction('reset_password')">
                批量重置密码
              </el-button>
            </div>
          </div>

          <el-result
            v-if="lastBulkResult"
            icon="success"
            title="最近一次批量操作结果"
            :sub-title="`${lastBulkResult.detail} 已处理 ${lastBulkResult.processed_count} 个账户，跳过 ${lastBulkResult.skipped_count} 个账户。`"
          >
            <template #extra>
              <div class="result-box">
                <p>操作类型：{{ lastBulkResult.action }}</p>
                <p v-if="lastBulkResult.temporary_password">临时密码：{{ lastBulkResult.temporary_password }}</p>
                <p>{{ lastBulkResult.recovery_notice }}</p>
              </div>
            </template>
          </el-result>
          <el-table
            ref="teacherTableRef"
            v-loading="listLoading"
            :data="filteredTeachers"
            class="teacher-overview-table"
            stripe
            highlight-current-row
            :row-class-name="rowClassName"
            empty-text="暂无教师记录"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="36" />
            <el-table-column label="工号/登录账号" width="152">
              <template #default="{ row }">
                <div class="account-identity">
                  <div class="account-primary">{{ row.employee_id }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="real_name" label="姓名" width="88" />
            <el-table-column label="身份" width="88">
              <template #default="{ row }">
                <el-tag effect="plain" type="primary">{{ resolveRoleLabel(row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="department" label="所属学院" width="118" />
            <el-table-column prop="title" label="职称" width="80" />
            <el-table-column prop="discipline" label="学科方向" width="136" />
            <el-table-column label="账号状态" width="96">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" effect="plain">
                  {{ row.account_status_label || (row.is_active ? '启用' : '停用') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="密码状态" width="108">
              <template #default="{ row }">
                <el-tag :type="row.password_reset_required ? 'warning' : 'success'" effect="plain">
                  {{ row.password_status_label || (row.password_reset_required ? '待修改密码' : '状态正常') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="132">
              <template #default="{ row }">
                <div class="table-actions">
                  <template v-if="canManageTeacherAccounts">
                    <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                    <el-dropdown trigger="click" @command="handleMoreCommand(row, $event)">
                      <el-button link type="primary" :loading="resetLoadingId === row.id">更多</el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="profile">查看画像</el-dropdown-item>
                          <el-dropdown-item command="toggle-status">
                            {{ row.is_active ? '停用账户' : '恢复启用' }}
                          </el-dropdown-item>
                          <el-dropdown-item command="reset-password">重置密码</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </template>
                  <el-button v-else link type="primary" @click="handleMoreAction(row, 'profile')">查看画像</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </section>
    </template>

    <el-dialog v-model="editDialogVisible" title="编辑教师资料" width="720px">
      <el-form ref="editFormRef" :model="editTeacher" :rules="editRules" label-position="top">
        <div class="grid two-cols">
          <el-form-item label="工号(ID)">
            <el-input :model-value="editTeacher.employee_id" disabled />
          </el-form-item>
          <el-form-item label="登录账号">
            <el-input :model-value="editTeacher.username" disabled />
          </el-form-item>
        </div>

        <div class="grid two-cols">
          <el-form-item label="姓名" prop="real_name">
            <el-input v-model="editTeacher.real_name" />
          </el-form-item>
          <el-form-item label="职称" prop="title">
            <el-input v-model="editTeacher.title" />
          </el-form-item>
        </div>

        <div class="grid two-cols">
          <el-form-item label="所属学院" prop="department">
            <el-input v-model="editTeacher.department" />
          </el-form-item>
          <el-form-item label="学科方向">
            <el-input v-model="editTeacher.discipline" />
          </el-form-item>
        </div>

        <div class="grid two-cols">
          <el-form-item label="H-index">
            <el-input-number v-model="editTeacher.h_index" :min="0" style="width: 100%" />
          </el-form-item>
          <el-form-item label="账户状态">
            <el-switch v-model="editTeacher.is_active" inline-prompt active-text="启用" inactive-text="停用" />
          </el-form-item>
        </div>

        <el-form-item label="研究兴趣">
          <el-input v-model="editTeacher.research_interests" placeholder="多个兴趣可用逗号分隔" />
        </el-form-item>

        <el-alert
          :title="buildPasswordSecurityNotice(editTeacher)"
          :type="editTeacher.password_reset_required ? 'warning' : 'info'"
          :closable="false"
          show-icon
        />

        <el-alert
          :title="buildAccountLifecycleHint(editTeacher)"
          :type="editTeacher.is_active ? 'info' : 'error'"
          :closable="false"
          show-icon
        />

        <el-form-item label="个人简介">
          <el-input v-model="editTeacher.bio" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-actions">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveTeacherEdit">保存修改</el-button>
        </div>
      </template>
    </el-dialog>

    <TeacherRadarPreviewDialog
      v-model="radarPreviewVisible"
      :teacher-id="previewTeacherId"
      :teacher-name="previewTeacherName"
    />
  </div>
</template>

<style scoped>
.teacher-management-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.12), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.12), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.hero-shell {
  max-width: 1180px;
  margin: 0 auto 22px;
}

.hero-main {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 28px 32px;
  border-radius: 26px;
  background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 62%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.14);
}

.eyebrow {
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 12px;
}

h1 {
  margin: 0;
}

.hero-copy-block {
  display: grid;
  gap: 12px;
}

.hero-copy {
  margin: 0;
  max-width: 760px;
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.8;
}

.card-header,
.actions,
.dialog-actions,
.toolbar-row,
.toolbar-filters,
.toolbar-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.summary-grid {
  max-width: 1180px;
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  border: none;
  border-radius: 22px;
  background: color-mix(in srgb, var(--panel-bg) 92%, var(--brand-primary) 8%);
  box-shadow: var(--workspace-shadow);
}

.summary-label {
  display: block;
  color: var(--el-text-color-secondary);
  margin-bottom: 10px;
}

.summary-value {
  font-size: 30px;
  color: var(--el-text-color-primary);
}

.management-shell {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
  gap: 20px;
}

.management-shell--single {
  grid-template-columns: 1fr;
}

.create-card,
.list-card {
  border: none;
  border-radius: 24px;
  background: var(--panel-bg);
  box-shadow: var(--workspace-shadow);
}

.form-block {
  margin-top: 18px;
}

.grid {
  display: grid;
  gap: 16px;
}

.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.actions {
  justify-content: center;
  margin-top: 10px;
}

.toolbar-row {
  justify-content: space-between;
  margin: 18px 0;
  align-items: stretch;
}

.toolbar-filters {
  flex: 1;
}

.toolbar-filters :deep(.el-input),
.toolbar-filters :deep(.el-select) {
  width: 100%;
  max-width: 260px;
}

.toolbar-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.result-box {
  margin-bottom: 16px;
  padding: 16px 20px;
  border-radius: 16px;
  background: var(--surface-2);
  color: var(--el-text-color-primary);
  text-align: left;
}

.summary-guidance {
  margin-top: 12px;
}

.result-box p,
.security-copy {
  margin: 8px 0;
  line-height: 1.6;
}

.account-identity {
  display: grid;
  gap: 2px;
  line-height: 1.5;
  justify-items: center;
  text-align: center;
}

.account-primary {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.account-secondary {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  white-space: nowrap;
}

.teacher-overview-table :deep(th.el-table__cell),
.teacher-overview-table :deep(td.el-table__cell) {
  padding-top: 8px;
  padding-bottom: 8px;
}

.teacher-overview-table :deep(th.el-table__cell > .cell),
.teacher-overview-table :deep(td.el-table__cell > .cell) {
  padding-left: 1px;
  padding-right: 1px;
  text-align: center;
}

.teacher-overview-table :deep(.el-table__header-wrapper .cell) {
  color: var(--el-text-color-primary);
}

.teacher-overview-table :deep(.el-table__body-wrapper .cell) {
  color: var(--el-text-color-primary);
}

.teacher-overview-table :deep(.el-table__fixed-right th.el-table__cell > .cell),
.teacher-overview-table :deep(.el-table__fixed-right td.el-table__cell > .cell) {
  padding-left: 0;
  padding-right: 0;
}

.teacher-overview-table :deep(.el-table__fixed-right .el-button + .el-button) {
  margin-left: 0;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(1)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(1)) {
  width: 28px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(2)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(2)) {
  width: 152px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(3)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(3)) {
  width: 88px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(4)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(4)) {
  width: 88px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(5)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(5)) {
  width: 118px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(6)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(6)) {
  width: 80px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(7)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(7)) {
  width: 136px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(8)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(8)) {
  width: 96px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(9)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(9)) {
  width: 108px !important;
}

.teacher-overview-table :deep(.el-table__header colgroup col:nth-child(10)),
.teacher-overview-table :deep(.el-table__body colgroup col:nth-child(10)) {
  width: 132px !important;
}

.security-secondary {
  color: var(--el-text-color-secondary);
}

:deep(.focus-row) {
  --el-table-tr-bg-color: rgba(37, 99, 235, 0.08);
}

.dialog-actions {
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .teacher-management-page {
    padding: 16px;
  }

  .hero-main,
  .hero-actions,
  .summary-grid,
  .two-cols,
  .card-header,
  .dialog-actions,
  .toolbar-row,
  .toolbar-filters,
  .toolbar-actions {
    flex-direction: column;
    grid-template-columns: 1fr;
    align-items: stretch;
  }
}
</style>
