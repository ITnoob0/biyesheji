<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules, TableInstance } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { ensureSessionUserContext, setSessionUser, type SessionUser } from '../utils/sessionAuth'

interface TeacherRecord extends SessionUser {
  employee_id: number
  discipline?: string | null
  research_interests?: string | null
  h_index?: number
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

const router = useRouter()
const route = useRoute()
const teacherTableRef = ref<TableInstance>()

const currentUser = ref<SessionUser | null>(null)
const teachers = ref<TeacherRecord[]>([])
const createLoading = ref(false)
const listLoading = ref(false)
const resetLoadingId = ref<number | null>(null)
const lastCreatedAccount = ref<{ employee_id: number; username: string; initial_password?: string } | null>(null)
const editDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()

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
  research_direction: [],
  bio: '',
  discipline: '',
  research_interests: '',
  h_index: 0,
  is_active: true,
  is_admin: false,
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

const checkedAdmin = computed(() => Boolean(currentUser.value?.is_admin))
const focusTeacherId = computed(() => Number(route.query.focus || 0))

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
}

const ensureAdminUser = async (): Promise<SessionUser | null> => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return null
  }

  if (!sessionUser.is_admin) {
    router.replace({ name: 'dashboard' })
    return null
  }

  currentUser.value = sessionUser
  return sessionUser
}

const loadTeachers = async () => {
  listLoading.value = true
  try {
    const response = await axios.get('/api/users/teachers/')
    teachers.value = response.data
    await nextTick()
    focusTeacherRow()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '教师列表加载失败')
  } finally {
    listLoading.value = false
  }
}

const createTeacher = async () => {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  createLoading.value = true
  try {
    const response = await axios.post('/api/users/teachers/', {
      ...createTeacherForm,
      research_direction: toResearchDirection(createTeacherForm.research_interests),
    })

    lastCreatedAccount.value = {
      employee_id: response.data.employee_id,
      username: response.data.username,
      initial_password: response.data.initial_password,
    }

    ElMessage.success('教师账号创建成功')
    resetCreateForm()
    await loadTeachers()
  } catch (error: any) {
    const detail = error?.response?.data
    if (detail && typeof detail === 'object') {
      const firstError = Object.values(detail)[0]
      ElMessage.error(Array.isArray(firstError) ? String(firstError[0]) : String(firstError))
    } else {
      ElMessage.error('教师账号创建失败')
    }
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
    const response = await axios.patch(`/api/users/teachers/${editTeacher.id}/`, {
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
      setSessionUser(response.data)
      currentUser.value = response.data
    }

    ElMessage.success('教师资料已更新')
    editDialogVisible.value = false
    await loadTeachers()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '教师资料更新失败')
  }
}

const resetPassword = async (teacher: TeacherRecord) => {
  await ElMessageBox.confirm(`确认将 ${teacher.real_name || teacher.username} 的密码重置为默认密码吗？`, '重置确认', {
    type: 'warning',
  })

  resetLoadingId.value = teacher.id
  try {
    const response = await axios.post(`/api/users/teachers/${teacher.id}/reset-password/`)
    ElMessage.success(`已将 ${teacher.real_name || teacher.username} 的密码重置为 ${response.data.password}`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '密码重置失败')
  } finally {
    resetLoadingId.value = null
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
})
</script>

<template>
  <div class="teacher-management-page">
    <section class="hero-shell">
      <div class="hero-main">
        <div class="hero-copy-block">
          <p class="eyebrow">Teacher Management</p>
          <h1>教师管理</h1>
          <p class="hero-copy">
            面向管理员统一维护教师账号、基础资料与密码状态，保持教师画像主链路稳定可用。
          </p>
          <div class="hero-tags">
            <span class="hero-tag">管理员入口</span>
            <span class="hero-tag">账号与档案维护</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button type="primary" @click="router.push('/dashboard')">返回画像主页</el-button>
          <el-button plain @click="loadTeachers">刷新教师数据</el-button>
        </div>
      </div>
    </section>

    <el-result
      v-if="currentUser && !checkedAdmin"
      icon="warning"
      title="当前页面仅限管理员使用"
      sub-title="教师个人基础档案请前往“编辑基础档案”页面维护。"
    />

    <template v-else>
      <section class="management-shell">
        <el-card class="create-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>创建教师账号</span>
              <el-tag type="warning" effect="plain">管理员入口</el-tag>
            </div>
          </template>

          <el-alert
            title="规则：工号必须是 6 位数字，工号将直接作为教师登录账号，管理员创建时需要同步设置初始密码。"
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
              <el-form-item label="所属学院" prop="department">
                <el-input v-model="createTeacherForm.department" />
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
                <el-input v-model="createTeacherForm.confirm_password" type="password" show-password @keyup.enter="createTeacher" />
              </el-form-item>
            </div>

            <div class="actions">
              <el-button @click="resetCreateForm">重置</el-button>
              <el-button type="primary" :loading="createLoading" @click="createTeacher">创建账号</el-button>
            </div>
          </el-form>

          <el-result
            v-if="lastCreatedAccount"
            icon="success"
            title="最新创建结果"
            sub-title="以下登录信息可直接交付给对应教师。"
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

        <el-card class="list-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>教师账号总览</span>
              <el-tag type="success" effect="plain">{{ teachers.length }} 条记录</el-tag>
            </div>
          </template>

          <el-table
            ref="teacherTableRef"
            v-loading="listLoading"
            :data="teachers"
            stripe
            highlight-current-row
            :row-class-name="rowClassName"
            empty-text="暂无教师记录"
          >
            <el-table-column prop="employee_id" label="工号(ID)" width="120" />
            <el-table-column prop="username" label="登录账号" width="140" />
            <el-table-column prop="real_name" label="姓名" width="120" />
            <el-table-column prop="department" label="所属学院" min-width="160" />
            <el-table-column prop="title" label="职称" width="120" />
            <el-table-column prop="discipline" label="学科方向" min-width="160" />
            <el-table-column prop="h_index" label="H-index" width="100" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                <el-button link type="success" @click="router.push(`/profile/${row.id}`)">查看画像</el-button>
                <el-button link type="warning" :loading="resetLoadingId === row.id" @click="resetPassword(row)">
                  重置密码
                </el-button>
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
          <el-form-item label="账号状态">
            <el-switch v-model="editTeacher.is_active" inline-prompt active-text="启用" inactive-text="停用" />
          </el-form-item>
        </div>

        <el-form-item label="研究兴趣">
          <el-input v-model="editTeacher.research_interests" placeholder="多个兴趣可用逗号分隔" />
        </el-form-item>

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
  padding: 0;
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

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
}

.hero-actions,
.card-header,
.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.management-shell {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.create-card,
.list-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
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

:deep(.focus-row) {
  --el-table-tr-bg-color: rgba(37, 99, 235, 0.08);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .teacher-management-page {
    padding: 16px;
  }

  .hero-main,
  .hero-actions,
  .two-cols {
    flex-direction: column;
    grid-template-columns: 1fr;
    align-items: stretch;
  }
}
</style>
