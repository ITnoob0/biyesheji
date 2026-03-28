<script setup lang="ts">
import { ChatDotRound, DataAnalysis, DocumentAdd, MagicStick } from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  achievementTotal: number
  representativeCount: number
}>()

const router = useRouter()

const quickLinks = computed(() => [
  {
    key: 'achievements',
    title: '成果工作台',
    description: '录入论文、项目、知识产权、教学成果和学术服务。',
    stat: `${props.achievementTotal} 项成果`,
    icon: DocumentAdd,
    actionLabel: '进入成果页',
    action: () => router.push('/entry'),
  },
  {
    key: 'portrait',
    title: '教师画像',
    description: '查看画像摘要、研究标签、雷达维度和趋势图。',
    stat: `${props.representativeCount} 条成果速览`,
    icon: DataAnalysis,
    actionLabel: '查看画像',
    action: () => router.push('/dashboard'),
  },
  {
    key: 'recommendations',
    title: '项目推荐',
    description: '查看与当前研究方向和成果相关的项目指南推荐。',
    stat: '规则增强推荐',
    icon: MagicStick,
    actionLabel: '查看推荐',
    action: () => router.push('/project-recommendations'),
  },
  {
    key: 'assistant',
    title: '智能问答',
    description: '围绕教师画像、成果结构和推荐理由生成说明。',
    stat: '单场景问答',
    icon: ChatDotRound,
    actionLabel: '进入问答',
    action: () => router.push('/assistant-demo'),
  },
])
</script>

<template>
  <el-card class="link-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span>统一入口</span>
        <el-tag type="primary" effect="plain">教师视角导航</el-tag>
      </div>
    </template>

    <el-alert
      title="个人中心已作为教师默认工作台入口，以下模块可从这里继续进入；顶部品牌按钮也会优先返回个人中心。"
      type="info"
      :closable="false"
      show-icon
    />

    <div class="link-grid">
      <article v-for="item in quickLinks" :key="item.key" class="link-item">
        <div class="link-head">
          <el-icon class="link-icon">
            <component :is="item.icon" />
          </el-icon>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
          </div>
        </div>
        <div class="link-footer">
          <el-tag effect="plain">{{ item.stat }}</el-tag>
          <el-button type="primary" plain @click="item.action()">{{ item.actionLabel }}</el-button>
        </div>
      </article>
    </div>
  </el-card>
</template>

<style scoped>
.link-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
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
  margin-top: 16px;
}

.link-item {
  display: grid;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 20px;
  background: #f8fbff;
}

.link-head {
  align-items: flex-start;
  justify-content: flex-start;
}

.link-head strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
}

.link-head p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.link-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(15, 118, 110, 0.14));
  color: #2563eb;
  font-size: 20px;
  flex-shrink: 0;
}

.link-footer {
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .card-header,
  .link-head,
  .link-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
