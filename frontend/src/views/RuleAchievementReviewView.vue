<template>
  <div class="rule-achievement-review-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="workspace-hero__eyebrow">Rule Achievement Review</p>
        <h1 class="workspace-hero__title">成果审核</h1>
        <p class="workspace-hero__text">
          审核教师按核心科研能力规则提交的成果事实。只有审核通过后的成果，才会正式计入教师成果库与积分统计。
          <span v-if="sessionUser?.department">当前范围：{{ sessionUser.department }}</span>
        </p>
      </div>
      <div class="workspace-page-actions">
        <el-button plain @click="router.push('/teachers')">返回教师管理</el-button>
        <el-button type="primary" :loading="loading" @click="refreshAll">刷新待审</el-button>
      </div>
    </section>

    <section v-if="!canReview" class="workspace-content-shell">
      <el-result icon="warning" title="无审核权限" sub-title="当前账号不具备规则化成果审核权限。" />
    </section>

    <section v-else class="workspace-content-shell">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="workspace-section-head">
            <span>待审核成果</span>
            <el-tag type="warning" effect="plain">{{ records.length }} 条</el-tag>
          </div>
        </template>

        <el-table :data="records" row-key="id" v-loading="loading" empty-text="暂无待审核成果">
          <el-table-column prop="teacher_name" label="教师" width="120" />
          <el-table-column prop="title" label="成果名称" min-width="220" />
          <el-table-column prop="category_name" label="成果大类" width="140" />
          <el-table-column prop="rule_item_title" label="加分项" min-width="220" />
          <el-table-column prop="provisional_score" label="建议分数" width="110" />
          <el-table-column prop="date_acquired" label="成果时间" width="120" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
              <el-button link type="danger" @click="openRejectDialog(row)">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <el-dialog v-model="detailDialogVisible" title="成果审核详情" width="960px" destroy-on-close>
      <template v-if="currentRecord">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          class="detail-alert"
          :title="`${currentRecord.category_name} / ${currentRecord.rule_item_title}`"
          :description="`规则积分：${currentRecord.score_preview.score_text || '未配置'}；系统建议分数：${resolveSuggestedScore(currentRecord)} 分。`"
        />

        <el-descriptions :column="2" border class="detail-descriptions">
          <el-descriptions-item label="教师">{{ currentRecord.teacher_name }}</el-descriptions-item>
          <el-descriptions-item label="成果名称">{{ currentRecord.title }}</el-descriptions-item>
          <el-descriptions-item label="成果大类">{{ currentRecord.category_name }}</el-descriptions-item>
          <el-descriptions-item label="加分项">{{ currentRecord.rule_item_title }}</el-descriptions-item>
          <el-descriptions-item label="成果时间">{{ currentRecord.date_acquired }}</el-descriptions-item>
          <el-descriptions-item label="建议分数">{{ resolveSuggestedScore(currentRecord) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <div class="detail-section__head">
            <strong>审核计分</strong>
            <p>系统先依据规则给出建议分数，学院管理员核对材料后填写最终分数，再执行审核通过。</p>
          </div>
          <div class="score-review-card">
            <div class="score-review-card__meta">
              <span>系统建议分数</span>
              <strong>{{ resolveSuggestedScore(currentRecord) }}</strong>
            </div>
            <el-form label-position="top" class="score-review-form">
              <el-form-item label="最终分数" required>
                <el-input-number
                  v-model="finalScoreDraft"
                  :min="0"
                  :precision="2"
                  :step="0.5"
                  style="width: 100%"
                />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div v-for="section in currentFormSections" :key="section.key" class="detail-section">
          <div class="detail-section__head">
            <strong>{{ section.title }}</strong>
            <p>{{ section.description }}</p>
          </div>

          <div class="detail-grid">
            <div
              v-for="field in section.fields"
              :key="`${section.key}-${field.storage}-${field.key}`"
              class="detail-grid__item"
              :class="{ 'detail-grid__item--full': field.column_span >= 2 }"
            >
              <span class="detail-grid__label">{{ field.label }}</span>
              <div class="detail-grid__value">
                <template v-if="Array.isArray(resolveRecordFieldValue(currentRecord, field))">
                  <div class="tag-list">
                    <el-tag
                      v-for="item in resolveRecordFieldValue(currentRecord, field) as string[]"
                      :key="`${field.key}-${item}`"
                      size="small"
                      effect="plain"
                    >
                      {{ item }}
                    </el-tag>
                    <span v-if="!(resolveRecordFieldValue(currentRecord, field) as string[]).length" class="muted">未填写</span>
                  </div>
                </template>
                <template v-else>
                  <span>{{ formatFieldDisplay(resolveRecordFieldValue(currentRecord, field), field) }}</span>
                </template>
              </div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section__head">
            <strong>系统计分提示</strong>
          </div>
          <div class="detail-note-list">
            <p v-for="note in currentRecord.score_preview.notes" :key="note">{{ note }}</p>
            <p v-if="!currentRecord.score_preview.notes.length" class="muted">当前无额外计分提示。</p>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section__head">
            <strong>佐证说明与附件</strong>
          </div>
          <p class="detail-note">{{ currentRecord.evidence_note || '未填写佐证说明。' }}</p>
          <div v-if="currentRecord.attachments.length" class="attachment-links">
            <el-link
              v-for="item in currentRecord.attachments"
              :key="item.id"
              :href="item.file_url"
              target="_blank"
              type="primary"
            >
              {{ item.original_name || item.file }}
            </el-link>
          </div>
          <p v-else class="muted">当前未上传附件。</p>
        </div>
      </template>
      <template #footer v-if="currentRecord">
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="danger" plain @click="openRejectDialog(currentRecord)">驳回</el-button>
        <el-button type="primary" :loading="submitting" @click="approveRecord">审核通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectDialogVisible" title="驳回成果" width="520px">
      <el-form label-position="top">
        <el-form-item label="驳回原因">
          <el-input v-model="rejectReason" type="textarea" :rows="4" placeholder="请填写驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type {
  RuleAchievementEntryConfigResponse,
  RuleAchievementFormFieldSchema,
  RuleAchievementFormSectionSchema,
  RuleAchievementRecord,
} from '../types/ruleAchievements'
import {
  approveRuleAchievement,
  fetchPendingRuleAchievements,
  fetchRuleAchievementEntryConfig,
  rejectRuleAchievement,
} from './rule-achievements/api'

const router = useRouter()
const sessionUser = ref<SessionUser | null>(null)
const loading = ref(false)
const submitting = ref(false)
const records = ref<RuleAchievementRecord[]>([])
const entryConfig = ref<RuleAchievementEntryConfigResponse | null>(null)
const currentRecord = ref<RuleAchievementRecord | null>(null)
const detailDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejectTargetId = ref<number | null>(null)
const finalScoreDraft = ref<number | null>(null)

const ROOT_FIELD_KEY_MAP = {
  title: 'title',
  external_reference: 'external_reference',
  date_acquired: 'date_acquired',
  issuing_organization: 'issuing_organization',
  publication_name: 'publication_name',
  role_text: 'role_text',
  author_rank: 'author_rank',
  is_corresponding_author: 'is_corresponding_author',
  is_representative: 'is_representative',
  school_unit_order: 'school_unit_order',
  amount_value: 'amount_value',
  keywords_text: 'keywords_text',
  coauthor_names: 'coauthor_names',
  team_identifier: 'team_identifier',
  team_total_members: 'team_total_members',
  team_allocated_score: 'team_allocated_score',
  team_contribution_note: 'team_contribution_note',
  evidence_note: 'evidence_note',
} as const

const canReview = computed(() => Boolean(sessionUser.value?.role_code === 'college_admin' || sessionUser.value?.role_code === 'admin'))
const schemaMap = computed(() => {
  const map = new Map<number, RuleAchievementFormSectionSchema[]>()
  for (const item of entryConfig.value?.items || []) {
    map.set(item.id, item.resolved_entry_form_schema || [])
  }
  return map
})
const currentFormSections = computed<RuleAchievementFormSectionSchema[]>(() =>
  currentRecord.value ? schemaMap.value.get(currentRecord.value.rule_item) || [] : [],
)
const resolveSuggestedScore = (record: RuleAchievementRecord | null) =>
  record?.provisional_score || record?.score_preview?.preview_score || '0.00'

const loadConfig = async () => {
  entryConfig.value = await fetchRuleAchievementEntryConfig()
}

const loadRecords = async () => {
  if (!canReview.value) return
  loading.value = true
  try {
    records.value = await fetchPendingRuleAchievements()
  } catch (error) {
    console.error(error)
    ElMessage.error('待审核成果加载失败')
  } finally {
    loading.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([loadConfig(), loadRecords()])
}

const approveRecord = async () => {
  if (!currentRecord.value) return
  if (finalScoreDraft.value === null || Number.isNaN(finalScoreDraft.value) || finalScoreDraft.value < 0) {
    ElMessage.warning('请先确认最终分数')
    return
  }
  const id = currentRecord.value.id
  const finalScore = Number(finalScoreDraft.value)
  submitting.value = true
  try {
    await approveRuleAchievement(id, finalScore)
    ElMessage.success('审核通过后，该成果已正式计入教师成果与积分统计。')
    await loadRecords()
    if (currentRecord.value?.id === id) {
      detailDialogVisible.value = false
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('审核通过失败')
  } finally {
    submitting.value = false
  }
}

const openDetail = (row: RuleAchievementRecord) => {
  currentRecord.value = row
  finalScoreDraft.value = Number(resolveSuggestedScore(row))
  detailDialogVisible.value = true
}

const openRejectDialog = (row: RuleAchievementRecord) => {
  rejectTargetId.value = row.id
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

const confirmReject = async () => {
  if (!rejectTargetId.value || !rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  submitting.value = true
  try {
    await rejectRuleAchievement(rejectTargetId.value, rejectReason.value.trim())
    ElMessage.success('成果已驳回')
    rejectDialogVisible.value = false
    if (currentRecord.value?.id === rejectTargetId.value) {
      detailDialogVisible.value = false
    }
    await loadRecords()
  } catch (error) {
    console.error(error)
    ElMessage.error('成果驳回失败')
  } finally {
    submitting.value = false
  }
}

const resolveRecordFieldValue = (record: RuleAchievementRecord, field: RuleAchievementFormFieldSchema): unknown => {
  if (field.storage === 'root') {
    const rootKey = ROOT_FIELD_KEY_MAP[field.key as keyof typeof ROOT_FIELD_KEY_MAP]
    return rootKey ? record[rootKey] : undefined
  }
  return record.factual_payload?.[field.key]
}

const resolveOptionLabel = (field: RuleAchievementFormFieldSchema, value: unknown) => {
  const rawValue = value === null || value === undefined ? '' : String(value)
  const target = field.options.find(option => option.value === rawValue)
  return target?.label || rawValue
}

const formatFieldDisplay = (value: unknown, field: RuleAchievementFormFieldSchema) => {
  if (value === null || value === undefined || value === '') {
    return '未填写'
  }
  if (field.component === 'boolean') {
    return value ? '是' : '否'
  }
  if (field.component === 'select') {
    return resolveOptionLabel(field, value)
  }
  return String(value)
}

onMounted(async () => {
  sessionUser.value = await ensureSessionUserContext()
  await refreshAll()
})
</script>

<style scoped>
.rule-achievement-review-page {
  min-height: 100%;
}

.detail-alert,
.detail-descriptions,
.detail-section + .detail-section {
  margin-top: 16px;
}

.detail-section {
  display: grid;
  gap: 12px;
}

.detail-section__head {
  display: grid;
  gap: 6px;
}

.detail-section__head p,
.muted,
.detail-note {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-grid__item {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
  display: grid;
  gap: 8px;
}

.detail-grid__item--full {
  grid-column: 1 / -1;
}

.detail-grid__label {
  color: var(--text-tertiary);
  font-size: 13px;
}

.detail-grid__value {
  color: var(--text-primary);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-note-list {
  display: grid;
  gap: 8px;
}

.score-review-card {
  display: grid;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
}

.score-review-card__meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.score-review-card__meta span {
  color: var(--text-tertiary);
}

.score-review-card__meta strong {
  font-size: 24px;
  color: var(--brand-primary);
}

.score-review-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.detail-note-list p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.attachment-links,
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
