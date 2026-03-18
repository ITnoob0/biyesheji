import { resolvePostLoginRedirect } from '../src/utils/sessionFlow.js'
import { upsertAchievementRecord, removeAchievementRecord } from '../src/views/achievement-entry/recordState.js'
import { buildGraphSourceSummary } from '../src/views/graph/sourceState.js'
import { filterRecommendationItems, sortRecommendationItems } from '../src/views/project-guides/recommendationHelpers.js'

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const verifyRedirectRecovery = () => {
  assert(resolvePostLoginRedirect('/entry', '/profile/100001') === '/profile/100001', '应优先回跳缓存目标页')
  assert(resolvePostLoginRedirect('/entry', '') === '/entry', '应在无缓存回跳时使用路由 redirect')
  assert(resolvePostLoginRedirect('', '') === '/dashboard', '应在无 redirect 时回到画像主页')
}

const verifyAchievementListUpdate = () => {
  const baseList = [
    { id: 1, title: '旧论文' },
    { id: 2, title: '旧项目' },
  ]
  const updated = upsertAchievementRecord(baseList, { id: 1, title: '新论文' })
  assert(updated[0].title === '新论文', '编辑后列表应更新对应记录')

  const appended = upsertAchievementRecord(baseList, { id: 3, title: '新增成果' })
  assert(appended.length === 3 && appended[0].id === 3, '新增后列表应插入新记录')

  const removed = removeAchievementRecord(appended, 2)
  assert(removed.every(item => item.id !== 2), '删除后列表应移除对应记录')
}

const verifyGraphFallbackSummary = () => {
  const summary = buildGraphSourceSummary({
    source: 'mysql',
    fallback_used: true,
    notice: '当前图谱已自动回退到 MySQL 关系数据展示。',
  })
  assert(summary.title === 'MySQL 回退链路', '图谱回退时应展示 MySQL 回退说明')
  assert(summary.source === 'MYSQL', '图谱数据来源标签应标准化输出')
}

const verifyRecommendationFiltering = () => {
  const items = [
    {
      id: 1,
      title: '科研画像专项指南',
      issuing_agency: '省教育厅',
      summary: '聚焦科研画像与知识图谱',
      application_deadline: '2026-05-01',
      updated_at: '2026-03-10',
      recommendation_score: 78,
      match_category_tags: ['主题匹配型', '学科匹配型'],
    },
    {
      id: 2,
      title: '企业合作指南',
      issuing_agency: '某企业',
      summary: '聚焦工程合作',
      application_deadline: '2026-04-01',
      updated_at: '2026-03-01',
      recommendation_score: 48,
      match_category_tags: ['活跃度支撑型'],
    },
  ]

  const filtered = filterRecommendationItems(items, '科研画像', '主题匹配型')
  assert(filtered.length === 1 && filtered[0].id === 1, '推荐列表应支持按关键词和分类筛选')

  const sortedByDeadline = sortRecommendationItems(items, 'deadline')
  assert(sortedByDeadline[0].id === 2, '推荐列表应支持按申报窗口排序')
}

const run = () => {
  verifyRedirectRecovery()
  verifyAchievementListUpdate()
  verifyGraphFallbackSummary()
  verifyRecommendationFiltering()
  console.log('Third-round UI verification passed.')
}

run()
