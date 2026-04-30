<template>
  <div class="rule-achievement-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="workspace-hero__eyebrow">Rule Driven Achievement Entry</p>
        <h1 class="workspace-hero__title">教师成果录入中心</h1>
        <p class="workspace-hero__text hero-copy">
          按成果大类与加分项逐项录入事实信息，系统会自动限制字段、校验必填项，并预估积分。提交后进入学院管理员审核，
          审核通过后才正式进入教师成果与积分统计。
        </p>
      </div>
      <div class="workspace-page-actions">
        <el-button plain @click="router.push('/dashboard')">返回教师画像</el-button>
        <el-button type="primary" :loading="loading" @click="refreshAll">刷新数据</el-button>
      </div>
    </section>

    <section v-if="isAdminUser" class="workspace-content-shell">
      <el-result
        icon="info"
        title="当前入口面向教师录入"
        sub-title="学院管理员请通过“教师管理 / 成果审核”查看待审成果。"
      >
        <template #extra>
          <el-button type="primary" @click="router.push('/teachers/achievement-review')">进入成果审核</el-button>
        </template>
      </el-result>
    </section>

    <template v-else>
      <section class="workspace-content-shell entry-grid">
        <el-card shadow="never" class="workspace-surface-card">
          <template #header>
            <div class="workspace-section-head">
              <span>{{ editingId ? '编辑规则化成果' : '新增规则化成果' }}</span>
              <el-tag type="success" effect="plain">{{ entryConfig?.active_version.name || '未配置版本' }}</el-tag>
            </div>
          </template>

          <el-form label-position="top">
            <div class="double-grid">
              <el-form-item label="成果大类" required>
                <el-select v-model="form.categoryId" style="width: 100%">
                  <el-option v-for="item in categoryOptions" :key="item.id" :label="item.name" :value="item.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="加分项" required>
                <el-select v-model="form.ruleItemId" filterable style="width: 100%">
                  <el-option
                    v-for="item in filteredItemOptions"
                    :key="item.id"
                    :label="`${item.rule_code || '未编码'} · ${item.title}`"
                    :value="item.id"
                  />
                </el-select>
              </el-form-item>
            </div>

            <el-alert
              v-if="selectedCategory"
              v-show="false"
              type="info"
              :closable="false"
              show-icon
              class="form-alert"
            >
              <template #title>{{ selectedCategory?.name || '' }}</template>
              <template #default>
                <p>{{ selectedCategory.description || '请按正式成果材料逐项填写事实字段。' }}</p>
              </template>
            </el-alert>

            <el-alert
              v-if="selectedCategory"
              v-show="false"
              type="warning"
              :closable="false"
              show-icon
              class="form-alert"
              title="唯一识别信息按成果材料填写"
              description="项目、成果转化、平台团队等表单明确标注必填时必须填写；论文、获奖、智库、科普获奖等没有稳定编号时可留空，系统会结合题名、单位和时间辅助识别。"
            />

            <template v-for="section in selectedFormSections" :key="section.key">
              <div class="form-section">
                <div class="form-section__header">
                  <h3>{{ section.title }}</h3>
                  <p>{{ section.description }}</p>
                </div>
                <div class="dynamic-grid">
                  <div
                    v-for="field in section.fields"
                    :key="`${field.storage}:${field.key}`"
                    class="dynamic-grid__item"
                    :class="{ 'dynamic-grid__item--full': field.column_span >= 2 }"
                  >
                    <el-form-item :label="resolveFieldLabel(field)" :required="isEffectiveRequired(field)">
                      <template v-if="field.component === 'text'">
                        <el-input
                          :model-value="toTextValue(getFieldValue(field))"
                          :placeholder="resolveFieldPlaceholder(field)"
                          @update:model-value="setFieldValue(field, $event)"
                        />
                      </template>

                      <template v-else-if="field.component === 'textarea'">
                        <el-input
                          type="textarea"
                          :rows="3"
                          :model-value="toTextValue(getFieldValue(field))"
                          :placeholder="resolveFieldPlaceholder(field)"
                          @update:model-value="setFieldValue(field, $event)"
                        />
                      </template>

                      <template v-else-if="field.component === 'number'">
                        <el-input-number
                          :model-value="toNumberValue(getFieldValue(field))"
                          :min="field.min ?? 0"
                          :precision="field.precision ?? 0"
                          style="width: 100%"
                          @update:model-value="setFieldValue(field, $event)"
                        />
                      </template>

                      <template v-else-if="field.component === 'date'">
                        <el-date-picker
                          :model-value="toDateValue(getFieldValue(field))"
                          type="date"
                          value-format="YYYY-MM-DD"
                          style="width: 100%"
                          @update:model-value="setFieldValue(field, $event)"
                        />
                      </template>

                      <template v-else-if="field.component === 'select'">
                        <el-select
                          :model-value="toTextValue(getFieldValue(field))"
                          style="width: 100%"
                          clearable
                          :placeholder="resolveSelectPlaceholder(field)"
                          @update:model-value="setFieldValue(field, $event)"
                        >
                          <el-option
                            v-for="option in field.options"
                            :key="option.value"
                            :label="option.label"
                            :value="option.value"
                          />
                        </el-select>
                      </template>

                      <template v-else-if="field.component === 'boolean'">
                        <el-select
                          v-if="field.key === 'is_representative'"
                          :model-value="Boolean(getFieldValue(field))"
                          style="width: 100%"
                          @update:model-value="setFieldValue(field, $event)"
                        >
                          <el-option label="是" :value="true" />
                          <el-option label="否" :value="false" />
                        </el-select>
                        <el-switch
                          v-else
                          :model-value="Boolean(getFieldValue(field))"
                          @update:model-value="setFieldValue(field, $event)"
                        />
                      </template>

                      <div v-if="resolveFieldHelpText(field)" class="field-help">{{ resolveFieldHelpText(field) }}</div>
                    </el-form-item>
                  </div>
                </div>
              </div>
            </template>

            <div class="form-section">
              <div class="form-section__header">
                <h3>佐证说明与附件</h3>
                <p>只保留与当前成果直接相关的证明材料，避免上传无关截图或重复文件。</p>
              </div>
              <div class="dynamic-grid">
                <div class="dynamic-grid__item dynamic-grid__item--full">
                  <el-form-item label="佐证说明">
                    <el-input
                      v-model="form.evidenceNote"
                      type="textarea"
                      :rows="3"
                      placeholder="可补充到账说明、采纳情况、署名说明、单位排序说明等"
                    />
                  </el-form-item>
                </div>
                <div class="dynamic-grid__item dynamic-grid__item--full">
                  <el-form-item label="上传佐证材料">
                    <el-upload
                      multiple
                      :auto-upload="false"
                      :limit="6"
                      :on-change="handleUploadChange"
                      :on-remove="handleUploadRemove"
                      :file-list="uploadList"
                    >
                      <el-button type="primary" plain>选择文件</el-button>
                      <template #tip>
                        <div class="el-upload__tip">编辑成果时重新选择文件，会替换当前附件。</div>
                      </template>
                    </el-upload>
                    <div v-if="editingId && existingAttachments.length" class="existing-attachments">
                      <span class="muted">当前已上传：</span>
                      <el-link v-for="item in existingAttachments" :key="item.id" :href="item.file_url" target="_blank" type="primary">
                        {{ item.original_name || item.file }}
                      </el-link>
                    </div>
                  </el-form-item>
                </div>
              </div>
            </div>

            <div class="actions">
              <el-button @click="resetForm">{{ editingId ? '取消编辑' : '重置' }}</el-button>
              <el-button type="primary" :loading="submitting" @click="submitForm">
                {{ editingId ? '更新并重新提交审核' : '提交并进入审核' }}
              </el-button>
            </div>
          </el-form>
        </el-card>

      </section>

      <section class="workspace-content-shell">
        <el-card shadow="never" class="workspace-surface-card">
          <template #header>
            <div class="workspace-section-head workspace-section-head--wrap">
              <span>我的规则化成果</span>
              <el-tag effect="plain">{{ records.length }} 条</el-tag>
            </div>
          </template>

          <div class="record-summary-grid">
            <div class="record-summary-item">
              <span>待审核成果</span>
              <strong>{{ pendingRecordCount }} 条</strong>
              <p>待审核预估积分 {{ pendingScoreTotal.toFixed(2) }} 分</p>
            </div>
            <div class="record-summary-item">
              <span>已通过成果</span>
              <strong>{{ approvedRecordCount }} 条</strong>
              <p>已生效积分 {{ approvedScoreTotal.toFixed(2) }} 分</p>
            </div>
            <div class="record-summary-item">
              <span>已驳回成果</span>
              <strong>{{ rejectedRecordCount }} 条</strong>
              <p>驳回成果不计入教师积分与画像</p>
            </div>
          </div>

          <el-table :data="records" row-key="id" v-loading="loading" empty-text="暂无成果记录">
            <el-table-column prop="title" label="成果名称" min-width="220" />
            <el-table-column prop="category_name" label="成果大类" width="150" />
            <el-table-column prop="rule_item_title" label="加分项" min-width="220" />
            <el-table-column prop="provisional_score" label="预估积分" width="100" />
            <el-table-column prop="final_score" label="生效积分" width="100" />
            <el-table-column label="审核状态" width="120">
              <template #default="{ row }">
                <el-tag :type="resolveStatusTag(row.status)" effect="plain">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="date_acquired" label="成果时间" width="120" />
            <el-table-column label="操作" width="170">
              <template #default="{ row }">
                <el-button link type="primary" @click="startEdit(row)">编辑</el-button>
                <el-button link type="info" @click="openHistory(row)">流转</el-button>
                <el-button link type="danger" @click="removeRecord(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </section>

      <el-dialog v-model="historyDialogVisible" title="成果流转记录" width="780px">
        <el-timeline v-if="workflowHistory.length">
          <el-timeline-item
            v-for="item in workflowHistory"
            :key="item.id"
            :timestamp="formatDateTime(item.created_at)"
            placement="top"
          >
            <strong>{{ item.action_label }}</strong>
            <p>{{ item.summary }}</p>
            <p v-if="item.operator_name" class="muted">操作人：{{ item.operator_name }}</p>
            <p v-if="item.review_comment" class="muted">审核意见：{{ item.review_comment }}</p>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无流转记录" :image-size="100" />
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile, UploadFiles } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type {
  RuleAchievementAttachment,
  RuleAchievementEntryConfigResponse,
  RuleAchievementFormFieldSchema,
  RuleAchievementFormSectionSchema,
  RuleAchievementItemOption,
  RuleAchievementRecord,
} from '../types/ruleAchievements'
import {
  createRuleAchievement,
  deleteRuleAchievement,
  fetchRuleAchievementEntryConfig,
  fetchRuleAchievementWorkflow,
  fetchRuleAchievements,
  updateRuleAchievement,
} from './rule-achievements/api'

const router = useRouter()
const sessionUser = ref<SessionUser | null>(null)
const loading = ref(false)
const submitting = ref(false)
const entryConfig = ref<RuleAchievementEntryConfigResponse | null>(null)
const records = ref<RuleAchievementRecord[]>([])
const editingId = ref<number | null>(null)
const historyDialogVisible = ref(false)
const workflowHistory = ref<
  Array<{
    id: number
    action_label: string
    summary: string
    operator_name: string
    review_comment: string
    created_at: string
  }>
>([])
const uploadFiles = ref<File[]>([])
const uploadList = ref<UploadFile[]>([])
const existingAttachments = ref<RuleAchievementAttachment[]>([])
const factualPayload = ref<Record<string, unknown>>({})
const preservedFactualPayload = ref<Record<string, unknown>>({})
const hydratingSchema = ref(false)

const form = reactive({
  categoryId: null as number | null,
  ruleItemId: null as number | null,
  title: '',
  externalReference: '',
  dateAcquired: '',
  issuingOrganization: '',
  publicationName: '',
  roleText: '',
  authorRank: null as number | null,
  isCorrespondingAuthor: false,
  isRepresentative: false,
  schoolUnitOrder: '',
  amountValue: null as number | null,
  keywordsText: '',
  coauthorNamesText: '',
  teamIdentifier: '',
  teamTotalMembers: null as number | null,
  teamAllocatedScore: null as number | null,
  teamContributionNote: '',
  evidenceNote: '',
})

const ROOT_FIELD_KEY_MAP = {
  title: 'title',
  external_reference: 'externalReference',
  date_acquired: 'dateAcquired',
  issuing_organization: 'issuingOrganization',
  publication_name: 'publicationName',
  role_text: 'roleText',
  author_rank: 'authorRank',
  is_corresponding_author: 'isCorrespondingAuthor',
  is_representative: 'isRepresentative',
  school_unit_order: 'schoolUnitOrder',
  amount_value: 'amountValue',
  keywords_text: 'keywordsText',
  coauthor_names: 'coauthorNamesText',
  team_identifier: 'teamIdentifier',
  team_total_members: 'teamTotalMembers',
  team_allocated_score: 'teamAllocatedScore',
  team_contribution_note: 'teamContributionNote',
  evidence_note: 'evidenceNote',
} as const

const uniqueIdentifierLabelMap: Record<string, string> = {
  PAPER_BOOK: 'DOI / ISBN / 检索号 / 刊号',
  PROJECT: '项目编号 / 合同编号 / 任务书编号',
  AWARD: '证书编号 / 通知文号',
  TRANSFORMATION: '专利号 / 标准号 / 合同号 / 登记号',
  THINK_TANK: '批示编号 / 刊发编号 / 采纳编号',
  PLATFORM_TEAM: '认定文号 / 正式编号',
  SCI_POP_AWARD: '证书编号 / 通知文号',
}

const uniqueIdentifierPlaceholderMap: Record<string, string> = {
  PAPER_BOOK: '如有 DOI、ISBN、检索号或刊号请填写',
  PROJECT: '请填写立项编号、合同编号或任务书编号',
  AWARD: '如有证书编号或通知文号请填写',
  TRANSFORMATION: '请填写专利号、标准号、合同号或登记号',
  THINK_TANK: '如有批示编号、刊发编号或采纳编号请填写',
  PLATFORM_TEAM: '请填写认定文号或正式编号',
  SCI_POP_AWARD: '如有证书编号或通知文号请填写',
}

const requiredUniqueIdentifierHelpText =
  '当前成果类别需要正式编号或正式标识来完成审核与去重，请与立项、合同、授权、登记或认定材料保持一致。'
const optionalUniqueIdentifierHelpText =
  '如正式材料中有编号或稳定标识请填写；没有时可留空，系统会结合成果名称、单位、时间等信息辅助识别。'
const teamIdentifierHelpText =
  '同一平台或团队由不同教师分别录入时，团队归并标识必须保持完全一致，建议使用“平台/团队名称 + 认定文号”。'

const isAdminUser = computed(() => Boolean(sessionUser.value?.is_admin))
const categoryOptions = computed(() => entryConfig.value?.categories || [])
const itemOptions = computed(() => entryConfig.value?.items || [])
const selectedCategory = computed(() => categoryOptions.value.find(item => item.id === form.categoryId))
const currentCategoryCode = computed(() => (selectedCategory.value?.code || '').trim().toUpperCase())
const filteredItemOptions = computed(() => itemOptions.value.filter(item => item.category_id === form.categoryId))
const selectedRuleItem = computed<RuleAchievementItemOption | undefined>(() => itemOptions.value.find(item => item.id === form.ruleItemId))
const selectedFormSections = computed<RuleAchievementFormSectionSchema[]>(() => selectedRuleItem.value?.resolved_entry_form_schema || [])
const visibleFactualKeys = computed(
  () =>
    new Set(
      selectedFormSections.value
        .flatMap(section => section.fields)
        .filter(field => field.storage === 'factual_payload')
        .map(field => field.key),
    ),
)
const approvedRecordCount = computed(() => records.value.filter(item => item.status === 'APPROVED').length)
const pendingRecordCount = computed(() => records.value.filter(item => item.status === 'PENDING_REVIEW').length)
const rejectedRecordCount = computed(() => records.value.filter(item => item.status === 'REJECTED').length)
const approvedScoreTotal = computed(() =>
  records.value
    .filter(item => item.status === 'APPROVED')
    .reduce((sum, item) => sum + Number(item.final_score || 0), 0),
)
const pendingScoreTotal = computed(() =>
  records.value
    .filter(item => item.status === 'PENDING_REVIEW')
    .reduce((sum, item) => sum + Number(item.provisional_score || 0), 0),
)

const isRootSchemaField = (key: string): key is keyof typeof ROOT_FIELD_KEY_MAP => key in ROOT_FIELD_KEY_MAP

const splitTextList = (raw: string) =>
  raw
    .split(/[，,\n]+/)
    .map(item => item.trim())
    .filter(Boolean)

const defaultFieldValue = (field: RuleAchievementFormFieldSchema) => {
  if (field.component === 'boolean') return false
  if (field.component === 'number') return null
  return ''
}

const toTextValue = (value: unknown) => (value === null || value === undefined ? '' : String(value))
const toNumberValue = (value: unknown) => (value === '' || value === null || value === undefined ? null : Number(value))
const toDateValue = (value: unknown) => (value ? String(value) : '')
const resolveUniqueIdentifierLabel = () =>
  uniqueIdentifierLabelMap[currentCategoryCode.value] || '成果唯一识别信息'
const resolveUniqueIdentifierPlaceholder = () =>
  uniqueIdentifierPlaceholderMap[currentCategoryCode.value] || '请填写成果正式编号或正式标识'

const isEffectiveRequired = (field: RuleAchievementFormFieldSchema) => field.required

const resolveFieldLabel = (field: RuleAchievementFormFieldSchema) => {
  if (field.key === 'external_reference') {
    return resolveUniqueIdentifierLabel()
  }
  return field.label
}

const resolveFieldPlaceholder = (field: RuleAchievementFormFieldSchema) => {
  if (field.key === 'external_reference') {
    return resolveUniqueIdentifierPlaceholder()
  }
  return field.placeholder
}

const resolveFieldHelpText = (field: RuleAchievementFormFieldSchema) => {
  if (field.key === 'external_reference') {
    return isEffectiveRequired(field) ? requiredUniqueIdentifierHelpText : optionalUniqueIdentifierHelpText
  }
  if (field.key === 'team_identifier') {
    return field.help_text || teamIdentifierHelpText
  }
  return field.help_text
}

const resolveSelectPlaceholder = (field: RuleAchievementFormFieldSchema) =>
  field.placeholder || `请选择${resolveFieldLabel(field)}`

const getRootFieldValue = (schemaKey: string) => {
  if (!isRootSchemaField(schemaKey)) return undefined
  const localKey = ROOT_FIELD_KEY_MAP[schemaKey]
  return (form as Record<string, unknown>)[localKey]
}

const setRootFieldValue = (schemaKey: string, value: unknown) => {
  if (!isRootSchemaField(schemaKey)) return
  const localKey = ROOT_FIELD_KEY_MAP[schemaKey]
  if (schemaKey === 'coauthor_names' || schemaKey === 'keywords_text') {
    ;(form as Record<string, unknown>)[localKey] = typeof value === 'string' ? value : ''
    return
  }
  ;(form as Record<string, unknown>)[localKey] = value as never
}

const getFieldValue = (field: RuleAchievementFormFieldSchema) => {
  if (field.storage === 'root') {
    const rootValue = getRootFieldValue(field.key)
    return rootValue === undefined ? defaultFieldValue(field) : rootValue
  }
  return field.key in factualPayload.value ? factualPayload.value[field.key] : defaultFieldValue(field)
}

const setFieldValue = (field: RuleAchievementFormFieldSchema, value: unknown) => {
  if (field.storage === 'root') {
    setRootFieldValue(field.key, value)
    return
  }
  factualPayload.value = {
    ...factualPayload.value,
    [field.key]: value,
  }
}

const rebaseDynamicPayload = () => {
  const nextPayload: Record<string, unknown> = {}
  for (const key of visibleFactualKeys.value) {
    if (key in factualPayload.value) {
      nextPayload[key] = factualPayload.value[key]
    }
  }
  factualPayload.value = nextPayload
}

const ensureRuleSelection = () => {
  if (!form.categoryId && categoryOptions.value.length) {
    form.categoryId = categoryOptions.value[0]?.id || null
  }
  if (!filteredItemOptions.value.find(item => item.id === form.ruleItemId)) {
    form.ruleItemId = filteredItemOptions.value[0]?.id || null
  }
}

const resetForm = () => {
  editingId.value = null
  existingAttachments.value = []
  uploadFiles.value = []
  uploadList.value = []
  factualPayload.value = {}
  preservedFactualPayload.value = {}
  Object.assign(form, {
    categoryId: categoryOptions.value[0]?.id || null,
    ruleItemId: null,
    title: '',
    externalReference: '',
    dateAcquired: '',
    issuingOrganization: '',
    publicationName: '',
    roleText: '',
    authorRank: null,
    isCorrespondingAuthor: false,
    isRepresentative: false,
    schoolUnitOrder: '',
    amountValue: null,
    keywordsText: '',
    coauthorNamesText: '',
    teamIdentifier: '',
    teamTotalMembers: null,
    teamAllocatedScore: null,
    teamContributionNote: '',
    evidenceNote: '',
  })
  ensureRuleSelection()
}

const loadEntryConfig = async () => {
  entryConfig.value = await fetchRuleAchievementEntryConfig()
  ensureRuleSelection()
}

const loadRecords = async () => {
  records.value = await fetchRuleAchievements()
}

const refreshAll = async () => {
  loading.value = true
  try {
    await loadEntryConfig()
    if (!isAdminUser.value) {
      await loadRecords()
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('成果数据加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => form.categoryId,
  () => {
    ensureRuleSelection()
    if (!hydratingSchema.value) {
      preservedFactualPayload.value = {}
      rebaseDynamicPayload()
    }
  },
)

watch(
  () => form.ruleItemId,
  () => {
    if (!hydratingSchema.value) {
      preservedFactualPayload.value = {}
      rebaseDynamicPayload()
    }
  },
)

const buildSubmittedFactualPayload = () => {
  const payload: Record<string, unknown> = { ...preservedFactualPayload.value }
  for (const key of visibleFactualKeys.value) {
    payload[key] = factualPayload.value[key] ?? ''
  }
  return payload
}

const collectMissingLabels = () => {
  const missing: string[] = []
  for (const section of selectedFormSections.value) {
    for (const field of section.fields) {
      if (!isEffectiveRequired(field)) continue
      const value = getFieldValue(field)
      const empty =
        value === null ||
        value === undefined ||
        (typeof value === 'string' && !value.trim()) ||
        (Array.isArray(value) && value.length === 0)
      if (empty) {
        missing.push(resolveFieldLabel(field))
      }
    }
  }
  return missing
}

const buildFormData = () => {
  const payload = new FormData()
  if (form.categoryId) payload.append('category', String(form.categoryId))
  if (form.ruleItemId) payload.append('rule_item', String(form.ruleItemId))
  payload.append('title', form.title.trim())
  payload.append('external_reference', form.externalReference.trim())
  payload.append('date_acquired', form.dateAcquired)
  payload.append('issuing_organization', form.issuingOrganization.trim())
  payload.append('publication_name', form.publicationName.trim())
  payload.append('role_text', form.roleText.trim())
  if (form.authorRank) payload.append('author_rank', String(form.authorRank))
  payload.append('is_corresponding_author', String(form.isCorrespondingAuthor))
  payload.append('is_representative', String(form.isRepresentative))
  payload.append('school_unit_order', form.schoolUnitOrder.trim())
  if (form.amountValue !== null && form.amountValue !== undefined) payload.append('amount_value', String(form.amountValue))
  payload.append('keywords_text', form.keywordsText.trim())
  payload.append('coauthor_names', JSON.stringify(splitTextList(form.coauthorNamesText)))
  payload.append('team_identifier', form.teamIdentifier.trim())
  if (form.teamTotalMembers) payload.append('team_total_members', String(form.teamTotalMembers))
  if (form.teamAllocatedScore !== null && form.teamAllocatedScore !== undefined) payload.append('team_allocated_score', String(form.teamAllocatedScore))
  payload.append('team_contribution_note', form.teamContributionNote.trim())
  payload.append('evidence_note', form.evidenceNote.trim())
  payload.append('factual_payload', JSON.stringify(buildSubmittedFactualPayload()))
  uploadFiles.value.forEach(file => payload.append('evidence_files', file))
  return payload
}

const submitForm = async () => {
  if (!form.categoryId || !form.ruleItemId) {
    ElMessage.warning('请先选择成果大类和加分项')
    return
  }

  const missingLabels = collectMissingLabels()
  if (missingLabels.length) {
    ElMessage.warning(`请先补全：${missingLabels.slice(0, 4).join('、')}${missingLabels.length > 4 ? ' 等字段' : ''}`)
    return
  }

  submitting.value = true
  try {
    const payload = buildFormData()
    if (editingId.value) {
      await updateRuleAchievement(editingId.value, payload)
      ElMessage.success('成果已更新，并重新进入审核')
    } else {
      await createRuleAchievement(payload)
      ElMessage.success('成果已提交，等待学院管理员审核')
    }
    resetForm()
    await loadRecords()
  } catch (error) {
    console.error(error)
    ElMessage.error('成果提交失败')
  } finally {
    submitting.value = false
  }
}

const extractVisibleFactualPayload = (payload: Record<string, unknown>) => {
  const nextPayload: Record<string, unknown> = {}
  for (const key of visibleFactualKeys.value) {
    if (key in payload) {
      nextPayload[key] = payload[key]
    }
  }
  return nextPayload
}

const startEdit = (row: RuleAchievementRecord) => {
  hydratingSchema.value = true
  editingId.value = row.id
  existingAttachments.value = row.attachments || []
  uploadFiles.value = []
  uploadList.value = []
  Object.assign(form, {
    categoryId: row.category,
    ruleItemId: row.rule_item,
    title: row.title,
    externalReference: row.external_reference,
    dateAcquired: row.date_acquired,
    issuingOrganization: row.issuing_organization,
    publicationName: row.publication_name,
    roleText: row.role_text,
    authorRank: row.author_rank,
    isCorrespondingAuthor: row.is_corresponding_author,
    isRepresentative: row.is_representative,
    schoolUnitOrder: row.school_unit_order,
    amountValue: row.amount_value === null || row.amount_value === '' ? null : Number(row.amount_value),
    keywordsText: row.keywords_text,
    coauthorNamesText: (row.coauthor_names || []).join('，'),
    teamIdentifier: row.team_identifier,
    teamTotalMembers: row.team_total_members,
    teamAllocatedScore: row.team_allocated_score === null || row.team_allocated_score === '' ? null : Number(row.team_allocated_score),
    teamContributionNote: row.team_contribution_note,
    evidenceNote: row.evidence_note,
  })
  preservedFactualPayload.value = { ...(row.factual_payload || {}) }
  factualPayload.value = extractVisibleFactualPayload(row.factual_payload || {})
  hydratingSchema.value = false
}

const removeRecord = async (id: number) => {
  try {
    await ElMessageBox.confirm('删除后将移出当前规则成果链路，确认继续吗？', '删除确认', { type: 'warning' })
    await deleteRuleAchievement(id)
    ElMessage.success('成果已删除')
    if (editingId.value === id) resetForm()
    await loadRecords()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('成果删除失败')
    }
  }
}

const openHistory = async (row: RuleAchievementRecord) => {
  try {
    const data = await fetchRuleAchievementWorkflow(row.id)
    workflowHistory.value = data.history || []
    historyDialogVisible.value = true
  } catch (error) {
    console.error(error)
    ElMessage.error('流转记录加载失败')
  }
}

const collectUploadFiles = (files: UploadFiles): File[] =>
  files.flatMap(item => (item.raw ? [item.raw as File] : []))

const handleUploadChange = (_file: UploadFile, files: UploadFiles) => {
  uploadList.value = files
  uploadFiles.value = collectUploadFiles(files)
}

const handleUploadRemove = (_file: UploadFile, files: UploadFiles) => {
  uploadList.value = files
  uploadFiles.value = collectUploadFiles(files)
}

const resolveStatusTag = (status: string) => {
  if (status === 'APPROVED') return 'success'
  if (status === 'REJECTED') return 'danger'
  return 'warning'
}

const formatDateTime = (value?: string) => {
  if (!value) return '未记录'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  sessionUser.value = await ensureSessionUserContext()
  await refreshAll()
  if (!editingId.value) {
    resetForm()
  }
})
</script>

<style scoped>
.rule-achievement-page {
  min-height: 100%;
}

.hero-copy {
  max-width: 760px;
}

.entry-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.double-grid,
.dynamic-grid,
.record-summary-grid {
  display: grid;
  gap: 16px;
}

.double-grid,
.dynamic-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dynamic-grid__item--full {
  grid-column: 1 / -1;
}

.form-section {
  margin-bottom: 20px;
}

.form-section__header {
  margin-bottom: 12px;
}

.form-section__header h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: var(--text-primary);
}

.form-section__header p,
.field-help,
.muted,
.preview-label {
  color: var(--text-tertiary);
}

.field-help {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
}

.actions,
.existing-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.actions {
  justify-content: flex-end;
}

.preview-card {
  height: fit-content;
}

.preview-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-score {
  font-size: 28px;
  color: #1d4ed8;
}

.form-alert {
  margin-bottom: 16px;
}

.record-summary-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 16px;
}

.record-summary-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
  display: grid;
  gap: 6px;
}

.record-summary-item span,
.record-summary-item p {
  color: var(--text-tertiary);
}

.record-summary-item strong {
  color: var(--text-primary);
  font-size: 24px;
}

.record-summary-item p {
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .entry-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .double-grid,
  .dynamic-grid,
  .record-summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
