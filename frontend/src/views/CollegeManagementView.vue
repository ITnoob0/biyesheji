<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { CollegeListResponse, CollegeRecordResponse } from '../types/users'
import { resolveApiErrorMessage } from '../utils/authPresentation.js'

const colleges = ref<CollegeRecordResponse[]>([])
const loading = ref(false)
const creating = ref(false)
const deletingId = ref<number | null>(null)
const createFormRef = ref<FormInstance>()
const createForm = reactive({
  name: '',
})

const createRules: FormRules = {
  name: [{ required: true, message: '请填写学院名称', trigger: 'blur' }],
}

const activeColleges = computed(() => colleges.value.filter(item => item.is_active))
const totalAccountCount = computed(() => activeColleges.value.reduce((sum, item) => sum + item.account_count, 0))
const totalTeacherCount = computed(() => activeColleges.value.reduce((sum, item) => sum + item.teacher_count, 0))
const totalCollegeAdminCount = computed(() => activeColleges.value.reduce((sum, item) => sum + item.college_admin_count, 0))

const loadColleges = async () => {
  loading.value = true
  try {
    const response = await axios.get<CollegeListResponse>('/api/users/colleges/')
    colleges.value = response.data.records ?? []
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '学院目录加载失败'))
  } finally {
    loading.value = false
  }
}

const createCollege = async () => {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await axios.post('/api/users/colleges/', {
      name: createForm.name.trim(),
    })
    ElMessage.success('学院已新增')
    createForm.name = ''
    createFormRef.value.clearValidate()
    await loadColleges()
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '学院新增失败'))
  } finally {
    creating.value = false
  }
}

const deleteCollege = async (college: CollegeRecordResponse) => {
  if (college.account_count > 0) {
    ElMessage.warning(`该学院下已有 ${college.account_count} 个账号，请先迁移相关学院管理员和教师账号。`)
    return
  }

  await ElMessageBox.confirm(`确认删除“${college.name}”吗？删除后该学院不能再用于注册或创建账号。`, '删除学院', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })

  deletingId.value = college.id
  try {
    await axios.delete(`/api/users/colleges/${college.id}/`)
    ElMessage.success('学院已删除')
    await loadColleges()
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '学院删除失败'))
  } finally {
    deletingId.value = null
  }
}

onMounted(loadColleges)
</script>

<template>
  <div class="college-management-page workspace-page">
    <section class="hero-shell">
      <div class="hero-main workspace-hero workspace-hero--brand">
        <div class="hero-copy-block">
          <p class="eyebrow workspace-hero__eyebrow">College Directory</p>
          <h1 class="workspace-hero__title">学院管理</h1>
          <p class="hero-copy workspace-hero__text">
            维护系统可用学院目录，学院管理员与教师账号只能归属到已存在学院。
          </p>
        </div>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card workspace-surface-card" shadow="never">
        <span class="summary-label">学院数量</span>
        <strong class="summary-value">{{ activeColleges.length }}</strong>
      </el-card>
      <el-card class="summary-card workspace-surface-card" shadow="never">
        <span class="summary-label">教师账号</span>
        <strong class="summary-value">{{ totalTeacherCount }}</strong>
      </el-card>
      <el-card class="summary-card workspace-surface-card" shadow="never">
        <span class="summary-label">学院管理员</span>
        <strong class="summary-value">{{ totalCollegeAdminCount }}</strong>
      </el-card>
      <el-card class="summary-card workspace-surface-card" shadow="never">
        <span class="summary-label">目录内账号</span>
        <strong class="summary-value">{{ totalAccountCount }}</strong>
      </el-card>
    </section>

    <section class="content-shell">
      <el-card class="create-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="card-header workspace-section-head">
            <span>新增学院</span>
          </div>
        </template>

        <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top" class="create-form">
          <el-form-item label="学院名称" prop="name" required>
            <el-input v-model="createForm.name" placeholder="请输入学院全称" @keyup.enter="createCollege" />
          </el-form-item>
          <el-button type="primary" :loading="creating" @click="createCollege">新增学院</el-button>
        </el-form>
      </el-card>

      <el-card class="list-card workspace-surface-card" shadow="never">
        <template #header>
          <div class="card-header workspace-section-head">
            <span>学院目录</span>
            <el-button plain size="small" :loading="loading" @click="loadColleges">刷新</el-button>
          </div>
        </template>

        <el-table v-loading="loading" :data="activeColleges" stripe empty-text="暂无学院记录">
          <el-table-column prop="name" label="学院名称" min-width="220" />
          <el-table-column prop="teacher_count" label="教师账号" width="110" />
          <el-table-column prop="college_admin_count" label="学院管理员" width="120" />
          <el-table-column prop="account_count" label="账号合计" width="100" />
          <el-table-column label="状态" width="96">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
                {{ row.is_active ? '可用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="108">
            <template #default="{ row }">
              <el-button
                link
                type="danger"
                :disabled="row.account_count > 0"
                :loading="deletingId === row.id"
                @click="deleteCollege(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.college-management-page {
  min-height: 100vh;
  padding: 28px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.hero-shell,
.summary-grid,
.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.hero-shell {
  margin-bottom: 22px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.summary-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 92px;
}

.summary-label {
  color: #64748b;
  font-size: 14px;
}

.summary-value {
  color: #0f172a;
  font-size: 28px;
  line-height: 1;
}

.content-shell {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  gap: 18px;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

@media (max-width: 960px) {
  .summary-grid,
  .content-shell {
    grid-template-columns: 1fr;
  }

  .college-management-page {
    padding: 18px;
  }
}
</style>
