<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../../utils/sessionAuth'
import { resolveApiErrorMessage } from '../../utils/apiFeedback.js'

interface AchievementClaimRecord {
  id: number
  achievement_id: number
  achievement_title: string
  achievement_abstract: string
  achievement_date_acquired: string
  achievement_journal: string
  achievement_status: string
  initiator_name: string
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'CONFLICT'
  status_label: string
  pending_days: number
  created_at: string
  proposed_order?: number | null
  proposed_author_rank?: number | null
  proposed_is_corresponding?: boolean
}

interface AchievementClaimListResponse {
  records: AchievementClaimRecord[]
}

const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const processingIds = ref<number[]>([])
const records = ref<AchievementClaimRecord[]>([])

const dialogVisible = ref(false)
const activeClaim = ref<AchievementClaimRecord | null>(null)
const claimMode = ref<'direct' | 'edit'>('direct')
const claimForm = reactive({
  actual_order: 1,
  actual_is_corresponding: false,
  confirmation_note: '',
})

const processingIdSet = computed(() => new Set(processingIds.value))
const isAdminUser = computed(() => currentUser.value?.is_admin === true)

const withProcessing = async (claimId: number, handler: () => Promise<void>) => {
  processingIds.value = Array.from(new Set([...processingIds.value, claimId]))
  try {
    await handler()
  } finally {
    processingIds.value = processingIds.value.filter(id => id !== claimId)
  }
}

const getProposedOrder = (item: AchievementClaimRecord): number | null => {
  if (typeof item.proposed_order === 'number') return item.proposed_order
  if (typeof item.proposed_author_rank === 'number') return item.proposed_author_rank
  return null
}

const loadClaims = async () => {
  if (isAdminUser.value) {
    records.value = []
    return
  }
  loading.value = true
  try {
    const { data } = await axios.get<AchievementClaimListResponse>('/api/achievements/claims/pending/')
    records.value = data.records ?? []
  } catch (error: any) {
    ElMessage.error(resolveApiErrorMessage(error, '待认领成果加载失败'))
  } finally {
    loading.value = false
  }
}

const openClaimDialog = (item: AchievementClaimRecord) => {
  activeClaim.value = item
  claimMode.value = 'direct'
  claimForm.actual_order = getProposedOrder(item) || 1
  claimForm.actual_is_corresponding = Boolean(item.proposed_is_corresponding)
  claimForm.confirmation_note = ''
  dialogVisible.value = true
}

const submitClaim = async () => {
  if (!activeClaim.value) return

  if (claimMode.value === 'edit' && (!Number.isFinite(claimForm.actual_order) || claimForm.actual_order < 1)) {
    ElMessage.warning('请填写正确的作者位次（正整数）。')
    return
  }

  const claimId = activeClaim.value.id
  await withProcessing(claimId, async () => {
    try {
      await axios.post(`/api/achievements/claims/${claimId}/accept/`, {
        actual_order: claimForm.actual_order,
        actual_is_corresponding: claimForm.actual_is_corresponding,
        confirmation_note: claimForm.confirmation_note.trim(),
      })
      ElMessage.success('认领已提交，成果关系已按你的确认写入。')
      dialogVisible.value = false
      await loadClaims()
    } catch (error: any) {
      ElMessage.error(resolveApiErrorMessage(error, '认领失败'))
    }
  })
}

const rejectClaim = async () => {
  if (!activeClaim.value) return
  const inputResult = await ElMessageBox.prompt('请填写拒绝原因。', '拒绝认领', {
    confirmButtonText: '确认拒绝',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：位次标注不符，请修正后重新邀请',
    inputPattern: /^.{2,200}$/,
    inputErrorMessage: '请输入 2 到 200 个字符',
    type: 'warning',
  }).catch(() => null)

  if (!inputResult) return

  const claimId = activeClaim.value.id
  await withProcessing(claimId, async () => {
    try {
      await axios.post(`/api/achievements/claims/${claimId}/reject/`, {
        reason: inputResult.value.trim(),
      })
      ElMessage.success('已拒绝该认领邀请。')
      dialogVisible.value = false
      await loadClaims()
    } catch (error: any) {
      ElMessage.error(resolveApiErrorMessage(error, '拒绝认领失败'))
    }
  })
}

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (!currentUser.value) {
    router.replace({ name: 'login' })
    return
  }
  await loadClaims()
})
</script>

<template>
  <div class="claim-page workspace-page">
    <el-card class="claim-card workspace-surface-card" shadow="never">
      <template #header>
        <div class="claim-head workspace-section-head">
          <div class="title-group">
            <strong>待认领成果</strong>
            <span>点击成果后确认“位次 + 通讯作者”信息，再完成认领。</span>
          </div>
          <el-button plain :loading="loading" @click="loadClaims">刷新列表</el-button>
        </div>
      </template>

      <el-result
        v-if="isAdminUser"
        icon="info"
        title="管理员账号无需处理成果认领"
        sub-title="认领邀请仅面向教师账户。"
      />

      <el-empty v-else-if="!loading && !records.length" description="当前没有待认领成果" :image-size="88" />

      <div v-else class="claim-list">
        <el-card v-for="item in records" :key="item.id" class="claim-item workspace-surface-card" shadow="never">
          <div class="claim-item-head">
            <div class="claim-title-group">
              <strong>{{ item.achievement_title }}</strong>
              <div class="claim-tags">
                <el-tag type="primary" effect="plain">论文成果</el-tag>
                <el-tag type="info" effect="plain">{{ item.achievement_journal || '未填写期刊/会议' }}</el-tag>
                <el-tag type="warning" effect="plain">待认领 {{ item.pending_days }} 天</el-tag>
                <el-tag type="success" effect="plain">
                  录入者提议：第{{ getProposedOrder(item) || '未填' }}作者 / {{ item.proposed_is_corresponding ? '通讯作者' : '非通讯作者' }}
                </el-tag>
              </div>
            </div>
            <span class="claim-date">{{ item.achievement_date_acquired }}</span>
          </div>

          <p class="claim-summary">{{ item.achievement_abstract || '暂无摘要。' }}</p>

          <div class="claim-meta">
            <span>录入者：{{ item.initiator_name }}</span>
            <span>邀请时间：{{ item.created_at.slice(0, 10) }}</span>
          </div>

          <div class="claim-actions">
            <el-button type="primary" :loading="processingIdSet.has(item.id)" @click="openClaimDialog(item)">
              认领确认
            </el-button>
          </div>
        </el-card>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" title="认领确认" width="560px" destroy-on-close>
      <template v-if="activeClaim">
        <div class="claim-dialog-info">
          <div>录入者设置你的署名为：</div>
          <strong>
            第{{ getProposedOrder(activeClaim) || '未填写' }}作者，{{ activeClaim.proposed_is_corresponding ? '通讯作者' : '非通讯作者' }}
          </strong>
        </div>
        <div class="claim-dialog-mode">
          <el-button :type="claimMode === 'direct' ? 'primary' : 'default'" @click="claimMode = 'direct'">直接认领</el-button>
          <el-button :type="claimMode === 'edit' ? 'primary' : 'default'" @click="claimMode = 'edit'">修改我的位次后认领</el-button>
        </div>
        <div v-if="claimMode === 'edit'" class="claim-dialog-edit">
          <el-form label-position="top">
            <el-form-item label="我的作者位次">
              <el-input-number v-model="claimForm.actual_order" :min="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="我是通讯作者">
              <el-switch v-model="claimForm.actual_is_corresponding" inline-prompt active-text="是" inactive-text="否" />
            </el-form-item>
            <el-form-item label="备注（可选）">
              <el-input v-model="claimForm.confirmation_note" type="textarea" :rows="2" placeholder="可填写位次修正说明" />
            </el-form-item>
          </el-form>
        </div>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button @click="rejectClaim">不是我（拒绝）</el-button>
        <el-button type="primary" @click="submitClaim">确认认领</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.claim-page {
  min-height: 100%;
  padding: 24px;
  background: var(--page-bg);
}

.claim-card,
.claim-item {
  border: 1px solid var(--border-color-soft);
  border-radius: 22px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.claim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.title-group {
  display: grid;
  gap: 4px;
}

.title-group strong {
  color: var(--text-primary);
}

.title-group span,
.claim-summary,
.claim-meta,
.claim-date {
  color: var(--text-tertiary);
}

.claim-list {
  display: grid;
  gap: 14px;
}

.claim-item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.claim-title-group {
  display: grid;
  gap: 10px;
}

.claim-title-group strong {
  color: var(--text-primary);
  font-size: 18px;
}

.claim-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.claim-summary {
  margin: 14px 0 10px;
  line-height: 1.8;
}

.claim-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
}

.claim-actions {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.claim-dialog-info {
  display: grid;
  gap: 4px;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.claim-dialog-mode {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

@media (max-width: 768px) {
  .claim-page {
    padding: 16px;
  }

  .claim-head,
  .claim-item-head,
  .claim-dialog-mode {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
