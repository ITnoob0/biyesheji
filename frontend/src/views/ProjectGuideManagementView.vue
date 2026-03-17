<template>
  <div class="guide-page">
    <section class="hero-panel">
      <div>
        <p class="eyebrow">Guide Management</p>
        <h1>项目指南管理</h1>
        <p class="hero-text">面向管理员维护项目指南基础数据，为后续推荐提供可解释的数据来源。</p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button type="primary" :loading="loading" @click="loadGuides">刷新列表</el-button>
      </div>
    </section>

    <el-result
      v-if="checkedUser && !checkedUser.is_admin"
      icon="warning"
      title="当前页面仅限管理员使用"
      sub-title="教师账号可前往“项目推荐”页面查看个性化推荐结果。"
    />

    <div v-else class="guide-grid content-shell">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>{{ editingId ? '编辑项目指南' : '新增项目指南' }}</span>
            <el-tag type="info" effect="plain">当前阶段扩展能力</el-tag>
          </div>
        </template>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="指南标题" prop="title">
            <el-input v-model="form.title" placeholder="请输入项目指南标题" />
          </el-form-item>
          <div class="double-grid">
            <el-form-item label="发布单位" prop="issuing_agency">
              <el-input v-model="form.issuing_agency" placeholder="如 省教育厅、科技部" />
            </el-form-item>
            <el-form-item label="指南级别" prop="guide_level">
              <el-select v-model="form.guide_level" style="width: 100%">
                <el-option v-for="item in guideLevelOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>
          <div class="double-grid">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width: 100%">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="截止时间">
              <el-date-picker v-model="form.application_deadline" value-format="YYYY-MM-DD" type="date" style="width: 100%" />
            </el-form-item>
          </div>
          <el-form-item label="指南摘要" prop="summary">
            <el-input v-model="form.summary" type="textarea" :rows="4" placeholder="概述指南主题、支持方向和申报重点" />
          </el-form-item>
          <el-form-item label="主题关键词">
            <el-input v-model="form.targetKeywordsInput" placeholder="多个关键词请用逗号、顿号或换行分隔" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="面向学科/院系">
            <el-input v-model="form.targetDisciplinesInput" placeholder="如 教育数据智能、教育技术学院" type="textarea" :rows="2" />
          </el-form-item>
          <div class="double-grid">
            <el-form-item label="资助强度">
              <el-input v-model="form.support_amount" placeholder="如 20-30 万元" />
            </el-form-item>
            <el-form-item label="来源链接">
              <el-input v-model="form.source_url" placeholder="可选，填写官方通知链接" />
            </el-form-item>
          </div>
          <el-form-item label="申报要求">
            <el-input v-model="form.eligibility_notes" type="textarea" :rows="3" placeholder="如 近三年相关成果、团队基础等" />
          </el-form-item>
          <div class="actions">
            <el-button @click="resetForm">重置</el-button>
            <el-button type="primary" :loading="submitting" @click="submitForm">{{ editingId ? '保存修改' : '创建指南' }}</el-button>
          </div>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header card-header-wrap">
            <span>指南列表</span>
            <div class="toolbar">
              <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width: 140px" @change="loadGuides">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-input v-model="searchKeyword" placeholder="搜索标题或发布单位" clearable style="width: 220px" @keyup.enter="loadGuides" />
              <el-button @click="loadGuides">查询</el-button>
            </div>
          </div>
        </template>

        <el-table :data="guides" v-loading="loading" empty-text="暂无项目指南">
          <el-table-column prop="title" label="指南标题" min-width="230" />
          <el-table-column prop="issuing_agency" label="发布单位" min-width="150" />
          <el-table-column prop="guide_level_display" label="级别" width="110" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'OPEN' ? 'success' : row.status === 'DRAFT' ? 'info' : 'warning'">
                {{ row.status_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="application_deadline" label="截止时间" width="130" />
          <el-table-column label="主题匹配" min-width="220">
            <template #default="{ row }">
              <div class="tag-list">
                <el-tag v-for="tag in row.target_keywords.slice(0, 4)" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="startEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="removeGuide(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type { GuideLevel, GuideStatus, ProjectGuideRecord } from './project-guides/types'

const guideEndpoint = '/api/project-guides/'
const router = useRouter()

const guideLevelOptions: Array<{ label: string; value: GuideLevel }> = [
  { label: '国家级', value: 'NATIONAL' },
  { label: '省部级', value: 'PROVINCIAL' },
  { label: '市厅级', value: 'MUNICIPAL' },
  { label: '企业合作', value: 'ENTERPRISE' },
]

const statusOptions: Array<{ label: string; value: GuideStatus }> = [
  { label: '草稿', value: 'DRAFT' },
  { label: '申报中', value: 'OPEN' },
  { label: '已截止', value: 'CLOSED' },
]

const checkedUser = ref<SessionUser | null>(null)
const formRef = ref<FormInstance>()
const guides = ref<ProjectGuideRecord[]>([])
const loading = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const statusFilter = ref<GuideStatus | ''>('')
const searchKeyword = ref('')

const form = reactive({
  title: '',
  issuing_agency: '',
  guide_level: 'PROVINCIAL' as GuideLevel,
  status: 'OPEN' as GuideStatus,
  application_deadline: '',
  summary: '',
  targetKeywordsInput: '',
  targetDisciplinesInput: '',
  support_amount: '',
  eligibility_notes: '',
  source_url: '',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入指南标题', trigger: 'blur' }],
  issuing_agency: [{ required: true, message: '请输入发布单位', trigger: 'blur' }],
  guide_level: [{ required: true, message: '请选择指南级别', trigger: 'change' }],
  status: [{ required: true, message: '请选择指南状态', trigger: 'change' }],
  summary: [{ required: true, message: '请输入指南摘要', trigger: 'blur' }],
}

const parseTextList = (raw: string): string[] =>
  raw
    .split(/[\n,，、；;]+/)
    .map(item => item.trim())
    .filter(Boolean)

const resetForm = () => {
  formRef.value?.resetFields()
  editingId.value = null
  form.guide_level = 'PROVINCIAL'
  form.status = 'OPEN'
  form.application_deadline = ''
  form.targetKeywordsInput = ''
  form.targetDisciplinesInput = ''
  form.support_amount = ''
  form.eligibility_notes = ''
  form.source_url = ''
}

const loadGuides = async () => {
  loading.value = true
  try {
    const { data } = await axios.get<ProjectGuideRecord[]>(guideEndpoint, {
      params: {
        status: statusFilter.value || undefined,
        search: searchKeyword.value || undefined,
      },
    })
    guides.value = data
  } finally {
    loading.value = false
  }
}

const submitForm = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      title: form.title,
      issuing_agency: form.issuing_agency,
      guide_level: form.guide_level,
      status: form.status,
      application_deadline: form.application_deadline || null,
      summary: form.summary,
      target_keywords: parseTextList(form.targetKeywordsInput),
      target_disciplines: parseTextList(form.targetDisciplinesInput),
      support_amount: form.support_amount,
      eligibility_notes: form.eligibility_notes,
      source_url: form.source_url,
    }

    if (editingId.value) {
      await axios.patch(`${guideEndpoint}${editingId.value}/`, payload)
      ElMessage.success('项目指南已更新')
    } else {
      await axios.post(guideEndpoint, payload)
      ElMessage.success('项目指南已创建')
    }

    resetForm()
    await loadGuides()
  } finally {
    submitting.value = false
  }
}

const startEdit = (row: ProjectGuideRecord) => {
  editingId.value = row.id
  form.title = row.title
  form.issuing_agency = row.issuing_agency
  form.guide_level = row.guide_level
  form.status = row.status
  form.application_deadline = row.application_deadline || ''
  form.summary = row.summary
  form.targetKeywordsInput = row.target_keywords.join('，')
  form.targetDisciplinesInput = row.target_disciplines.join('，')
  form.support_amount = row.support_amount
  form.eligibility_notes = row.eligibility_notes
  form.source_url = row.source_url
}

const removeGuide = async (guideId: number) => {
  await ElMessageBox.confirm('删除后该指南将不再参与教师推荐，确认继续吗？', '删除确认', { type: 'warning' })
  await axios.delete(`${guideEndpoint}${guideId}/`)
  ElMessage.success('项目指南已删除')
  await loadGuides()
}

onMounted(async () => {
  checkedUser.value = await ensureSessionUserContext()
  if (checkedUser.value?.is_admin) {
    await loadGuides()
  }
})
</script>

<style scoped>
.guide-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
}

.hero-panel {
  max-width: 1180px;
  margin: 0 auto 22px;
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

.guide-grid :deep(.el-card) {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.hero-actions,
.card-header,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

h1 {
  margin: 0;
}

.hero-text {
  margin: 12px 0 0;
  max-width: 720px;
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.8;
}

.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.guide-grid {
  display: grid;
  grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
  gap: 20px;
  margin-top: 20px;
}

.double-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.card-header-wrap {
  align-items: flex-start;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1180px) {
  .guide-grid,
  .double-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .actions {
    display: flex;
  }
}

@media (max-width: 768px) {
  .guide-page {
    padding: 16px;
  }

  .hero-panel,
  .hero-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
