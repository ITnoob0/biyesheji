<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { AchievementOverview, RecentAchievementRecord } from '../../views/dashboard/portrait'

const props = defineProps<{
  loading?: boolean
  achievementOverview: AchievementOverview
  recentAchievements: RecentAchievementRecord[]
}>()

const router = useRouter()

const summaryItems = computed(() => [
  { label: '核心科研积分', value: `${props.achievementOverview.total_score ?? 0} 分` },
  { label: '学术产出', value: `${props.achievementOverview.paper_score ?? 0} 分 / ${props.achievementOverview.paper_count} 项` },
  { label: '科研项目', value: `${props.achievementOverview.project_score ?? 0} 分 / ${props.achievementOverview.project_count} 项` },
  {
    label: '平台科普',
    value: `${props.achievementOverview.academic_service_score ?? 0} 分 / ${props.achievementOverview.academic_service_count} 项`,
  },
])
</script>

<template>
  <el-card class="achievement-card workspace-surface-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span>代表成果速览</span>
        <el-button type="primary" plain @click="router.push('/entry')">去管理成果</el-button>
      </div>
    </template>

    <div class="summary-grid">
      <div v-for="item in summaryItems" :key="item.label" class="summary-item">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>

    <el-skeleton :loading="Boolean(loading)" animated>
      <template #template>
        <div class="skeleton-list">
          <el-skeleton-item variant="h3" style="width: 50%" />
          <el-skeleton-item variant="text" style="width: 100%" />
          <el-skeleton-item variant="text" style="width: 82%" />
        </div>
      </template>

      <template #default>
        <div v-if="recentAchievements.length" class="achievement-list">
          <article v-for="item in recentAchievements.slice(0, 4)" :key="`${item.type}-${item.id}`" class="achievement-item">
            <div class="achievement-head">
              <strong>{{ item.title }}</strong>
              <el-tag effect="plain">{{ item.type_label }}</el-tag>
            </div>
            <p class="achievement-detail">{{ item.detail }}</p>
            <p class="achievement-meta">{{ item.highlight }} / {{ item.date_acquired }}</p>
          </article>
        </div>

        <el-empty v-else description="当前暂无可展示的代表成果，可先前往成果工作台补充数据。" />
      </template>
    </el-skeleton>
  </el-card>
</template>

<style scoped>
.achievement-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.card-header,
.achievement-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.summary-item,
.achievement-item {
  padding: 18px 20px;
  border-radius: 20px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.summary-item span {
  display: block;
  margin-bottom: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.summary-item strong {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 700;
}

.achievement-head strong {
  color: var(--text-primary);
  font-size: 20px;
  line-height: 1.45;
}

.achievement-list,
.skeleton-list {
  display: grid;
  gap: 14px;
}

.achievement-detail,
.achievement-meta {
  margin: 6px 0 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.achievement-meta {
  color: var(--text-tertiary);
  font-size: 13px;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
