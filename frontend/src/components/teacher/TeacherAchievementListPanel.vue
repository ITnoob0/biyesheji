<template>
  <div class="achievement-panel">
    <div class="filter-shell">
      <div class="filter-head">
        <div class="filter-title-group">
          <strong>成果筛选</strong>
          <span>按类型、时间和作者排名快速定位成果记录</span>
        </div>
        <div class="filter-actions">
          <el-tag type="info" effect="plain">共 {{ records.length }} 条</el-tag>
          <el-tag type="success" effect="plain">当前 {{ filteredRecords.length }} 条</el-tag>
          <el-button text type="primary" @click="resetFilters">重置筛选</el-button>
        </div>
      </div>

      <div class="filter-grid">
        <el-select v-model="selectedType" placeholder="按成果类型筛选">
          <el-option label="全部类型" value="all" />
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>

        <el-date-picker
          v-model="selectedDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DD"
          clearable
        />

        <el-select v-model="selectedAuthorRank" placeholder="按作者排名筛选">
          <el-option label="全部排名" value="all" />
          <el-option label="负责人 / 第一作者" value="lead" />
          <el-option label="参与成员" value="participating" />
          <el-option label="未区分排名" value="unspecified" />
        </el-select>
      </div>
    </div>

    <el-empty v-if="!filteredRecords.length" :description="emptyDescription || '暂无成果记录'" :image-size="88" />

    <div v-else class="achievement-list">
      <div
        v-for="item in filteredRecords"
        :id="resolveItemId?.(item)"
        :key="`${item.type}-${item.id}`"
        class="achievement-item"
        :class="{ 'achievement-item--active': isActiveRecord?.(item) }"
      >
        <div class="achievement-head">
          <div class="achievement-title-block">
            <strong>{{ item.title }}</strong>
            <div class="achievement-tags">
              <el-tag v-if="item.is_representative" size="small" type="success" effect="plain">代表作</el-tag>
              <el-tag size="small" effect="plain" :type="resolveAchievementTagType(item.type)">{{ item.type_label }}</el-tag>
              <el-tag size="small" type="info" effect="plain">{{ item.author_rank_label }}</el-tag>
            </div>
          </div>
          <span class="achievement-date">{{ item.date_acquired }}</span>
        </div>
        <p>{{ item.detail }}</p>
        <p class="achievement-highlight">{{ item.highlight }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AllAchievementRecord } from '../../views/dashboard/portrait'

const props = defineProps<{
  records: AllAchievementRecord[]
  emptyDescription?: string
  resolveItemId?: (record: AllAchievementRecord) => string | undefined
  isActiveRecord?: (record: AllAchievementRecord) => boolean
}>()

const selectedType = ref('all')
const selectedAuthorRank = ref<'all' | 'lead' | 'participating' | 'unspecified'>('all')
const selectedDateRange = ref<[string, string] | []>([])

const typeOptions = computed(() => {
  const seen = new Map<string, string>()
  for (const item of props.records) {
    if (!seen.has(item.type)) seen.set(item.type, item.type_label)
  }
  return Array.from(seen.entries()).map(([value, label]) => ({ value, label }))
})

const filteredRecords = computed(() =>
  props.records.filter(item => {
    if (selectedType.value !== 'all' && item.type !== selectedType.value) return false
    if (selectedAuthorRank.value !== 'all' && item.author_rank_category !== selectedAuthorRank.value) return false

    if (selectedDateRange.value.length === 2) {
      const [start, end] = selectedDateRange.value
      if (item.date_acquired < start || item.date_acquired > end) return false
    }

    return true
  }),
)

const resetFilters = () => {
  selectedType.value = 'all'
  selectedAuthorRank.value = 'all'
  selectedDateRange.value = []
}

const resolveAchievementTagType = (type: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' => {
  const mapping: Record<string, 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
    paper: 'success',
    project: 'primary',
    intellectual_property: 'warning',
    teaching_achievement: 'info',
    academic_service: 'danger',
  }
  return mapping[type] || 'info'
}
</script>

<style scoped>
.achievement-panel {
  display: grid;
  gap: 18px;
}

.filter-shell {
  display: grid;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.9));
  border: 1px solid var(--border-color-soft);
}

.filter-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.filter-title-group {
  display: grid;
  gap: 6px;
}

.filter-title-group strong {
  color: var(--text-primary);
  font-size: 15px;
}

.filter-title-group span {
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.6;
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.achievement-list {
  display: grid;
  gap: 14px;
}

.achievement-item {
  padding: 18px 20px;
  border-radius: 20px;
  border: 1px solid var(--border-color-soft);
  background: var(--panel-bg);
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
}

.achievement-item--active {
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: 0 18px 42px rgba(37, 99, 235, 0.14);
  transform: translateY(-1px);
}

.achievement-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.achievement-title-block {
  display: grid;
  gap: 8px;
}

.achievement-title-block strong {
  color: var(--text-primary);
}

.achievement-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.achievement-date {
  color: var(--text-tertiary);
  white-space: nowrap;
}

.achievement-item p {
  margin: 0;
  line-height: 1.7;
  color: var(--text-tertiary);
}

.achievement-highlight {
  margin-top: 8px !important;
}

@media (max-width: 900px) {
  .filter-head {
    flex-direction: column;
  }

  .filter-actions {
    justify-content: flex-start;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .achievement-head {
    flex-direction: column;
  }

  .achievement-date {
    white-space: normal;
  }
}
</style>
