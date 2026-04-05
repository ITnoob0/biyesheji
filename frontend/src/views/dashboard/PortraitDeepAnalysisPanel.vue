<template>
  <section class="deep-grid">
    <el-card class="panel-card workspace-surface-card" shadow="never">
      <template #header>
        <div class="section-head workspace-section-head">
          <span>阶段对比</span>
        </div>
      </template>

      <div class="panel-intro">
        <strong>{{ stageComparison?.summary || '当前阶段暂无足够样本形成阶段对比。' }}</strong>
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
          v-for="item in comparisonDimensions"
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
          <div v-if="item.drivers?.length" class="tag-row">
            <el-tag v-for="driver in item.drivers" :key="`${item.key}-${driver}`" size="small" effect="plain" type="success">
              {{ driver }}
            </el-tag>
          </div>
          <p v-if="item.interpretation">{{ item.interpretation }}</p>
        </div>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DimensionInsight, StageComparison } from './portrait'

const props = defineProps<{
  stageComparison: StageComparison | null
  dimensionInsights: DimensionInsight[]
}>()

const dimensionCatalog = [
  { key: 'academic_output', name: '基础学术产出' },
  { key: 'funding_support', name: '经费与项目攻关' },
  { key: 'ip_strength', name: '知识产权沉淀' },
  { key: 'talent_training', name: '人才培养成效' },
  { key: 'academic_reputation', name: '学术活跃与声誉' },
  { key: 'interdisciplinary', name: '跨学科融合度' },
] as const

const comparisonDimensions = computed(() => {
  const stageMap = new Map((props.stageComparison?.changed_dimensions || []).map(item => [item.key, item]))
  const insightMap = new Map(props.dimensionInsights.map(item => [item.key, item]))

  return dimensionCatalog.map(item => {
    const existing = stageMap.get(item.key)
    if (existing) {
      return existing
    }

    const currentInsight = insightMap.get(item.key)
    const currentValue = currentInsight?.value ?? 0

    return {
      key: item.key,
      name: item.name,
      current_value: currentValue,
      baseline_value: currentValue,
      delta: 0,
      trend: 'flat' as const,
      change_summary: '',
      drivers: [],
      interpretation: currentInsight?.formula_note || '',
      boundary_note: '',
    }
  })
})

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
</script>

<style scoped>
.deep-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.panel-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 22px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.panel-intro,
.compare-stat,
.delta-item,
.report-section {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.panel-intro,
.delta-list {
  display: grid;
  gap: 14px;
}

.panel-intro strong,
.report-section strong {
  color: var(--text-primary);
}

.panel-intro p,
.compare-stat p,
.delta-item p,
.report-section p {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.compare-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.compare-stat span {
  display: block;
  margin-bottom: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.compare-stat strong {
  color: var(--text-primary);
  font-size: 20px;
}

.compare-stat.accent {
  background: linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 12%, var(--surface-2)) 0%, var(--panel-bg) 100%);
}

.delta-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.delta-list {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.delta-list,
.tag-row {
  margin-top: 14px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.delta-up {
  color: var(--accent-success);
}

.delta-down {
  color: var(--accent-danger);
}

.delta-flat {
  color: var(--text-secondary);
}

@media (max-width: 1180px) {
  .compare-summary-grid,
  .delta-list {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .compare-summary-grid,
  .delta-list {
    grid-template-columns: 1fr;
  }
}
</style>
