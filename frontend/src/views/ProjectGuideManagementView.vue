<template>
  <div class="guide-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">Guide Management</p>
        <h1 class="workspace-hero__title">项目指南管理</h1>
        <p class="hero-text workspace-hero__text">面向管理员维护项目指南基础数据，为后续推荐提供可解释的数据来源。</p>
      </div>
      <div class="hero-actions workspace-page-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button plain @click="router.push('/project-recommendations')">推荐分析入口</el-button>
        <el-button type="primary" :loading="loading" @click="loadGuides">刷新列表</el-button>
      </div>
    </section>

    <div
      v-if="checkedUser && !checkedUser.is_admin"
      class="workspace-status-result content-shell"
    >
      <el-result
        icon="warning"
        title="当前页面仅限管理员使用"
        sub-title="教师账号可前往“项目推荐”页面查看个性化推荐结果。"
      />
    </div>

    <div
      v-else
      class="guide-grid content-shell"
      :class="{ 'guide-grid--single': !showFormCard || !showListCard }"
    >
      <el-card v-if="showFormCard" shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="card-header workspace-section-head">
            <span>新增项目指南</span>
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
            <el-form-item label="规则档位" prop="rule_profile">
              <el-select v-model="form.rule_profile" style="width: 100%">
                <el-option v-for="item in ruleProfileOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item v-if="!isCollegeAdmin" label="发布范围" prop="scope">
            <el-select v-model="form.scope" style="width: 100%">
              <el-option v-for="item in scopeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item v-else label="发布范围">
            <el-input model-value="本学院" disabled />
          </el-form-item>
          <div class="triple-grid">
            <el-form-item label="关键词加成">
              <el-input-number v-model="form.rule_config.keyword_bonus" :min="0" :max="20" style="width: 100%" />
            </el-form-item>
            <el-form-item label="学科加成">
              <el-input-number v-model="form.rule_config.discipline_bonus" :min="0" :max="20" style="width: 100%" />
            </el-form-item>
            <el-form-item label="活跃度加成">
              <el-input-number v-model="form.rule_config.activity_bonus" :min="0" :max="20" style="width: 100%" />
            </el-form-item>
          </div>
          <div class="triple-grid">
            <el-form-item label="窗口加成">
              <el-input-number v-model="form.rule_config.window_bonus" :min="0" :max="20" style="width: 100%" />
            </el-form-item>
            <el-form-item label="资助加成">
              <el-input-number v-model="form.rule_config.support_bonus" :min="0" :max="20" style="width: 100%" />
            </el-form-item>
            <el-form-item label="画像联动加成">
              <el-input-number v-model="form.rule_config.portrait_bonus" :min="0" :max="20" style="width: 100%" />
            </el-form-item>
          </div>
          <div class="double-grid">
            <el-form-item label="截止时间">
              <el-date-picker v-model="form.application_deadline" value-format="YYYY-MM-DD" type="date" style="width: 100%" />
            </el-form-item>
            <el-form-item label="推荐标签">
              <el-input v-model="form.recommendationTagsInput" placeholder="如 教育场景、重点指南、适合青年教师" />
            </el-form-item>
          </div>
          <el-form-item label="指南摘要" prop="summary">
            <el-input v-model="form.summary" type="textarea" :rows="4" placeholder="概述指南主题、支持方向和申报重点" />
          </el-form-item>
          <el-form-item label="主题关键词">
            <el-input v-model="form.targetKeywordsInput" placeholder="多个关键词请用逗号、顿号或换行分隔" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="面向学科/院系">
            <el-input v-model="form.targetDisciplinesInput" placeholder="如 教育数据智能、教育科学学院" type="textarea" :rows="2" />
          </el-form-item>
          <div class="double-grid">
            <el-form-item label="资助强度">
              <el-input v-model="form.support_amount" placeholder="如 20-30 万元" />
            </el-form-item>
            <el-form-item label="来源链接">
              <el-input v-model="form.source_url" placeholder="可选，填写官方通知链接" />
            </el-form-item>
          </div>
          <el-form-item label="生命周期说明">
            <el-input v-model="form.lifecycle_note" placeholder="如 已发布待申报、已完成首轮推荐复核等" />
          </el-form-item>
          <el-form-item label="申报要求">
            <el-input v-model="form.eligibility_notes" type="textarea" :rows="3" placeholder="如 近三年相关成果、团队基础等" />
          </el-form-item>
          <div class="actions">
            <el-button @click="resetForm">重置</el-button>
            <el-button type="primary" :loading="submitting" @click="submitForm">创建指南</el-button>
          </div>
        </el-form>
      </el-card>

      <el-card v-if="showListCard" shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="card-header card-header-wrap workspace-section-head">
            <span>{{ isLifecycleSection ? '生命周期管理' : '指南列表' }}</span>
            <div class="toolbar workspace-toolbar">
              <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width: 140px" @change="loadGuides">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-select v-model="scopeFilter" clearable placeholder="全部范围" style="width: 140px" @change="loadGuides">
                <el-option v-for="item in scopeFilterOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
              <el-input v-model="searchKeyword" placeholder="搜索标题或发布单位" clearable style="width: 220px" @keyup.enter="loadGuides" />
              <el-button @click="loadGuides">查询</el-button>
            </div>
          </div>
        </template>

        <template v-if="isLifecycleSection">
          <div class="lifecycle-filter-row">
            <el-date-picker
              v-model="deadlineRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="截止起始"
              end-placeholder="截止结束"
              style="width: 280px"
            />
            <el-date-picker
              v-model="updatedRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="更新起始"
              end-placeholder="更新结束"
              style="width: 280px"
            />
            <el-date-picker
              v-model="publishedRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="发布起始"
              end-placeholder="发布结束"
              style="width: 280px"
            />
            <el-date-picker
              v-model="archivedRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="归档起始"
              end-placeholder="归档结束"
              style="width: 280px"
            />
            <el-button @click="resetLifecycleFilters">重置时间筛选</el-button>
          </div>

          <div class="summary-grid" v-if="summary">
            <div class="summary-card">
              <strong>{{ summary.total_count }}</strong>
              <span>指南总数</span>
              <p>草稿 {{ summary.draft_count }} / 已归档 {{ summary.archived_count }}</p>
            </div>
            <div class="summary-card">
              <strong>{{ summary.active_count + summary.urgent_count }}</strong>
              <span>治理中的活跃指南</span>
              <p>申报中 {{ summary.active_count }} / 临近截止 {{ summary.urgent_count }}</p>
            </div>
            <div class="summary-card">
              <strong>{{ summary.deadline_warning_count }}</strong>
              <span>近 30 天到期</span>
              <p>超期未归档 {{ summary.overdue_active_count }}</p>
            </div>
          </div>

          <el-table
            :data="guides"
            v-loading="loading"
            empty-text="暂无生命周期数据"
            :header-cell-style="{ textAlign: 'center' }"
            :cell-style="{ textAlign: 'center' }"
          >
            <el-table-column prop="title" label="指南标题" min-width="220" />
            <el-table-column label="范围" width="110">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" :type="row.scope === 'GLOBAL' ? 'primary' : 'success'">
                  {{ row.scope_display || (row.scope === 'GLOBAL' ? '全局' : '本学院') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="resolveStatusTagType(row.status)">
                  {{ row.status_display }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="application_deadline" label="截止时间" width="130" />
            <el-table-column prop="published_at" label="发布时间" min-width="180" />
            <el-table-column prop="archived_at" label="归档时间" min-width="180" />
            <el-table-column prop="updated_at" label="最近更新时间" min-width="180" />
            <el-table-column label="生命周期说明" min-width="200">
              <template #default="{ row }">
                <span class="muted">{{ row.lifecycle_note || '无' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <template v-if="isRowManageable(row)">
                  <el-button link type="primary" @click="showLifecycleDetail(row)">查看详情</el-button>
                  <el-button
                    v-if="row.status !== 'ARCHIVED'"
                    link
                    type="warning"
                    @click="updateGuideStatus(row, 'ARCHIVED')"
                  >
                    归档
                  </el-button>
                  <el-button v-else link type="success" @click="updateGuideStatus(row, 'ACTIVE')">重新开放</el-button>
                </template>
                <span v-else class="muted">仅可查看</span>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <template v-else>
          <div class="summary-grid" v-if="summary">
            <div class="summary-card">
              <strong>{{ summary.total_count }}</strong>
              <span>指南总数</span>
              <p>申报中 {{ summary.active_count }} / 临近截止 {{ summary.urgent_count }}</p>
            </div>
            <div class="summary-card">
              <strong>{{ summary.deadline_warning_count }}</strong>
              <span>近 30 天到期</span>
              <p>归档 {{ summary.archived_count }} / 草稿 {{ summary.draft_count }}</p>
            </div>
            <div class="summary-card">
              <strong>{{ summary.config_coverage_count }}</strong>
              <span>已配置细化规则</span>
              <p>待整理活跃项 {{ summary.stale_active_count }}</p>
            </div>
          </div>

          <el-table
            :data="guides"
            v-loading="loading"
            empty-text="暂无项目指南"
            :header-cell-style="{ textAlign: 'center' }"
            :cell-style="{ textAlign: 'center' }"
          >
            <el-table-column prop="title" label="指南标题" min-width="230" />
            <el-table-column prop="issuing_agency" label="发布单位" min-width="150" />
            <el-table-column prop="guide_level_display" label="级别" width="110" />
            <el-table-column prop="rule_profile_display" label="规则档位" width="120" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="resolveStatusTagType(row.status)">
                  {{ row.status_display }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="范围" width="110">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" :type="row.scope === 'GLOBAL' ? 'primary' : 'success'">
                  {{ row.scope_display || (row.scope === 'GLOBAL' ? '全局' : '本学院') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="application_deadline" label="截止时间" width="130" />
            <el-table-column label="生命周期" min-width="220">
              <template #default="{ row }">
                <div class="timeline-cell">
                  <span v-if="row.published_at">发布 {{ row.published_at }}</span>
                  <span v-if="row.closed_at">关闭 {{ row.closed_at }}</span>
                  <span v-if="row.archived_at">归档 {{ row.archived_at }}</span>
                  <span v-if="row.lifecycle_note">{{ row.lifecycle_note }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="主题匹配" min-width="220">
              <template #default="{ row }">
                <div class="tag-list">
                  <el-tag v-for="tag in row.target_keywords.slice(0, 4)" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="规则细化" min-width="180">
              <template #default="{ row }">
                <div class="tag-list">
                  <el-tag v-for="(value, key) in row.rule_config" :key="`${row.id}-${key}`" size="small" type="warning" effect="plain">
                    {{ key }} +{{ value }}
                  </el-tag>
                  <span v-if="!Object.keys(row.rule_config || {}).length" class="muted">默认</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="推荐标签" min-width="180">
              <template #default="{ row }">
                <div class="tag-list">
                  <el-tag v-for="tag in row.recommendation_tags.slice(0, 3)" :key="tag" size="small" type="success" effect="plain">
                    {{ tag }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <template v-if="isRowManageable(row)">
                  <el-button
                    v-if="canTargetedPush(row)"
                    link
                    type="success"
                    @click="handleTargetedPush(row)"
                  >
                    定向推送
                  </el-button>
                  <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                  <el-button link type="danger" @click="removeGuide(row.id)">删除</el-button>
                </template>
                <span v-else class="muted">仅可查看</span>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-card>
    </div>

    <el-dialog
      v-model="editDialogVisible"
      title="编辑项目指南"
      width="760px"
      destroy-on-close
      append-to-body
    >
      <el-form ref="editFormRef" :model="editForm" :rules="rules" label-position="top">
        <el-form-item label="指南标题" prop="title">
          <el-input v-model="editForm.title" placeholder="请输入项目指南标题" />
        </el-form-item>
        <div class="double-grid">
          <el-form-item label="发布单位" prop="issuing_agency">
            <el-input v-model="editForm.issuing_agency" placeholder="如 省教育厅、科技部" />
          </el-form-item>
          <el-form-item label="指南级别" prop="guide_level">
            <el-select v-model="editForm.guide_level" style="width: 100%">
              <el-option v-for="item in guideLevelOptions" :key="`edit-level-${item.value}`" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </div>
        <div class="double-grid">
          <el-form-item label="状态" prop="status">
            <el-select v-model="editForm.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="`edit-status-${item.value}`" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="规则档位" prop="rule_profile">
            <el-select v-model="editForm.rule_profile" style="width: 100%">
              <el-option v-for="item in ruleProfileOptions" :key="`edit-rule-${item.value}`" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item v-if="!isCollegeAdmin" label="发布范围" prop="scope">
          <el-select v-model="editForm.scope" style="width: 100%">
            <el-option v-for="item in scopeOptions" :key="`edit-scope-${item.value}`" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="发布范围">
          <el-input model-value="本学院" disabled />
        </el-form-item>
        <div class="triple-grid">
          <el-form-item label="关键词加成">
            <el-input-number v-model="editForm.rule_config.keyword_bonus" :min="0" :max="20" style="width: 100%" />
          </el-form-item>
          <el-form-item label="学科加成">
            <el-input-number v-model="editForm.rule_config.discipline_bonus" :min="0" :max="20" style="width: 100%" />
          </el-form-item>
          <el-form-item label="活跃度加成">
            <el-input-number v-model="editForm.rule_config.activity_bonus" :min="0" :max="20" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="triple-grid">
          <el-form-item label="窗口加成">
            <el-input-number v-model="editForm.rule_config.window_bonus" :min="0" :max="20" style="width: 100%" />
          </el-form-item>
          <el-form-item label="资助加成">
            <el-input-number v-model="editForm.rule_config.support_bonus" :min="0" :max="20" style="width: 100%" />
          </el-form-item>
          <el-form-item label="画像联动加成">
            <el-input-number v-model="editForm.rule_config.portrait_bonus" :min="0" :max="20" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="double-grid">
          <el-form-item label="截止时间">
            <el-date-picker v-model="editForm.application_deadline" value-format="YYYY-MM-DD" type="date" style="width: 100%" />
          </el-form-item>
          <el-form-item label="推荐标签">
            <el-input v-model="editForm.recommendationTagsInput" placeholder="如 教育场景、重点指南、适合青年教师" />
          </el-form-item>
        </div>
        <el-form-item label="指南摘要" prop="summary">
          <el-input v-model="editForm.summary" type="textarea" :rows="4" placeholder="概述指南主题、支持方向和申报重点" />
        </el-form-item>
        <el-form-item label="主题关键词">
          <el-input v-model="editForm.targetKeywordsInput" placeholder="多个关键词请用逗号、顿号或换行分隔" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="面向学科/院系">
          <el-input v-model="editForm.targetDisciplinesInput" placeholder="如 教育数据智能、教育科学学院" type="textarea" :rows="2" />
        </el-form-item>
        <div class="double-grid">
          <el-form-item label="资助强度">
            <el-input v-model="editForm.support_amount" placeholder="如 20-30 万元" />
          </el-form-item>
          <el-form-item label="来源链接">
            <el-input v-model="editForm.source_url" placeholder="可选，填写官方通知链接" />
          </el-form-item>
        </div>
        <el-form-item label="生命周期说明">
          <el-input v-model="editForm.lifecycle_note" placeholder="如 已发布待申报、已完成首轮推荐复核等" />
        </el-form-item>
        <el-form-item label="申报要求">
          <el-input v-model="editForm.eligibility_notes" type="textarea" :rows="3" placeholder="如 近三年相关成果、团队基础等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="actions">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submittingEdit" @click="submitEditForm">保存修改</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import type {
  GuideLevel,
  GuideLifecycleSummary,
  GuideRuleConfig,
  GuideRuleProfile,
  GuideScope,
  GuideStatus,
  GuideTargetedPushResponse,
  ProjectGuideRecord,
} from './project-guides/types'

type GuideManagementSection = 'overview' | 'manage' | 'lifecycle'

const props = withDefaults(
  defineProps<{
    sectionMode?: GuideManagementSection
  }>(),
  {
    sectionMode: 'overview',
  },
)

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
  { label: '申报中', value: 'ACTIVE' },
  { label: '临近截止', value: 'URGENT' },
  { label: '已结束', value: 'ARCHIVED' },
]
const scopeOptions: Array<{ label: string; value: GuideScope }> = [
  { label: '全局', value: 'GLOBAL' },
  { label: '本学院', value: 'ACADEMY' },
]
const scopeFilterOptions = scopeOptions

const ruleProfileOptions: Array<{ label: string; value: GuideRuleProfile }> = [
  { label: '均衡规则', value: 'BALANCED' },
  { label: '主题优先', value: 'KEYWORD_FIRST' },
  { label: '学科优先', value: 'DISCIPLINE_FIRST' },
  { label: '窗口优先', value: 'WINDOW_FIRST' },
  { label: '活跃度优先', value: 'ACTIVITY_FIRST' },
  { label: '画像联动优先', value: 'PORTRAIT_FIRST' },
  { label: '申报基础优先', value: 'FOUNDATION_FIRST' },
]

const checkedUser = ref<SessionUser | null>(null)
const isCollegeAdmin = computed(() => checkedUser.value?.role_code === 'college_admin')
const activeSection = computed(() => props.sectionMode)
const isLifecycleSection = computed(() => activeSection.value === 'lifecycle')
const showFormCard = computed(() => activeSection.value === 'manage')
const showListCard = computed(() => ['overview', 'lifecycle'].includes(activeSection.value))
const formRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()
const guides = ref<ProjectGuideRecord[]>([])
const summary = ref<GuideLifecycleSummary | null>(null)
const loading = ref(false)
const submitting = ref(false)
const submittingEdit = ref(false)
const editDialogVisible = ref(false)
const editingGuideId = ref<number | null>(null)
const statusFilter = ref<GuideStatus | ''>('')
const scopeFilter = ref<GuideScope | ''>('')
const searchKeyword = ref('')
const deadlineRange = ref<[string, string] | []>([])
const updatedRange = ref<[string, string] | []>([])
const publishedRange = ref<[string, string] | []>([])
const archivedRange = ref<[string, string] | []>([])

const form = reactive({
  title: '',
  issuing_agency: '',
  guide_level: 'PROVINCIAL' as GuideLevel,
  status: 'DRAFT' as GuideStatus,
  scope: 'GLOBAL' as GuideScope,
  rule_profile: 'BALANCED' as GuideRuleProfile,
  rule_config: {
    keyword_bonus: 0,
    discipline_bonus: 0,
    activity_bonus: 0,
    window_bonus: 0,
    support_bonus: 0,
    portrait_bonus: 0,
  } as GuideRuleConfig,
  application_deadline: '',
  summary: '',
  targetKeywordsInput: '',
  targetDisciplinesInput: '',
  recommendationTagsInput: '',
  support_amount: '',
  eligibility_notes: '',
  source_url: '',
  lifecycle_note: '',
})

const editForm = reactive({
  title: '',
  issuing_agency: '',
  guide_level: 'PROVINCIAL' as GuideLevel,
  status: 'DRAFT' as GuideStatus,
  scope: 'GLOBAL' as GuideScope,
  rule_profile: 'BALANCED' as GuideRuleProfile,
  rule_config: {
    keyword_bonus: 0,
    discipline_bonus: 0,
    activity_bonus: 0,
    window_bonus: 0,
    support_bonus: 0,
    portrait_bonus: 0,
  } as GuideRuleConfig,
  application_deadline: '',
  summary: '',
  targetKeywordsInput: '',
  targetDisciplinesInput: '',
  recommendationTagsInput: '',
  support_amount: '',
  eligibility_notes: '',
  source_url: '',
  lifecycle_note: '',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入指南标题', trigger: 'blur' }],
  issuing_agency: [{ required: true, message: '请输入发布单位', trigger: 'blur' }],
  guide_level: [{ required: true, message: '请选择指南级别', trigger: 'change' }],
  status: [{ required: true, message: '请选择指南状态', trigger: 'change' }],
  scope: [{ required: true, message: '请选择发布范围', trigger: 'change' }],
  summary: [{ required: true, message: '请输入指南摘要', trigger: 'blur' }],
}

const parseTextList = (raw: string): string[] =>
  raw
    .split(/[\n,，、；;]+/)
    .map(item => item.trim())
    .filter(Boolean)

const resetForm = () => {
  formRef.value?.resetFields()
  form.guide_level = 'PROVINCIAL'
  form.status = 'DRAFT'
  form.scope = isCollegeAdmin.value ? 'ACADEMY' : 'GLOBAL'
  form.rule_profile = 'BALANCED'
  form.rule_config = {
    keyword_bonus: 0,
    discipline_bonus: 0,
    activity_bonus: 0,
    window_bonus: 0,
    support_bonus: 0,
    portrait_bonus: 0,
  }
  form.application_deadline = ''
  form.targetKeywordsInput = ''
  form.targetDisciplinesInput = ''
  form.recommendationTagsInput = ''
  form.support_amount = ''
  form.eligibility_notes = ''
  form.source_url = ''
  form.lifecycle_note = ''
}

const loadSummary = async () => {
  const { data } = await axios.get<GuideLifecycleSummary>(`${guideEndpoint}summary/`)
  summary.value = data
}

const loadGuides = async () => {
  loading.value = true
  try {
    const lifecycleParams =
      isLifecycleSection.value
        ? {
            deadline_from: deadlineRange.value[0] || undefined,
            deadline_to: deadlineRange.value[1] || undefined,
            updated_from: updatedRange.value[0] || undefined,
            updated_to: updatedRange.value[1] || undefined,
            published_from: publishedRange.value[0] || undefined,
            published_to: publishedRange.value[1] || undefined,
            archived_from: archivedRange.value[0] || undefined,
            archived_to: archivedRange.value[1] || undefined,
          }
        : {}

    const { data } = await axios.get<ProjectGuideRecord[]>(guideEndpoint, {
      params: {
        status: statusFilter.value || undefined,
        scope: scopeFilter.value || undefined,
        search: searchKeyword.value || undefined,
        ...lifecycleParams,
      },
    })
    guides.value = data
    if (checkedUser.value?.is_admin) {
      await loadSummary()
    }
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
      scope: isCollegeAdmin.value ? 'ACADEMY' : form.scope,
      rule_profile: form.rule_profile,
      rule_config: form.rule_config,
      application_deadline: form.application_deadline || null,
      summary: form.summary,
      target_keywords: parseTextList(form.targetKeywordsInput),
      target_disciplines: parseTextList(form.targetDisciplinesInput),
      recommendation_tags: parseTextList(form.recommendationTagsInput),
      support_amount: form.support_amount,
      eligibility_notes: form.eligibility_notes,
      source_url: form.source_url,
      lifecycle_note: form.lifecycle_note,
    }

    await axios.post(guideEndpoint, payload)
    ElMessage.success('项目指南已创建')

    resetForm()
    await loadGuides()
  } finally {
    submitting.value = false
  }
}

const fillFormByRow = (
  target: typeof form | typeof editForm,
  row: ProjectGuideRecord,
) => {
  target.title = row.title
  target.issuing_agency = row.issuing_agency
  target.guide_level = row.guide_level
  target.status = row.status
  target.scope = row.scope
  target.rule_profile = row.rule_profile
  target.rule_config = {
    keyword_bonus: row.rule_config?.keyword_bonus || 0,
    discipline_bonus: row.rule_config?.discipline_bonus || 0,
    activity_bonus: row.rule_config?.activity_bonus || 0,
    window_bonus: row.rule_config?.window_bonus || 0,
    support_bonus: row.rule_config?.support_bonus || 0,
    portrait_bonus: row.rule_config?.portrait_bonus || 0,
  }
  target.application_deadline = row.application_deadline || ''
  target.summary = row.summary
  target.targetKeywordsInput = row.target_keywords.join('，')
  target.targetDisciplinesInput = row.target_disciplines.join('，')
  target.recommendationTagsInput = row.recommendation_tags.join('，')
  target.support_amount = row.support_amount
  target.eligibility_notes = row.eligibility_notes
  target.source_url = row.source_url
  target.lifecycle_note = row.lifecycle_note
}

const openEditDialog = (row: ProjectGuideRecord) => {
  editingGuideId.value = row.id
  fillFormByRow(editForm, row)
  editDialogVisible.value = true
}

const submitEditForm = async () => {
  if (!editingGuideId.value) return
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingEdit.value = true
  try {
    const payload = {
      title: editForm.title,
      issuing_agency: editForm.issuing_agency,
      guide_level: editForm.guide_level,
      status: editForm.status,
      scope: isCollegeAdmin.value ? 'ACADEMY' : editForm.scope,
      rule_profile: editForm.rule_profile,
      rule_config: editForm.rule_config,
      application_deadline: editForm.application_deadline || null,
      summary: editForm.summary,
      target_keywords: parseTextList(editForm.targetKeywordsInput),
      target_disciplines: parseTextList(editForm.targetDisciplinesInput),
      recommendation_tags: parseTextList(editForm.recommendationTagsInput),
      support_amount: editForm.support_amount,
      eligibility_notes: editForm.eligibility_notes,
      source_url: editForm.source_url,
      lifecycle_note: editForm.lifecycle_note,
    }

    await axios.patch(`${guideEndpoint}${editingGuideId.value}/`, payload)
    ElMessage.success('项目指南已更新')
    editDialogVisible.value = false
    await loadGuides()
  } finally {
    submittingEdit.value = false
  }
}

const removeGuide = async (guideId: number) => {
  await ElMessageBox.confirm('删除后该指南将不再参与教师推荐，确认继续吗？', '删除确认', { type: 'warning' })
  await axios.delete(`${guideEndpoint}${guideId}/`)
  ElMessage.success('项目指南已删除')
  await loadGuides()
}

const updateGuideStatus = async (row: ProjectGuideRecord, status: GuideStatus) => {
  await axios.patch(`${guideEndpoint}${row.id}/`, { status })
  ElMessage.success(status === 'ARCHIVED' ? '项目指南已归档' : '项目指南状态已更新')
  await loadGuides()
}

const resolveStatusTagType = (status: GuideStatus): 'success' | 'warning' | 'info' | 'danger' => {
  if (status === 'ACTIVE') return 'success'
  if (status === 'URGENT') return 'danger'
  if (status === 'ARCHIVED') return 'info'
  return 'info'
}

const isRowManageable = (row: ProjectGuideRecord): boolean => {
  if (!isCollegeAdmin.value) {
    return true
  }
  return row.scope === 'ACADEMY'
}

const canTargetedPush = (row: ProjectGuideRecord): boolean => {
  return isRowManageable(row) && (row.status === 'ACTIVE' || row.status === 'URGENT')
}

const handleTargetedPush = async (row: ProjectGuideRecord) => {
  const { data } = await axios.post<GuideTargetedPushResponse>(`${guideEndpoint}${row.id}/targeted_push/`, {})
  const notificationCountText = typeof data.notification_count === 'number' ? `，已发送通知 ${data.notification_count} 条` : ''
  ElMessage.success(`定向推送已执行，匹配教师 ${data.matched_count} 人${notificationCountText}`)
}

const resetLifecycleFilters = async () => {
  deadlineRange.value = []
  updatedRange.value = []
  publishedRange.value = []
  archivedRange.value = []
  await loadGuides()
}

const showLifecycleDetail = (row: ProjectGuideRecord) => {
  const lines = [
    `指南：${row.title}`,
    `状态：${row.status_display}`,
    `范围：${row.scope_display || (row.scope === 'GLOBAL' ? '全局' : '本学院')}`,
    `发布时间：${row.published_at || '无'}`,
    `关闭时间：${row.closed_at || '无'}`,
    `归档时间：${row.archived_at || '无'}`,
    `最近更新：${row.updated_at || '无'}`,
    `生命周期说明：${row.lifecycle_note || '无'}`,
  ]
  ElMessageBox.alert(lines.join('<br/>'), '生命周期详情', {
    dangerouslyUseHTMLString: true,
    confirmButtonText: '关闭',
  })
}

onMounted(async () => {
  checkedUser.value = await ensureSessionUserContext()
  if (checkedUser.value?.is_admin) {
    form.scope = isCollegeAdmin.value ? 'ACADEMY' : 'GLOBAL'
    await loadGuides()
  }
})
</script>

<style scoped>
.guide-page {
  min-height: 100%;
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

.guide-grid--single {
  grid-template-columns: 1fr;
}

.double-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.triple-grid,
.summary-grid {
  display: grid;
  gap: 16px;
}

.triple-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.summary-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 18px;
}

.summary-card {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
  display: grid;
  gap: 8px;
}

.summary-card strong {
  color: var(--text-primary);
  font-size: 24px;
}

.summary-card span,
.summary-card p,
.timeline-cell span,
.muted {
  color: var(--text-tertiary);
  line-height: 1.7;
  margin: 0;
}

.timeline-cell {
  display: grid;
  gap: 4px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.lifecycle-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
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
  .double-grid,
  .triple-grid,
  .summary-grid {
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
