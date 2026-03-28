<template>
  <section class="deep-grid">
    <el-card class="panel-card workspace-surface-card" shadow="never">
      <template #header>
        <div class="section-head workspace-section-head">
          <span>阶段对比</span>
          <el-tag type="primary" effect="plain">持续分析视图</el-tag>
        </div>
      </template>

      <div class="panel-intro">
        <strong>{{ stageComparison?.summary || '当前阶段暂无足够样本形成阶段对比。' }}</strong>
        <p>{{ stageComparison?.coverage_note || '当前仅保留阶段对比接口边界。' }}</p>
        <p v-if="stageComparison?.structured_summary">{{ stageComparison.structured_summary }}</p>
      </div>

      <div v-if="stageComparison?.available" class="compare-summary-grid">
        <div class="compare-stat">
          <span>{{ stageComparison.current_label }}</span>
          <strong>{{ stageComparison.current_total_score }} 分</strong>
          <p>{{ stageComparison.current_total_achievements }} 项成果</p>
        </div>
        <div class="compare-stat">
          <span>{{ stageComparison.baseline_label }}</span>
          <strong>{{ stageComparison.baseline_total_score }} 分</strong>
          <p>{{ stageComparison.baseline_total_achievements }} 项成果</p>
        </div>
        <div class="compare-stat accent">
          <span>综合变化</span>
          <strong :class="resolveDeltaClass(stageComparison.score_delta)">
            {{ formatSigned(stageComparison.score_delta) }} 分
          </strong>
          <p>成果量 {{ formatSigned(stageComparison.achievement_delta) }} 项</p>
        </div>
      </div>

      <div class="delta-list">
        <div
          v-for="item in stageComparison?.changed_dimensions || []"
          :key="item.key"
          class="delta-item"
        >
          <div class="delta-head">
            <strong>{{ item.name }}</strong>
            <el-tag
              size="small"
              effect="plain"
              :type="item.trend === 'up' ? 'success' : item.trend === 'down' ? 'danger' : 'info'"
            >
              {{ formatSigned(item.delta) }}
            </el-tag>
          </div>
          <p>{{ item.baseline_value }} -> {{ item.current_value }}</p>
          <p v-if="item.change_summary">{{ item.change_summary }}</p>
          <div v-if="item.drivers?.length" class="tag-row">
            <el-tag v-for="driver in item.drivers" :key="`${item.key}-${driver}`" size="small" effect="plain" type="success">
              {{ driver }}
            </el-tag>
          </div>
          <p v-if="item.interpretation">{{ item.interpretation }}</p>
          <p v-if="item.boundary_note">{{ item.boundary_note }}</p>
        </div>
      </div>
    </el-card>

    <el-card class="panel-card workspace-surface-card" shadow="never">
      <template #header>
        <div class="section-head workspace-section-head">
          <span>权重与形成逻辑</span>
          <el-tag type="success" effect="plain">结构化解释</el-tag>
        </div>
      </template>

      <div class="panel-intro">
        <strong>{{ portraitExplanation?.weight_logic_summary || calculationSummary?.formula_note }}</strong>
        <p>{{ portraitExplanation?.overview || '当前教师画像由多成果实时聚合形成。' }}</p>
      </div>

      <div v-if="calculationSummary" class="summary-bar">
        <div class="summary-pill">
          <span>总分</span>
          <strong>{{ calculationSummary.total_score }}</strong>
        </div>
        <div class="summary-pill">
          <span>优势维度</span>
          <strong>{{ calculationSummary.strongest_dimension.name }}</strong>
        </div>
        <div class="summary-pill">
          <span>待补维度</span>
          <strong>{{ calculationSummary.weakest_dimension.name }}</strong>
        </div>
      </div>

      <div class="weight-card-list">
        <div v-for="item in weightSpec" :key="item.key" class="weight-card">
          <div class="weight-head">
            <strong>{{ item.name }}</strong>
            <el-tag size="small" effect="plain" type="warning">{{ item.weight }}%</el-tag>
          </div>
          <p class="weight-score">当前得分 {{ item.current_value }}</p>
          <p>{{ item.formula_short }}</p>
          <div class="tag-row">
            <el-tag v-for="input in item.main_inputs" :key="`${item.key}-${input}`" size="small" effect="plain" type="info">
              {{ input }}
            </el-tag>
          </div>
          <p>{{ item.rationale }}</p>
        </div>
      </div>
    </el-card>

    <el-card class="panel-card workspace-surface-card" shadow="never">
      <template #header>
        <div class="section-head workspace-section-head">
          <span>快照边界</span>
          <el-tag type="warning" effect="plain">当前未落库</el-tag>
        </div>
      </template>

      <div class="panel-intro">
        <strong>{{ snapshotBoundary?.current_boundary_note || portraitExplanation?.snapshot_boundary_note }}</strong>
        <p>{{ snapshotBoundary?.frontend_carry_note || '前端当前承接生成时间、口径说明与阶段结论。' }}</p>
        <p>{{ portraitExplanation?.snapshot_version_note || snapshotBoundary?.version_semantics }}</p>
      </div>

      <div v-if="snapshotBoundary" class="boundary-grid">
        <div class="boundary-item">
          <span>快照语义</span>
          <strong>{{ snapshotVersionLabel }}</strong>
        </div>
        <div class="boundary-item">
          <span>生成时间</span>
          <strong>{{ generatedLabel }}</strong>
        </div>
        <div class="boundary-item">
          <span>生成触发</span>
          <strong>{{ snapshotBoundary.generation_trigger_label }}</strong>
        </div>
        <div class="boundary-item">
          <span>冻结口径</span>
          <strong>{{ snapshotBoundary.freeze_scope_note }}</strong>
        </div>
        <div class="boundary-item">
          <span>锚点年份</span>
          <strong>{{ snapshotBoundary.anchor_years.join(' / ') || '暂无' }}</strong>
        </div>
        <div class="boundary-item">
          <span>对比承接</span>
          <strong>{{ snapshotBoundary.comparison_ready ? '可做辅助阶段对比' : '当前样本不足' }}</strong>
        </div>
      </div>

      <div class="boundary-note-list">
        <div class="boundary-note">
          <strong>当前边界</strong>
          <p>{{ snapshotBoundary?.current_boundary_note || '当前画像快照仍以运行时分析视图承接。' }}</p>
        </div>
        <div class="boundary-note">
          <strong>版本语义</strong>
          <p>{{ snapshotBoundary?.version_semantics || '当前快照版本只承接口径说明。' }}</p>
        </div>
        <div class="boundary-note">
          <strong>对比边界</strong>
          <p>{{ snapshotBoundary?.compare_boundary_note || '当前只允许做辅助对比，不替代正式历史快照。' }}</p>
        </div>
        <div class="boundary-note">
          <strong>后续演进</strong>
          <p>{{ snapshotBoundary?.next_step_note || '后续如需正式落库，应单独定义冻结口径。' }}</p>
        </div>
      </div>

      <div class="tag-row">
        <el-tag
          v-for="field in snapshotBoundary?.recommended_fields || []"
          :key="field"
          size="small"
          effect="plain"
          type="success"
        >
          {{ field }}
        </el-tag>
      </div>
    </el-card>

    <el-card class="panel-card workspace-surface-card" shadow="never">
      <template #header>
        <div class="section-head workspace-section-head">
          <span>报告化展示</span>
          <el-tag type="danger" effect="plain">可导出</el-tag>
        </div>
      </template>

      <div class="report-head">
        <div>
          <strong>{{ portraitReport?.report_title || '教师画像分析报告' }}</strong>
          <p>{{ portraitReport?.summary || portraitExplanation?.report_boundary_note || '当前支持运行时生成结构化画像报告。' }}</p>
          <p v-if="portraitReport?.snapshot_digest">{{ portraitReport.snapshot_digest.label }} · {{ portraitReport.snapshot_digest.version }}</p>
        </div>
        <el-button type="primary" :loading="exporting" @click="$emit('export-report')">导出 Markdown 报告</el-button>
      </div>

      <div class="report-highlight-list">
        <div v-for="item in portraitReport?.highlights || []" :key="item" class="report-highlight">
          <strong>{{ item }}</strong>
        </div>
      </div>

      <div class="report-section-list">
        <div v-for="section in portraitReport?.sections || []" :key="section.title" class="report-section">
          <strong>{{ section.title }}</strong>
          <p>{{ section.summary }}</p>
          <div class="report-bullets">
            <p v-for="bullet in section.bullets" :key="bullet">{{ bullet }}</p>
          </div>
        </div>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type {
  CalculationSummary,
  PortraitExplanation,
  PortraitReportResponse,
  SnapshotBoundary,
  StageComparison,
  WeightSpecItem,
} from './portrait'
import { buildPortraitGeneratedLabel, buildSnapshotVersionLabel } from './portrait'

const props = defineProps<{
  stageComparison: StageComparison | null
  snapshotBoundary: SnapshotBoundary | null
  calculationSummary: CalculationSummary | null
  weightSpec: WeightSpecItem[]
  portraitExplanation: PortraitExplanation | null
  portraitReport: PortraitReportResponse | null
  exporting: boolean
}>()

defineEmits<{
  (event: 'export-report'): void
}>()

const formatSigned = (value?: number | null): string => {
  if (value === null || value === undefined) {
    return '0'
  }
  return `${value > 0 ? '+' : ''}${value}`
}

const resolveDeltaClass = (value?: number | null): string => {
  if ((value || 0) > 0) {
    return 'delta-up'
  }
  if ((value || 0) < 0) {
    return 'delta-down'
  }
  return 'delta-flat'
}

const generatedLabel = computed(() => buildPortraitGeneratedLabel(props.snapshotBoundary?.generated_at))
const snapshotVersionLabel = computed(() => buildSnapshotVersionLabel(props.snapshotBoundary))
</script>

<style scoped>
.deep-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.panel-card {
  border: none;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.panel-intro,
.compare-stat,
.delta-item,
.weight-card,
.boundary-item,
.boundary-note,
.report-highlight,
.report-section {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fafc;
}

.panel-intro,
.weight-card-list,
.boundary-note-list,
.report-section-list,
.delta-list {
  display: grid;
  gap: 14px;
}

.panel-intro strong,
.boundary-note strong,
.report-section strong {
  color: #0f172a;
}

.panel-intro p,
.compare-stat p,
.delta-item p,
.weight-card p,
.boundary-note p,
.report-section p,
.report-head p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.compare-summary-grid,
.boundary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.boundary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.compare-stat span,
.boundary-item span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

.compare-stat strong,
.boundary-item strong,
.report-highlight strong {
  color: #0f172a;
  font-size: 20px;
}

.compare-stat.accent {
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
}

.delta-head,
.weight-head,
.report-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.delta-list,
.boundary-note-list,
.report-highlight-list,
.report-bullets,
.tag-row {
  margin-top: 14px;
}

.weight-score {
  color: #0f172a !important;
  font-weight: 600;
}

.summary-bar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.summary-pill {
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
}

.summary-pill span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
}

.summary-pill strong {
  color: #0f172a;
}

.weight-card-list,
.report-highlight-list,
.report-section-list {
  margin-top: 14px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.delta-up {
  color: #059669;
}

.delta-down {
  color: #dc2626;
}

.delta-flat {
  color: #475569;
}

@media (max-width: 1180px) {
  .deep-grid,
  .compare-summary-grid,
  .summary-bar,
  .boundary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
