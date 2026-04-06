<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { TabName } from '../types/achievements'
import AchievementReviewGovernancePanel from './achievement-entry/AchievementReviewGovernancePanel.vue'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import { buildAdminRouteNotice } from '../utils/authPresentation.js'

const router = useRouter()
const sessionUser = ref<SessionUser | null>(null)
const activeTab = ref<TabName>('papers')
const pageLoading = ref(false)

const canReview = computed(() => Boolean(sessionUser.value?.is_admin))
const isCollegeAdmin = computed(() => sessionUser.value?.role_code === 'college_admin')

const tabOptions: Array<{ name: TabName; label: string }> = [
  { name: 'papers', label: '论文成果' },
  { name: 'projects', label: '科研项目' },
  { name: 'intellectual-properties', label: '知识产权' },
  { name: 'teaching-achievements', label: '教学成果' },
  { name: 'academic-services', label: '学术服务' },
]

const handleReviewUpdated = () => {
  ElMessage.success('审核操作已完成')
}

onMounted(async () => {
  pageLoading.value = true
  try {
    sessionUser.value = await ensureSessionUserContext()
    if (!sessionUser.value?.is_admin) {
      ElMessage.warning(buildAdminRouteNotice('成果审核'))
      router.replace('/dashboard')
    }
  } finally {
    pageLoading.value = false
  }
})
</script>

<template>
  <div class="achievement-review-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">Achievement Review</p>
        <h1 class="workspace-hero__title">成果审核</h1>
        <p class="hero-text workspace-hero__text">
          审核本学院教师提交的科研成果，包括论文、项目、知识产权、教学成果和学术服务。
          <span v-if="sessionUser?.department"> · 当前学院：{{ sessionUser.department }}</span>
        </p>
      </div>
    </section>

    <section v-if="!pageLoading && canReview" class="review-content workspace-content-shell">
      <el-tabs v-model="activeTab" class="review-tabs">
        <el-tab-pane
          v-for="tab in tabOptions"
          :key="tab.name"
          :label="tab.label"
          :name="tab.name"
        >
          <AchievementReviewGovernancePanel
            :tab="tab.name"
            :can-review="canReview"
            @updated="handleReviewUpdated"
          />
        </el-tab-pane>
      </el-tabs>
    </section>

    <section v-if="!pageLoading && !canReview" class="workspace-status-result workspace-content-shell">
      <el-result icon="warning" title="无审核权限" sub-title="当前账号不具备成果审核权限。" />
    </section>
  </div>
</template>

<style scoped>
.achievement-review-page {
  min-height: 100%;
  padding: 24px;
  background: var(--page-bg);
}

.hero-panel {
  margin-bottom: 22px;
  padding: 28px 32px;
  border-radius: 28px;
  background: var(--hero-bg);
  color: var(--text-on-brand);
  box-shadow: var(--workspace-shadow-strong);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

h1 {
  margin: 0;
}

.hero-text {
  margin: 12px 0 0;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.86);
}

.review-content {
  margin-bottom: 20px;
}

.review-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.review-tabs :deep(.el-tabs__item) {
  font-size: 15px;
}
</style>
