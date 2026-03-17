<template>
  <div class="achievement-entry-page">
    <section class="hero-panel">
      <div>
        <p class="eyebrow">Research Achievement Workspace</p>
        <h1>教师成果录入中心</h1>
        <p class="hero-text">
          当前录入账号：
          <strong>{{ teacherLabel }}</strong>
          <span v-if="sessionUser?.department"> · {{ sessionUser.department }}</span>
          <span v-if="sessionUser?.title"> · {{ sessionUser.title }}</span>
        </p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button type="primary" @click="refreshAllRecords" :loading="pageLoading">刷新数据</el-button>
      </div>
    </section>

    <el-tabs v-model="activeTab" class="entry-tabs content-shell">
      <el-tab-pane label="论文成果" name="papers">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>论文录入</span>
                <el-button type="primary" plain @click="bibtexDialogVisible = true">BibTeX 批量导入</el-button>
              </div>
            </template>
            <el-form ref="paperFormRef" :model="paperForm" :rules="paperRules" label-position="top">
              <el-form-item label="论文题目" prop="title">
                <el-input v-model="paperForm.title" placeholder="请输入论文题目" />
              </el-form-item>
              <el-form-item label="摘要" prop="abstract">
                <el-input v-model="paperForm.abstract" type="textarea" :rows="4" placeholder="请输入论文摘要" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="获得时间" prop="date_acquired">
                  <el-date-picker v-model="paperForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="论文类型" prop="paper_type">
                  <el-select v-model="paperForm.paper_type" style="width: 100%">
                    <el-option v-for="option in paperTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <div class="double-grid">
                <el-form-item label="期刊/会议名称" prop="journal_name">
                  <el-input v-model="paperForm.journal_name" placeholder="请输入期刊或会议名称" />
                </el-form-item>
                <el-form-item label="级别">
                  <el-input v-model="paperForm.journal_level" placeholder="如 SCI、EI、CCF-B" />
                </el-form-item>
              </div>
              <div class="double-grid">
                <el-form-item label="引用次数">
                  <el-input-number v-model="paperForm.citation_count" :min="0" style="width: 100%" />
                </el-form-item>
                <el-form-item label="DOI">
                  <el-input v-model="paperForm.doi" placeholder="如 10.1000/xyz123" />
                </el-form-item>
              </div>
              <el-form-item>
                <el-switch v-model="paperForm.is_first_author" active-text="第一作者/通讯作者" inactive-text="非第一作者" />
              </el-form-item>
              <el-form-item label="合作者">
                <el-input
                  v-model="paperForm.coauthorInput"
                  placeholder="多个合作者请用中文逗号、英文逗号或换行分隔"
                  type="textarea"
                  :rows="3"
                />
              </el-form-item>
              <div class="actions">
                <el-button @click="resetPaperForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap.papers" @click="submitPaper">提交论文</el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>我的论文记录</span>
                <el-tag type="info">{{ papers.length }} 篇</el-tag>
              </div>
            </template>
            <el-table :data="papers" v-loading="loadingMap.papers" empty-text="暂无论文成果">
              <el-table-column prop="title" label="题目" min-width="220" />
              <el-table-column prop="paper_type_display" label="类型" width="110" />
              <el-table-column prop="journal_name" label="期刊/会议" min-width="170" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="关键词" min-width="180">
                <template #default="{ row }">
                  <div class="tag-list">
                    <el-tag v-for="keyword in row.keywords" :key="keyword" size="small" effect="plain">{{ keyword }}</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeRecord('papers', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="科研项目" name="projects">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>项目录入</template>
            <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-position="top">
              <el-form-item label="项目名称" prop="title">
                <el-input v-model="projectForm.title" placeholder="请输入项目名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="立项时间" prop="date_acquired">
                  <el-date-picker v-model="projectForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="项目级别" prop="level">
                  <el-select v-model="projectForm.level" style="width: 100%">
                    <el-option v-for="option in projectLevelOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <div class="double-grid">
                <el-form-item label="承担角色" prop="role">
                  <el-select v-model="projectForm.role" style="width: 100%">
                    <el-option v-for="option in projectRoleOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="经费（万元）" prop="funding_amount">
                  <el-input-number v-model="projectForm.funding_amount" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </div>
              <el-form-item label="项目状态" prop="status">
                <el-input v-model="projectForm.status" placeholder="如 ONGOING、COMPLETED" />
              </el-form-item>
              <div class="actions">
                <el-button @click="resetProjectForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap.projects" @click="submitProject">提交项目</el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>我的项目记录</span>
                <el-tag type="success">{{ projects.length }} 项</el-tag>
              </div>
            </template>
            <el-table :data="projects" v-loading="loadingMap.projects" empty-text="暂无科研项目">
              <el-table-column prop="title" label="项目名称" min-width="220" />
              <el-table-column prop="level_display" label="级别" width="120" />
              <el-table-column prop="role_display" label="角色" width="120" />
              <el-table-column prop="funding_amount" label="经费(万元)" width="120" />
              <el-table-column prop="status" label="状态" width="120" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeRecord('projects', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="知识产权" name="intellectual-properties">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>知识产权录入</template>
            <el-form ref="ipFormRef" :model="ipForm" :rules="ipRules" label-position="top">
              <el-form-item label="成果名称" prop="title">
                <el-input v-model="ipForm.title" placeholder="请输入知识产权名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="授权/登记时间" prop="date_acquired">
                  <el-date-picker v-model="ipForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="类型" prop="ip_type">
                  <el-select v-model="ipForm.ip_type" style="width: 100%">
                    <el-option v-for="option in ipTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="登记号/专利号" prop="registration_number">
                <el-input v-model="ipForm.registration_number" placeholder="请输入登记号或专利号" />
              </el-form-item>
              <el-form-item>
                <el-switch v-model="ipForm.is_transformed" active-text="已成果转化" inactive-text="未成果转化" />
              </el-form-item>
              <div class="actions">
                <el-button @click="resetIpForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap['intellectual-properties']" @click="submitIp">提交知识产权</el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>我的知识产权</span>
                <el-tag type="warning">{{ intellectualProperties.length }} 项</el-tag>
              </div>
            </template>
            <el-table :data="intellectualProperties" v-loading="loadingMap['intellectual-properties']" empty-text="暂无知识产权成果">
              <el-table-column prop="title" label="名称" min-width="220" />
              <el-table-column prop="ip_type_display" label="类型" width="140" />
              <el-table-column prop="registration_number" label="登记号" min-width="180" />
              <el-table-column label="转化" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.is_transformed ? 'success' : 'info'">{{ row.is_transformed ? '已转化' : '未转化' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeRecord('intellectual-properties', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="教学成果" name="teaching-achievements">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>教学成果录入</template>
            <el-form ref="teachingFormRef" :model="teachingForm" :rules="teachingRules" label-position="top">
              <el-form-item label="成果名称" prop="title">
                <el-input v-model="teachingForm.title" placeholder="请输入教学成果名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="获得时间" prop="date_acquired">
                  <el-date-picker v-model="teachingForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="成果类型" prop="achievement_type">
                  <el-select v-model="teachingForm.achievement_type" style="width: 100%">
                    <el-option v-for="option in teachingTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="级别" prop="level">
                <el-input v-model="teachingForm.level" placeholder="如 国家级、省级、校级" />
              </el-form-item>
              <div class="actions">
                <el-button @click="resetTeachingForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap['teaching-achievements']" @click="submitTeaching">提交教学成果</el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>我的教学成果</span>
                <el-tag>{{ teachingAchievements.length }} 项</el-tag>
              </div>
            </template>
            <el-table :data="teachingAchievements" v-loading="loadingMap['teaching-achievements']" empty-text="暂无教学成果">
              <el-table-column prop="title" label="名称" min-width="220" />
              <el-table-column prop="achievement_type_display" label="类型" width="140" />
              <el-table-column prop="level" label="级别" width="120" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeRecord('teaching-achievements', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="学术服务" name="academic-services">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>学术服务录入</template>
            <el-form ref="serviceFormRef" :model="serviceForm" :rules="serviceRules" label-position="top">
              <el-form-item label="服务名称" prop="title">
                <el-input v-model="serviceForm.title" placeholder="请输入服务事项或报告名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="服务时间" prop="date_acquired">
                  <el-date-picker v-model="serviceForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="服务类型" prop="service_type">
                  <el-select v-model="serviceForm.service_type" style="width: 100%">
                    <el-option v-for="option in serviceTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="服务机构" prop="organization">
                <el-input v-model="serviceForm.organization" placeholder="请输入期刊、会议或机构名称" />
              </el-form-item>
              <div class="actions">
                <el-button @click="resetServiceForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap['academic-services']" @click="submitService">提交学术服务</el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>我的学术服务</span>
                <el-tag type="danger">{{ academicServices.length }} 项</el-tag>
              </div>
            </template>
            <el-table :data="academicServices" v-loading="loadingMap['academic-services']" empty-text="暂无学术服务">
              <el-table-column prop="title" label="事项" min-width="220" />
              <el-table-column prop="service_type_display" label="类型" width="140" />
              <el-table-column prop="organization" label="服务机构" min-width="180" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeRecord('academic-services', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <PaperBibtexImportDialog v-model="bibtexDialogVisible" @imported="handleBibtexImported" />
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PaperBibtexImportDialog from './achievement-entry/PaperBibtexImportDialog.vue'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import {
  achievementEndpointMap,
  createAchievementStatusMap,
  ipTypeOptions,
  normalizeAchievementList,
  paperTypeOptions,
  parseCoauthorInput,
  projectLevelOptions,
  projectRoleOptions,
  serviceTypeOptions,
  teachingTypeOptions,
} from './achievement-entry/constants'
import type {
  IpRecord,
  PaperRecord,
  ProjectRecord,
  ServiceRecord,
  TabName,
  TeachingRecord,
} from './achievement-entry/types'

const router = useRouter()
const activeTab = ref<TabName>('papers')
const pageLoading = ref(false)
const sessionUser = ref<SessionUser | null>(null)
const bibtexDialogVisible = ref(false)

const paperFormRef = ref<FormInstance>()
const projectFormRef = ref<FormInstance>()
const ipFormRef = ref<FormInstance>()
const teachingFormRef = ref<FormInstance>()
const serviceFormRef = ref<FormInstance>()

const papers = ref<PaperRecord[]>([])
const projects = ref<ProjectRecord[]>([])
const intellectualProperties = ref<IpRecord[]>([])
const teachingAchievements = ref<TeachingRecord[]>([])
const academicServices = ref<ServiceRecord[]>([])

const loadingMap = reactive<Record<TabName, boolean>>(createAchievementStatusMap())
const submittingMap = reactive<Record<TabName, boolean>>(createAchievementStatusMap())

const paperForm = reactive({
  title: '',
  abstract: '',
  date_acquired: '',
  paper_type: 'JOURNAL',
  journal_name: '',
  journal_level: '',
  citation_count: 0,
  is_first_author: true,
  doi: '',
  coauthorInput: '',
})

const projectForm = reactive({
  title: '',
  date_acquired: '',
  level: 'NATIONAL',
  role: 'PI',
  funding_amount: 0,
  status: 'ONGOING',
})

const ipForm = reactive({
  title: '',
  date_acquired: '',
  ip_type: 'PATENT_INVENTION',
  registration_number: '',
  is_transformed: false,
})

const teachingForm = reactive({
  title: '',
  date_acquired: '',
  achievement_type: 'COMPETITION',
  level: '',
})

const serviceForm = reactive({
  title: '',
  date_acquired: '',
  service_type: 'EDITOR',
  organization: '',
})

const teacherLabel = computed(() => {
  if (!sessionUser.value) {
    return '未识别教师'
  }

  return sessionUser.value.real_name || sessionUser.value.username
})

const requiredRule = (message: string) => [{ required: true, message, trigger: 'blur' }]

const paperRules: FormRules = {
  title: requiredRule('请输入论文题目'),
  abstract: requiredRule('请输入论文摘要'),
  date_acquired: requiredRule('请选择获得时间'),
  paper_type: requiredRule('请选择论文类型'),
  journal_name: requiredRule('请输入期刊或会议名称'),
}

const projectRules: FormRules = {
  title: requiredRule('请输入项目名称'),
  date_acquired: requiredRule('请选择立项时间'),
  level: requiredRule('请选择项目级别'),
  role: requiredRule('请选择承担角色'),
  funding_amount: requiredRule('请输入项目经费'),
  status: requiredRule('请输入项目状态'),
}

const ipRules: FormRules = {
  title: requiredRule('请输入成果名称'),
  date_acquired: requiredRule('请选择授权时间'),
  ip_type: requiredRule('请选择知识产权类型'),
  registration_number: requiredRule('请输入登记号'),
}

const teachingRules: FormRules = {
  title: requiredRule('请输入成果名称'),
  date_acquired: requiredRule('请选择获得时间'),
  achievement_type: requiredRule('请选择成果类型'),
  level: requiredRule('请输入成果级别'),
}

const serviceRules: FormRules = {
  title: requiredRule('请输入服务名称'),
  date_acquired: requiredRule('请选择服务时间'),
  service_type: requiredRule('请选择服务类型'),
  organization: requiredRule('请输入服务机构'),
}

const fetchRecords = async (tab: TabName): Promise<void> => {
  loadingMap[tab] = true
  try {
    const response = await axios.get(achievementEndpointMap[tab])
    const items = normalizeAchievementList(response.data)

    if (tab === 'papers') papers.value = items as PaperRecord[]
    if (tab === 'projects') projects.value = items as ProjectRecord[]
    if (tab === 'intellectual-properties') intellectualProperties.value = items as IpRecord[]
    if (tab === 'teaching-achievements') teachingAchievements.value = items as TeachingRecord[]
    if (tab === 'academic-services') academicServices.value = items as ServiceRecord[]
  } finally {
    loadingMap[tab] = false
  }
}

const refreshAllRecords = async (): Promise<void> => {
  pageLoading.value = true
  try {
    sessionUser.value = await ensureSessionUserContext()
    await Promise.all((Object.keys(achievementEndpointMap) as TabName[]).map(fetchRecords))
  } finally {
    pageLoading.value = false
  }
}

const resetPaperForm = (): void => {
  paperFormRef.value?.resetFields()
  paperForm.paper_type = 'JOURNAL'
  paperForm.citation_count = 0
  paperForm.is_first_author = true
  paperForm.coauthorInput = ''
}

const resetProjectForm = (): void => {
  projectFormRef.value?.resetFields()
  projectForm.level = 'NATIONAL'
  projectForm.role = 'PI'
  projectForm.funding_amount = 0
  projectForm.status = 'ONGOING'
}

const resetIpForm = (): void => {
  ipFormRef.value?.resetFields()
  ipForm.ip_type = 'PATENT_INVENTION'
  ipForm.is_transformed = false
}

const resetTeachingForm = (): void => {
  teachingFormRef.value?.resetFields()
  teachingForm.achievement_type = 'COMPETITION'
}

const resetServiceForm = (): void => {
  serviceFormRef.value?.resetFields()
  serviceForm.service_type = 'EDITOR'
}

const submitPaper = async (): Promise<void> => {
  const valid = await paperFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingMap.papers = true
  try {
    await axios.post(achievementEndpointMap.papers, {
      title: paperForm.title,
      abstract: paperForm.abstract,
      date_acquired: paperForm.date_acquired,
      paper_type: paperForm.paper_type,
      journal_name: paperForm.journal_name,
      journal_level: paperForm.journal_level,
      citation_count: paperForm.citation_count,
      is_first_author: paperForm.is_first_author,
      doi: paperForm.doi,
      coauthors: parseCoauthorInput(paperForm.coauthorInput),
    })
    ElMessage.success('论文成果已录入')
    resetPaperForm()
    await fetchRecords('papers')
  } finally {
    submittingMap.papers = false
  }
}

const submitProject = async (): Promise<void> => {
  const valid = await projectFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingMap.projects = true
  try {
    await axios.post(achievementEndpointMap.projects, { ...projectForm })
    ElMessage.success('科研项目已录入')
    resetProjectForm()
    await fetchRecords('projects')
  } finally {
    submittingMap.projects = false
  }
}

const submitIp = async (): Promise<void> => {
  const valid = await ipFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingMap['intellectual-properties'] = true
  try {
    await axios.post(achievementEndpointMap['intellectual-properties'], { ...ipForm })
    ElMessage.success('知识产权成果已录入')
    resetIpForm()
    await fetchRecords('intellectual-properties')
  } finally {
    submittingMap['intellectual-properties'] = false
  }
}

const submitTeaching = async (): Promise<void> => {
  const valid = await teachingFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingMap['teaching-achievements'] = true
  try {
    await axios.post(achievementEndpointMap['teaching-achievements'], { ...teachingForm })
    ElMessage.success('教学成果已录入')
    resetTeachingForm()
    await fetchRecords('teaching-achievements')
  } finally {
    submittingMap['teaching-achievements'] = false
  }
}

const submitService = async (): Promise<void> => {
  const valid = await serviceFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingMap['academic-services'] = true
  try {
    await axios.post(achievementEndpointMap['academic-services'], { ...serviceForm })
    ElMessage.success('学术服务已录入')
    resetServiceForm()
    await fetchRecords('academic-services')
  } finally {
    submittingMap['academic-services'] = false
  }
}

const removeRecord = async (tab: TabName, id: number): Promise<void> => {
  await ElMessageBox.confirm('删除后将同步影响画像统计与图谱展示，确认继续吗？', '删除确认', {
    type: 'warning',
  })

  await axios.delete(`${achievementEndpointMap[tab]}${id}/`)
  ElMessage.success('记录已删除')
  await fetchRecords(tab)
}

const handleBibtexImported = async (): Promise<void> => {
  await fetchRecords('papers')
}

onMounted(() => {
  void refreshAllRecords()
})
</script>

<style scoped>
.achievement-entry-page {
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.12), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.1), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
  min-height: 100vh;
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

.entry-tabs :deep(.el-card) {
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

.entry-tabs {
  margin-top: 0;
}

.entry-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.entry-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0 6px;
}

.entry-tabs :deep(.el-tabs__item) {
  height: 42px;
  font-weight: 600;
}

.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.entry-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 20px;
}

.double-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.actions {
  justify-content: flex-end;
  margin-top: 8px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1080px) {
  .entry-grid,
  .double-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .actions {
    display: flex;
  }
}

@media (max-width: 768px) {
  .achievement-entry-page {
    padding: 16px;
  }

  .hero-panel,
  .hero-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
