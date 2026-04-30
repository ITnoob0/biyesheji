<template>
  <div class="evaluation-rules-page workspace-page">
    <section class="hero-shell workspace-content-shell">
      <div class="hero-main workspace-hero workspace-hero--brand">
        <div class="hero-copy-block">
          <p class="workspace-hero__eyebrow">Core Research Evaluation Rules</p>
          <h1 class="workspace-hero__title">核心科研能力评价规则</h1>
          <p class="workspace-hero__text hero-copy">
            当前版本：
            <strong>{{ dashboardData?.active_version?.name || '未配置' }}</strong>
            <span v-if="dashboardData?.active_version?.status_display"> | {{ dashboardData.active_version.status_display }}</span>
            <span v-if="sessionUser?.role_label"> | {{ sessionUser.role_label }}</span>
          </p>
          <div class="hero-actions workspace-page-actions">
            <el-button v-if="entryScope === 'management'" plain @click="router.push('/teachers')">返回教师管理</el-button>
            <el-button v-else plain @click="router.push('/dashboard')">返回教师画像</el-button>
            <el-button
              v-if="entryScope === 'management' && canEdit && !showManageSection"
              plain
              @click="router.push('/evaluation-rules/manage')"
            >
              规则维护
            </el-button>
            <el-button
              v-if="entryScope === 'management' && showManageSection"
              plain
              @click="router.push('/evaluation-rules')"
            >
              规则总览
            </el-button>
            <el-button type="primary" :loading="loading" @click="handleRefresh">刷新规则</el-button>
          </div>
        </div>
      </div>
    </section>

    <section v-if="showOverviewSection && dashboardData" class="workspace-content-shell section-stack">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="workspace-section-head">
            <span>版本信息</span>
            <el-tag type="success" effect="plain">{{ dashboardData.summary.rule_count }} 条规则</el-tag>
          </div>
        </template>
        <div class="version-grid">
          <div>
            <span class="meta-label">版本名称</span>
            <strong>{{ dashboardData.active_version.name }}</strong>
          </div>
          <div>
            <span class="meta-label">版本编码</span>
            <strong>{{ dashboardData.active_version.code }}</strong>
          </div>
          <div>
            <span class="meta-label">来源文件</span>
            <strong>{{ dashboardData.active_version.source_document || '未填写' }}</strong>
          </div>
          <div>
            <span class="meta-label">更新时间</span>
            <strong>{{ formatDateTime(dashboardData.active_version.updated_at) }}</strong>
          </div>
        </div>
      </el-card>

      <section class="summary-grid">
        <div class="summary-card workspace-surface-card">
          <strong>{{ dashboardData.summary.category_count }}</strong>
          <span>规则大类</span>
          <p>学校管理员可维护大类、维度归属和是否参与总分。</p>
        </div>
        <div class="summary-card workspace-surface-card">
          <strong>{{ dashboardData.summary.included_count }}</strong>
          <span>可填报小项</span>
          <p>教师录入时按大类与加分项选择，系统自动展示对应规则分。</p>
        </div>
        <div class="summary-card workspace-surface-card">
          <strong>{{ dashboardData.summary.workflow_step_count }}</strong>
          <span>审核步骤</span>
          <p>教师填报后进入学院管理员审核，通过后才正式进入教师画像。</p>
        </div>
      </section>

      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="workspace-section-head">
            <span>规则总览</span>
            <el-tag effect="plain">{{ dashboardData.categories.length }} 个大类</el-tag>
          </div>
        </template>
        <el-collapse v-model="expandedGroups">
          <el-collapse-item v-for="group in dashboardData.grouped_rules" :key="group.key" :name="group.key">
            <template #title>
              <div class="collapse-title">
                <strong>{{ group.label }}</strong>
                <el-tag size="small" effect="plain">{{ group.items.length }} 条</el-tag>
                <el-tag size="small" type="warning" effect="plain" v-if="group.dimension_label">{{ group.dimension_label }}</el-tag>
              </div>
            </template>
            <el-table :data="group.items" row-key="id" empty-text="暂无规则条目">
              <el-table-column prop="rule_code" label="编码" width="140" />
              <el-table-column prop="discipline_display" label="学科口径" width="120" />
              <el-table-column prop="title" label="规则名称" min-width="280" />
              <el-table-column prop="score_text" label="规则积分" width="140" />
              <el-table-column label="计分方式" width="140">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.score_mode_display }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="团队计分" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.is_team_rule ? 'warning' : 'info'" effect="plain">
                    {{ row.is_team_rule ? '团队分配' : '否' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="总分/雷达" width="140">
                <template #default="{ row }">
                  <div class="tiny-flag-stack">
                    <el-tag size="small" :type="row.include_in_total ? 'success' : 'info'" effect="plain">
                      {{ row.include_in_total ? '进总分' : '不进总分' }}
                    </el-tag>
                    <el-tag size="small" :type="row.include_in_radar ? 'warning' : 'info'" effect="plain">
                      {{ row.include_in_radar ? '进雷达' : '不进雷达' }}
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="说明" min-width="260">
                <template #default="{ row }">
                  <span class="muted">{{ row.team_distribution_note || row.note || row.description || '—' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </section>

    <section v-if="showManageSection" class="workspace-content-shell section-stack">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="workspace-section-head">
            <span>规则分类管理</span>
            <el-button type="primary" plain @click="openCategoryDialog()">新增大类</el-button>
          </div>
        </template>
        <el-table :data="categoryItems" row-key="id" empty-text="暂无规则分类" v-loading="manageLoading">
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="dimension_label" label="画像维度" width="180" />
          <el-table-column label="填报/总分/雷达" width="200">
            <template #default="{ row }">
              <div class="tiny-flag-stack">
                <el-tag size="small" :type="row.entry_enabled ? 'success' : 'info'" effect="plain">
                  {{ row.entry_enabled ? '允许填报' : '不允许填报' }}
                </el-tag>
                <el-tag size="small" :type="row.include_in_total ? 'success' : 'info'" effect="plain">
                  {{ row.include_in_total ? '进总分' : '不进总分' }}
                </el-tag>
                <el-tag size="small" :type="row.include_in_radar ? 'warning' : 'info'" effect="plain">
                  {{ row.include_in_radar ? '进雷达' : '不进雷达' }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button link type="primary" @click="openCategoryDialog(row)">编辑</el-button>
              <el-button link type="danger" @click="removeCategory(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="workspace-section-head workspace-section-head--wrap">
            <span>规则条目管理</span>
            <div class="workspace-toolbar">
              <el-select v-model="ruleCategoryFilter" clearable placeholder="全部大类" style="width: 180px">
                <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-input v-model="ruleSearch" clearable placeholder="搜索规则名称" style="width: 220px" />
              <el-button type="primary" plain @click="openRuleDialog()">新增规则条目</el-button>
            </div>
          </div>
        </template>
        <el-table :data="filteredRuleItems" row-key="id" empty-text="暂无规则条目" v-loading="manageLoading">
          <el-table-column prop="rule_code" label="编码" width="120" />
          <el-table-column prop="category_name" label="大类" width="160" />
          <el-table-column prop="title" label="规则名称" min-width="240" />
          <el-table-column prop="score_text" label="规则积分" width="140" />
          <el-table-column prop="score_mode_display" label="计分方式" width="120" />
          <el-table-column prop="multi_match_policy_display" label="重复处理" width="140" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button link type="primary" @click="openRuleDialog(row)">编辑</el-button>
              <el-button link type="danger" @click="removeRule(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <el-dialog v-model="categoryDialogVisible" :title="editingCategoryId ? '编辑规则大类' : '新增规则大类'" width="720px">
      <el-form label-position="top">
        <div class="double-grid">
          <el-form-item label="分类编码">
            <el-input v-model="categoryForm.code" />
          </el-form-item>
          <el-form-item label="分类名称">
            <el-input v-model="categoryForm.name" />
          </el-form-item>
        </div>
        <div class="double-grid">
          <el-form-item label="画像维度键">
            <el-input v-model="categoryForm.dimension_key" placeholder="如 academic_output" />
          </el-form-item>
          <el-form-item label="画像维度名称">
            <el-input v-model="categoryForm.dimension_label" placeholder="如 学术产出与著作" />
          </el-form-item>
        </div>
        <el-form-item label="分类说明">
          <el-input v-model="categoryForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <div class="triple-grid">
          <el-form-item>
            <el-switch v-model="categoryForm.entry_enabled" active-text="允许教师填报" inactive-text="不允许教师填报" />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="categoryForm.include_in_total" active-text="参与总分" inactive-text="不参与总分" />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="categoryForm.include_in_radar" active-text="进入雷达" inactive-text="不进入雷达" />
          </el-form-item>
        </div>
        <el-form-item label="排序值">
          <el-input-number v-model="categoryForm.sort_order" :min="1" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item>
          <el-switch v-model="categoryForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCategory">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ruleDialogVisible" :title="editingRuleId ? '编辑规则条目' : '新增规则条目'" width="900px">
      <el-form label-position="top">
        <div class="triple-grid">
          <el-form-item label="规则编码">
            <el-input v-model="ruleForm.rule_code" />
          </el-form-item>
          <el-form-item label="所属大类">
            <el-select v-model="ruleForm.category_ref" style="width: 100%">
              <el-option v-for="item in categoryItems" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="学科口径">
            <el-select v-model="ruleForm.discipline" style="width: 100%">
              <el-option v-for="item in disciplineOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </div>
        <div class="triple-grid">
          <el-form-item label="计分方式">
            <el-select v-model="ruleForm.score_mode" style="width: 100%">
              <el-option v-for="item in scoreModeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="规则积分文本">
            <el-input v-model="ruleForm.score_text" placeholder="如 300 或 12/万元" />
          </el-form-item>
          <el-form-item label="排序值">
            <el-input-number v-model="ruleForm.sort_order" :min="1" :step="10" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="double-grid">
          <el-form-item label="基础积分">
            <el-input-number v-model="ruleForm.base_score" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="每单位积分">
            <el-input-number v-model="ruleForm.score_per_unit" :min="0" :precision="4" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="double-grid">
          <el-form-item label="计分单位">
            <el-input v-model="ruleForm.score_unit_label" placeholder="如 万元" />
          </el-form-item>
          <el-form-item label="互斥组">
            <el-input v-model="ruleForm.conflict_group" placeholder="同成果只取高时可配置统一组名" />
          </el-form-item>
        </div>
        <el-form-item label="重复命中处理">
          <el-select v-model="ruleForm.multi_match_policy" style="width: 100%">
            <el-option v-for="item in multiMatchOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则名称">
          <el-input v-model="ruleForm.title" />
        </el-form-item>
        <el-form-item label="规则说明">
          <el-input v-model="ruleForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="ruleForm.note" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="佐证要求">
          <el-input v-model="ruleForm.evidence_requirements" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="团队积分说明">
          <el-input v-model="ruleForm.team_distribution_note" type="textarea" :rows="3" />
        </el-form-item>
        <div class="triple-grid">
          <el-form-item>
            <el-switch v-model="ruleForm.requires_amount_input" active-text="需要金额/数量" inactive-text="无需金额/数量" />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="ruleForm.is_team_rule" active-text="团队积分项" inactive-text="非团队积分项" />
          </el-form-item>
          <el-form-item>
            <el-input-number v-model="ruleForm.team_max_member_ratio" :min="0" :max="1" :precision="3" :step="0.01" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="double-grid">
          <el-form-item>
            <el-switch v-model="ruleForm.include_in_total" active-text="参与总分" inactive-text="不参与总分" />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="ruleForm.include_in_radar" active-text="进入雷达" inactive-text="不进入雷达" />
          </el-form-item>
        </div>
        <el-form-item>
          <el-switch v-model="ruleForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type {
  EvaluationRuleCategoryRecord,
  EvaluationRuleDashboardResponse,
  EvaluationRuleItemRecord,
} from '../types/evaluationRules'

type SectionMode = 'overview' | 'manage'
type EntryScope = 'management' | 'portrait'

const props = withDefaults(
  defineProps<{
    sectionMode?: SectionMode
    entryScope?: EntryScope
  }>(),
  {
    sectionMode: 'overview',
    entryScope: 'management',
  },
)

const router = useRouter()
const sessionUser = ref<SessionUser | null>(null)
const dashboardData = ref<EvaluationRuleDashboardResponse | null>(null)
const loading = ref(false)
const manageLoading = ref(false)
const submitting = ref(false)
const expandedGroups = ref<string[]>([])
const categoryItems = ref<EvaluationRuleCategoryRecord[]>([])
const ruleItems = ref<EvaluationRuleItemRecord[]>([])
const ruleSearch = ref('')
const ruleCategoryFilter = ref<number | ''>('')

const categoryDialogVisible = ref(false)
const ruleDialogVisible = ref(false)
const editingCategoryId = ref<number | null>(null)
const editingRuleId = ref<number | null>(null)

const canEdit = computed(() => Boolean(dashboardData.value?.permissions?.can_edit))
const showOverviewSection = computed(() => props.sectionMode === 'overview')
const showManageSection = computed(() => props.sectionMode === 'manage' && canEdit.value)
const categoryOptions = computed(() => categoryItems.value.map(item => ({ label: item.name, value: item.id })))

const disciplineOptions = [
  { label: '自然科学', value: 'NATURAL' },
  { label: '人文社科', value: 'HUMANITIES' },
  { label: '通用', value: 'GENERAL' },
] as const

const scoreModeOptions = [
  { label: '固定积分', value: 'FIXED' },
  { label: '按金额/数量积分', value: 'PER_AMOUNT' },
  { label: '人工认定', value: 'MANUAL' },
] as const

const multiMatchOptions = [
  { label: '命中多项时取高', value: 'EXCLUSIVE_HIGHER' },
  { label: '允许叠加', value: 'STACKABLE' },
  { label: '需管理员确认', value: 'MANUAL_REVIEW' },
] as const

const categoryForm = reactive({
  version: 0,
  code: '',
  name: '',
  description: '',
  dimension_key: '',
  dimension_label: '',
  entry_enabled: true,
  include_in_total: true,
  include_in_radar: true,
  sort_order: 100,
  is_active: true,
})

const ruleForm = reactive({
  version: 0,
  category_ref: null as number | null,
  rule_code: '',
  discipline: 'GENERAL',
  entry_policy: 'REQUIRED',
  score_mode: 'FIXED',
  base_score: null as number | null,
  score_per_unit: null as number | null,
  score_unit_label: '',
  requires_amount_input: false,
  is_team_rule: false,
  team_distribution_note: '',
  team_max_member_ratio: 0.333,
  conflict_group: '',
  multi_match_policy: 'EXCLUSIVE_HIGHER',
  entry_form_schema: [] as Array<Record<string, unknown>>,
  title: '',
  description: '',
  score_text: '',
  note: '',
  evidence_requirements: '',
  include_in_total: true,
  include_in_radar: true,
  sort_order: 100,
  is_active: true,
})

const filteredRuleItems = computed(() =>
  ruleItems.value.filter(item => {
    if (ruleCategoryFilter.value && item.category_ref !== ruleCategoryFilter.value) return false
    if (ruleSearch.value.trim() && !item.title.includes(ruleSearch.value.trim())) return false
    return true
  }),
)

const resetCategoryForm = () => {
  editingCategoryId.value = null
  Object.assign(categoryForm, {
    version: dashboardData.value?.active_version?.id || 0,
    code: '',
    name: '',
    description: '',
    dimension_key: '',
    dimension_label: '',
    entry_enabled: true,
    include_in_total: true,
    include_in_radar: true,
    sort_order: 100,
    is_active: true,
  })
}

const resetRuleForm = () => {
  editingRuleId.value = null
  Object.assign(ruleForm, {
    version: dashboardData.value?.active_version?.id || 0,
    category_ref: categoryItems.value[0]?.id || null,
    rule_code: '',
    discipline: 'GENERAL',
    entry_policy: 'REQUIRED',
    score_mode: 'FIXED',
    base_score: null,
    score_per_unit: null,
    score_unit_label: '',
    requires_amount_input: false,
    is_team_rule: false,
    team_distribution_note: '',
    team_max_member_ratio: 0.333,
    conflict_group: '',
    multi_match_policy: 'EXCLUSIVE_HIGHER',
    entry_form_schema: [],
    title: '',
    description: '',
    score_text: '',
    note: '',
    evidence_requirements: '',
    include_in_total: true,
    include_in_radar: true,
    sort_order: 100,
    is_active: true,
  })
}

const loadDashboard = async () => {
  loading.value = true
  try {
    const { data } = await axios.get<EvaluationRuleDashboardResponse>('/api/evaluation-rules/dashboard/')
    dashboardData.value = data
    expandedGroups.value = data.grouped_rules.map(item => item.key)
    categoryItems.value = data.categories
    ruleItems.value = data.grouped_rules.flatMap(group => group.items)
  } catch (error) {
    console.error(error)
    ElMessage.error('评价规则加载失败')
  } finally {
    loading.value = false
  }
}

const loadManageResources = async () => {
  if (!showManageSection.value || !dashboardData.value?.active_version?.id) return
  manageLoading.value = true
  try {
    const [categoryResponse, itemResponse] = await Promise.all([
      axios.get<EvaluationRuleCategoryRecord[]>('/api/evaluation-rules/categories/', {
        params: { version: dashboardData.value.active_version.id },
      }),
      axios.get<EvaluationRuleItemRecord[]>('/api/evaluation-rules/items/', {
        params: { version: dashboardData.value.active_version.id },
      }),
    ])
    categoryItems.value = categoryResponse.data
    ruleItems.value = itemResponse.data
  } catch (error) {
    console.error(error)
    ElMessage.error('规则维护数据加载失败')
  } finally {
    manageLoading.value = false
  }
}

const handleRefresh = async () => {
  await loadDashboard()
  await loadManageResources()
}

const openCategoryDialog = (row?: EvaluationRuleCategoryRecord) => {
  resetCategoryForm()
  if (row) {
    editingCategoryId.value = row.id
    Object.assign(categoryForm, row)
  }
  categoryDialogVisible.value = true
}

const openRuleDialog = (row?: EvaluationRuleItemRecord) => {
  resetRuleForm()
  if (row) {
    editingRuleId.value = row.id
    Object.assign(ruleForm, {
      ...row,
      category_ref: row.category_ref,
      base_score: row.base_score === null || row.base_score === '' ? null : Number(row.base_score),
      score_per_unit: row.score_per_unit === null || row.score_per_unit === '' ? null : Number(row.score_per_unit),
      team_max_member_ratio: Number(row.team_max_member_ratio || 0.333),
    })
  }
  ruleDialogVisible.value = true
}

const submitCategory = async () => {
  if (!categoryForm.code.trim() || !categoryForm.name.trim()) {
    ElMessage.warning('请先填写分类编码和分类名称')
    return
  }
  submitting.value = true
  try {
    const payload = {
      ...categoryForm,
      code: categoryForm.code.trim(),
      name: categoryForm.name.trim(),
      description: categoryForm.description.trim(),
      dimension_key: categoryForm.dimension_key.trim(),
      dimension_label: categoryForm.dimension_label.trim(),
    }
    if (editingCategoryId.value) {
      await axios.patch(`/api/evaluation-rules/categories/${editingCategoryId.value}/`, payload)
      ElMessage.success('规则大类已更新')
    } else {
      await axios.post('/api/evaluation-rules/categories/', payload)
      ElMessage.success('规则大类已创建')
    }
    categoryDialogVisible.value = false
    await handleRefresh()
  } catch (error) {
    console.error(error)
    ElMessage.error('规则大类保存失败')
  } finally {
    submitting.value = false
  }
}

const submitRule = async () => {
  if (!ruleForm.title.trim() || !ruleForm.category_ref) {
    ElMessage.warning('请先填写规则名称并选择所属大类')
    return
  }
  submitting.value = true
  try {
    const payload = {
      ...ruleForm,
      rule_code: ruleForm.rule_code.trim(),
      score_unit_label: ruleForm.score_unit_label.trim(),
      conflict_group: ruleForm.conflict_group.trim(),
      title: ruleForm.title.trim(),
      description: ruleForm.description.trim(),
      score_text: ruleForm.score_text.trim(),
      note: ruleForm.note.trim(),
      evidence_requirements: ruleForm.evidence_requirements.trim(),
      team_distribution_note: ruleForm.team_distribution_note.trim(),
    }
    if (editingRuleId.value) {
      await axios.patch(`/api/evaluation-rules/items/${editingRuleId.value}/`, payload)
      ElMessage.success('规则条目已更新')
    } else {
      await axios.post('/api/evaluation-rules/items/', payload)
      ElMessage.success('规则条目已创建')
    }
    ruleDialogVisible.value = false
    await handleRefresh()
  } catch (error) {
    console.error(error)
    ElMessage.error('规则条目保存失败')
  } finally {
    submitting.value = false
  }
}

const removeCategory = async (row: EvaluationRuleCategoryRecord) => {
  try {
    await ElMessageBox.confirm(`确定删除规则大类“${row.name}”吗？`, '删除确认', { type: 'warning' })
    await axios.delete(`/api/evaluation-rules/categories/${row.id}/`)
    ElMessage.success('规则大类已删除')
    await handleRefresh()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('规则大类删除失败')
    }
  }
}

const removeRule = async (row: EvaluationRuleItemRecord) => {
  try {
    await ElMessageBox.confirm(`确定删除规则条目“${row.title}”吗？`, '删除确认', { type: 'warning' })
    await axios.delete(`/api/evaluation-rules/items/${row.id}/`)
    ElMessage.success('规则条目已删除')
    await handleRefresh()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('规则条目删除失败')
    }
  }
}

const formatDateTime = (value?: string) => {
  if (!value) return '未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未记录'
  return date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  sessionUser.value = await ensureSessionUserContext()
  await handleRefresh()
})
</script>

<style scoped>
.evaluation-rules-page {
  min-height: 100%;
}

.hero-shell {
  margin-bottom: 22px;
}

.hero-main {
  padding: 24px 28px;
  border-radius: 26px;
  box-sizing: border-box;
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

.section-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 248, 236, 0.96), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(212, 164, 88, 0.18);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card strong {
  font-size: 30px;
  line-height: 1;
  color: #8f3d15;
}

.summary-card span {
  font-weight: 700;
  color: #1f2937;
}

.summary-card p,
.muted {
  margin: 0;
  color: #6b7280;
}

.version-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.meta-label {
  display: block;
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 13px;
}

.collapse-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.tiny-flag-stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.double-grid,
.triple-grid {
  display: grid;
  gap: 16px;
}

.double-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.triple-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.workspace-section-head--wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 980px) {
  .double-grid,
  .triple-grid {
    grid-template-columns: 1fr;
  }

  .hero-main {
    padding: 24px;
  }
}
</style>
