<script setup lang="ts">
import { ChatDotRound, DataAnalysis, DocumentAdd, MagicStick } from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { openFloatingAssistant } from '../../utils/assistantLauncher'

const props = defineProps<{
  achievementTotal: number
  representativeCount: number
}>()

const router = useRouter()

const quickLinks = computed(() => [
  {
    key: 'achievements',
    title: '成果工作台',
    description: '按评价规则录入学术产出、项目、获奖转化与平台科普成果。',
    icon: DocumentAdd,
    stat: `${props.achievementTotal} 项成果`,
    actionLabel: '进入成果页',
    action: () => router.push('/entry'),
  },
  {
    key: 'portrait',
    title: '教师画像',
    description: '查看画像摘要、研究标签、雷达维度和趋势图。',
    icon: DataAnalysis,
    stat: `${props.representativeCount} 条成果速览`,
    actionLabel: '查看画像',
    action: () => router.push('/dashboard'),
  },
  {
    key: 'recommendations',
    title: '项目推荐',
    description: '查看与当前研究方向和成果相关的项目指南推荐。',
    icon: MagicStick,
    stat: '规则增强推荐',
    actionLabel: '查看推荐',
    action: () => router.push('/project-recommendations'),
  },
  {
    key: 'assistant',
    title: 'AI 助手',
    description: '通过侧边悬挂助手完成画像、成果和推荐相关问答。',
    icon: ChatDotRound,
    stat: 'Dify 增强问答',
    actionLabel: '打开助手',
    action: () => openFloatingAssistant({ contextHint: 'personal-center' }),
  },
])
</script>

<template>
  <el-card class="link-card workspace-surface-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span>快捷入口</span>
        <el-tag type="primary" effect="plain">统一入口</el-tag>
      </div>
    </template>

    <div class="link-grid">
      <article v-for="item in quickLinks" :key="item.key" class="link-item">
        <div class="link-head">
          <el-icon class="link-icon">
            <component :is="item.icon" />
          </el-icon>
          <div class="link-copy">
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
          </div>
        </div>
        <div class="link-footer">
          <span class="link-stat">{{ item.stat }}</span>
          <el-button type="primary" plain @click="item.action()">{{ item.actionLabel }}</el-button>
        </div>
      </article>
    </div>
  </el-card>
</template>

<style scoped>
.link-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.card-header,
.link-head,
.link-footer {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
}

.link-grid {
  display: grid;
  gap: 16px;
}

.link-item {
  display: grid;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 20px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.link-head {
  align-items: flex-start;
  justify-content: flex-start;
}

.link-copy {
  display: grid;
  gap: 8px;
}

.link-copy strong {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
}

.link-copy p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.8;
}

.link-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(15, 118, 110, 0.14));
  color: var(--brand-primary);
  font-size: 20px;
  flex-shrink: 0;
}

.link-footer {
  flex-wrap: wrap;
}

.link-stat {
  color: var(--text-tertiary);
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .card-header,
  .link-head,
  .link-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .link-copy strong {
    font-size: 18px;
  }
}
</style>
