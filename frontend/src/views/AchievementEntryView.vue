<template>
  <div class="entry-page">
    <section class="hero-panel">
      <div>
        <p class="eyebrow">Paper Entry Workspace</p>
        <h1>论文录入与成果管理</h1>
        <p class="hero-copy">
          当前登录教师为 {{ teacherLabel }}。提交后会自动入库，并触发关键词提取和学术图谱同步。
        </p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button :loading="listLoading" @click="loadPapers">刷新论文列表</el-button>
      </div>
    </section>

    <div class="entry-layout">
      <el-card class="form-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>录入论文</span>
            <el-tag type="success">{{ teacherLabel }}</el-tag>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="entry-form"
        >
          <el-form-item label="论文标题" prop="title">
            <el-input v-model="form.title" placeholder="请输入论文标题" />
          </el-form-item>

          <el-form-item label="摘要" prop="abstract">
            <el-input
              v-model="form.abstract"
              type="textarea"
              :rows="5"
              placeholder="请输入论文摘要，摘要越完整，关键词提取效果越好"
            />
          </el-form-item>

          <div class="grid two-cols">
            <el-form-item label="发表日期" prop="date_acquired">
              <el-date-picker
                v-model="form.date_acquired"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="论文类型" prop="paper_type">
              <el-select v-model="form.paper_type" placeholder="请选择论文类型" style="width: 100%">
                <el-option label="期刊论文" value="JOURNAL" />
                <el-option label="会议论文" value="CONFERENCE" />
              </el-select>
            </el-form-item>
          </div>

          <div class="grid two-cols">
            <el-form-item label="期刊/会议名称" prop="journal_name">
              <el-input v-model="form.journal_name" placeholder="请输入期刊或会议名称" />
            </el-form-item>

            <el-form-item label="期刊级别">
              <el-input v-model="form.journal_level" placeholder="例如 SCI、EI、CCF-A" />
            </el-form-item>
          </div>

          <div class="grid two-cols">
            <el-form-item label="DOI">
              <el-input v-model="form.doi" placeholder="可选，建议填写以避免重复录入" />
            </el-form-item>

            <el-form-item label="引用次数">
              <el-input-number v-model="form.citation_count" :min="0" :max="100000" style="width: 100%" />
            </el-form-item>
          </div>

          <div class="grid two-cols">
            <el-form-item label="作者位次">
              <el-switch
                v-model="form.is_first_author"
                inline-prompt
                active-text="第一/通讯作者"
                inactive-text="其他作者"
              />
            </el-form-item>

            <el-form-item label="合作者">
              <el-input
                v-model="form.coauthors"
                placeholder="多个作者请用英文逗号分隔，例如 张三, 李四"
              />
            </el-form-item>
          </div>

          <div class="form-actions">
            <el-button type="primary" :loading="submitLoading" @click="submitForm">提交论文</el-button>
            <el-button :disabled="submitLoading" @click="resetForm">重置表单</el-button>
          </div>
        </el-form>
      </el-card>

      <el-card class="summary-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>最近一次提交结果</span>
            <el-tag v-if="latestPaper" type="warning">已更新</el-tag>
          </div>
        </template>

        <el-empty v-if="!latestPaper" description="提交论文后，这里会显示结构化结果回显" />

        <template v-else>
          <h3 class="summary-title">{{ latestPaper.title }}</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="论文类型">
              {{ latestPaper.paper_type_display }}
            </el-descriptions-item>
            <el-descriptions-item label="期刊/会议">
              {{ latestPaper.journal_name }}
            </el-descriptions-item>
            <el-descriptions-item label="发表日期">
              {{ latestPaper.date_acquired }}
            </el-descriptions-item>
            <el-descriptions-item label="DOI">
              {{ latestPaper.doi || '未填写' }}
            </el-descriptions-item>
            <el-descriptions-item label="关键词">
              <div class="tag-row">
                <el-tag v-for="keyword in latestPaper.keywords" :key="keyword" type="success" effect="plain">
                  {{ keyword }}
                </el-tag>
                <span v-if="!latestPaper.keywords.length" class="muted">暂未提取到关键词</span>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="合作者">
              <div class="tag-row">
                <el-tag
                  v-for="author in latestPaper.coauthor_details"
                  :key="author.id"
                  type="info"
                  effect="plain"
                >
                  {{ author.name }}
                </el-tag>
                <span v-if="!latestPaper.coauthor_details.length" class="muted">无</span>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </el-card>
    </div>

    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="card-header list-header">
          <span>我的论文记录</span>
          <div class="list-tools">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索标题、期刊或 DOI"
              clearable
              class="search-input"
              @keyup.enter="loadPapers"
              @clear="loadPapers"
            />
            <el-select v-model="paperTypeFilter" clearable placeholder="论文类型" @change="loadPapers">
              <el-option label="期刊论文" value="JOURNAL" />
              <el-option label="会议论文" value="CONFERENCE" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table v-loading="listLoading" :data="papers" empty-text="当前还没有录入论文" stripe>
        <el-table-column prop="title" label="论文标题" min-width="260" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag effect="plain">{{ row.paper_type_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="journal_name" label="期刊/会议" min-width="180" />
        <el-table-column prop="date_acquired" label="发表日期" width="130" />
        <el-table-column label="关键词" min-width="200">
          <template #default="{ row }">
            <div class="tag-row">
              <el-tag v-for="keyword in row.keywords" :key="keyword" size="small" type="success" effect="plain">
                {{ keyword }}
              </el-tag>
              <span v-if="!row.keywords.length" class="muted">暂无</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="合作者" min-width="180">
          <template #default="{ row }">
            <div class="tag-row">
              <el-tag
                v-for="author in row.coauthor_details"
                :key="author.id"
                size="small"
                type="info"
                effect="plain"
              >
                {{ author.name }}
              </el-tag>
              <span v-if="!row.coauthor_details.length" class="muted">无</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              link
              :loading="deletingPaperId === row.id"
              @click="deletePaper(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'

interface CoAuthorDetail {
  id: number
  name: string
}

interface PaperRecord {
  id: number
  title: string
  abstract: string
  date_acquired: string
  paper_type: string
  paper_type_display: string
  journal_name: string
  journal_level: string
  citation_count: number
  is_first_author: boolean
  doi: string
  created_at: string
  coauthor_details: CoAuthorDetail[]
  keywords: string[]
}

interface PaperFormState {
  title: string
  abstract: string
  date_acquired: string
  paper_type: string
  journal_name: string
  journal_level: string
  doi: string
  citation_count: number
  is_first_author: boolean
  coauthors: string
}

const router = useRouter()
const formRef = ref<FormInstance>()
const submitLoading = ref(false)
const listLoading = ref(false)
const deletingPaperId = ref<number | null>(null)
const papers = ref<PaperRecord[]>([])
const latestPaper = ref<PaperRecord | null>(null)
const currentUser = ref<SessionUser | null>(null)
const searchKeyword = ref('')
const paperTypeFilter = ref('')

const createDefaultForm = (): PaperFormState => ({
  title: '',
  abstract: '',
  date_acquired: '',
  paper_type: '',
  journal_name: '',
  journal_level: '',
  doi: '',
  citation_count: 0,
  is_first_author: true,
  coauthors: '',
})

const form = reactive<PaperFormState>(createDefaultForm())

const rules: FormRules<PaperFormState> = {
  title: [{ required: true, message: '请输入论文标题', trigger: 'blur' }],
  abstract: [{ required: true, message: '请输入论文摘要', trigger: 'blur' }],
  date_acquired: [{ required: true, message: '请选择发表日期', trigger: 'change' }],
  paper_type: [{ required: true, message: '请选择论文类型', trigger: 'change' }],
  journal_name: [{ required: true, message: '请输入期刊或会议名称', trigger: 'blur' }],
}

const teacherLabel = computed(() => {
  if (!currentUser.value) {
    return '未登录用户'
  }

  return currentUser.value.real_name || currentUser.value.username
})

const ensureUser = async (): Promise<SessionUser | null> => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return null
  }

  currentUser.value = sessionUser
  return sessionUser
}

const loadPapers = async () => {
  const sessionUser = await ensureUser()
  if (!sessionUser) return

  listLoading.value = true

  try {
    const response = await axios.get('/api/achievements/papers/', {
      params: {
        search: searchKeyword.value || undefined,
        paper_type: paperTypeFilter.value || undefined,
      },
    })

    papers.value = response.data
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '加载论文列表失败，请检查后端接口。')
  } finally {
    listLoading.value = false
  }
}

const submitForm = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const sessionUser = await ensureUser()
  if (!sessionUser) return

  submitLoading.value = true

  try {
    const payload = {
      title: form.title,
      abstract: form.abstract,
      date_acquired: form.date_acquired,
      paper_type: form.paper_type,
      journal_name: form.journal_name,
      journal_level: form.journal_level || undefined,
      doi: form.doi || undefined,
      citation_count: form.citation_count,
      is_first_author: form.is_first_author,
      coauthors: form.coauthors
        ? form.coauthors.split(',').map(item => item.trim()).filter(Boolean)
        : [],
    }

    const response = await axios.post('/api/achievements/papers/', payload)
    latestPaper.value = response.data
    ElMessage.success('论文录入成功，已完成数据库写入并触发后续分析。')
    resetForm()
    await loadPapers()
  } catch (error: any) {
    const detail = error?.response?.data
    if (typeof detail === 'string') {
      ElMessage.error(detail)
      return
    }

    if (detail && typeof detail === 'object') {
      const firstError = Object.values(detail)[0]
      ElMessage.error(Array.isArray(firstError) ? String(firstError[0]) : String(firstError))
      return
    }

    ElMessage.error(error?.message || '论文录入失败，请稍后再试。')
  } finally {
    submitLoading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, createDefaultForm())
  formRef.value?.clearValidate()
}

const deletePaper = async (paper: PaperRecord) => {
  try {
    await ElMessageBox.confirm(`确认删除论文“${paper.title}”吗？此操作不可恢复。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }

  deletingPaperId.value = paper.id

  try {
    await axios.delete(`/api/achievements/papers/${paper.id}/`)
    if (latestPaper.value?.id === paper.id) {
      latestPaper.value = null
    }
    ElMessage.success('论文已删除。')
    await loadPapers()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '删除失败，请稍后重试。')
  } finally {
    deletingPaperId.value = null
  }
}

onMounted(async () => {
  const sessionUser = await ensureUser()
  if (!sessionUser) return
  await loadPapers()
})
</script>

<style scoped>
.entry-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(67, 97, 238, 0.12), transparent 28%),
    radial-gradient(circle at top right, rgba(42, 157, 143, 0.12), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  margin-bottom: 24px;
  padding: 28px 32px;
  border-radius: 24px;
  background: linear-gradient(135deg, #0f172a 0%, #1d3557 100%);
  color: #fff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.16);
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.68);
}

.hero-panel h1 {
  margin: 0;
  font-size: 32px;
}

.hero-copy {
  max-width: 720px;
  margin: 12px 0 0;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.entry-layout {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.form-card,
.summary-card,
.list-card {
  border: none;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.entry-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.grid {
  display: grid;
  gap: 16px;
}

.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}

.summary-title {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 22px;
  color: #0f172a;
}

.list-header {
  align-items: center;
}

.list-tools {
  display: flex;
  gap: 12px;
}

.search-input {
  width: 260px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.muted {
  color: #94a3b8;
}

@media (max-width: 1080px) {
  .entry-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .entry-page {
    padding: 16px;
  }

  .hero-panel {
    flex-direction: column;
    align-items: flex-start;
    padding: 24px;
  }

  .hero-panel h1 {
    font-size: 26px;
  }

  .hero-actions,
  .list-tools,
  .two-cols {
    width: 100%;
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }
}
</style>
