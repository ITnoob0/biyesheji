import { resolvePostLoginRedirect } from '../src/utils/sessionFlow.js'
import {
  buildAccountLifecycleHint,
  buildAdminRouteNotice,
  buildAdminPortraitSelectionNotice,
  buildPasswordSecurityNotice,
  buildPublicContactSummary,
  buildSessionRecoveryNotice,
  resolveContactVisibilityLabel,
  buildSelfOnlyNotice,
  resolveLoginFailureMessage,
  resolveRoleLabel,
} from '../src/utils/authPresentation.js'
import { buildApiErrorNotice, resolveApiErrorMessage } from '../src/utils/apiFeedback.js'
import {
  resolvePostLoginLandingPath,
  resolveWorkspaceHomePath,
  shouldRedirectAdminPortraitRoute,
} from '../src/utils/workspaceNavigation.js'
import { upsertAchievementRecord, removeAchievementRecord } from '../src/views/achievement-entry/recordState.js'
import {
  buildImportFeedbackLines,
  buildPaperDuplicateWarnings,
  buildPaperMetadataHints,
} from '../src/views/achievement-entry/paperLifecycle.js'
import { buildDimensionTrendNarrative, buildKeywordEvolution, buildThemeFocusSummary } from '../src/views/dashboard/portraitInsights.js'
import { buildGraphSourceSummary } from '../src/views/graph/sourceState.js'
import {
  buildDistributionCards,
  filterRecommendationItems,
  sortRecommendationItems,
} from '../src/views/project-guides/recommendationHelpers.js'
import { assistantQuestionOptions, buildAssistantFallbackAnswer } from '../src/views/assistant/helpers.js'

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const verifyRedirectRecovery = () => {
  assert(resolvePostLoginRedirect('/entry', '/profile/100001') === '/profile/100001', '应优先回跳缓存的目标页')
  assert(resolvePostLoginRedirect('/entry', '') === '/entry', '无缓存回跳时应使用路由 redirect')
  assert(resolvePostLoginRedirect('', '') === '/dashboard', '无 redirect 时应回到画像首页')

  assert(resolveWorkspaceHomePath({ is_admin: true }) === '/dashboard', '管理员工作台首页应支持画像主页')
  assert(resolveWorkspaceHomePath({ is_admin: false }) === '/profile-editor', '教师工作台首页应落到个人中心')
  assert(
    resolvePostLoginLandingPath('/dashboard', { id: 1, is_admin: true }) === '/dashboard',
    '管理员登录后应允许回到自己的画像主页',
  )
  assert(
    resolvePostLoginLandingPath('', { id: 100001, is_admin: false }) === '/profile-editor',
    '教师登录后默认应进入个人中心',
  )
  assert(
    resolvePostLoginLandingPath('/profile/1', { id: 1, is_admin: true }) === '/profile/1',
    '管理员登录后应允许进入自己的画像详情页',
  )
  assert(
    resolvePostLoginLandingPath('/profile/100001', { id: 1, is_admin: true }) === '/profile/100001',
    '管理员若明确查看指定教师画像，应保留该目标页',
  )
  assert(
    shouldRedirectAdminPortraitRoute({ name: 'dashboard', params: {} }, { id: 1, is_admin: true }) === false,
    '管理员访问 dashboard 时不应被错误重定向',
  )
  assert(
    shouldRedirectAdminPortraitRoute({ name: 'profile', params: { id: '1' } }, { id: 1, is_admin: true }) === false,
    '管理员访问自己的画像详情页时不应被错误重定向',
  )
  assert(
    shouldRedirectAdminPortraitRoute({ name: 'profile', params: { id: '100001' } }, { id: 1, is_admin: true }) === false,
    '管理员查看指定教师画像时不应被错误重定向',
  )
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

const verifyPaperLifecycleHelpers = () => {
  const warnings = buildPaperDuplicateWarnings(
    {
      title: '教师画像平台研究',
      abstract: '摘要',
      date_acquired: '2026-03-01',
      paper_type: 'JOURNAL',
      journal_name: '现代教育技术',
      journal_level: '',
      published_volume: '',
      published_issue: '',
      pages: '',
      source_url: '',
      citation_count: 0,
      is_first_author: true,
      is_representative: false,
      doi: '10.1000/repeat-doi',
      coauthorInput: '',
    },
    [
      {
        id: 1,
        title: '教师画像平台研究',
        journal_name: '现代教育技术',
        publication_year: 2026,
        doi: '10.1000/repeat-doi',
      },
    ],
    null,
  )

  assert(warnings.length === 2, '论文助手应同时提示 DOI 与题目/期刊/年份重复风险')

  const hints = buildPaperMetadataHints({
    title: '教师画像平台研究',
    abstract: '摘要',
    date_acquired: '2026-03-01',
    paper_type: 'JOURNAL',
    journal_name: '现代教育技术',
    journal_level: '',
    published_volume: '',
    published_issue: '',
    pages: '',
    source_url: '',
    citation_count: 0,
    is_first_author: true,
    is_representative: false,
    doi: '',
    coauthorInput: '',
  })
  assert(hints.length === 3, '论文助手应提示 DOI、页码和来源链接缺失')

  const feedbackLines = buildImportFeedbackLines({
    imported_count: 1,
    skipped_count: 1,
    failed_count: 1,
    imported_records: [],
    skipped_entries: [{ title: '重复论文', doi: '', issue_summary: '重复记录已跳过。', errors: {} }],
    failed_entries: [{ title: '异常论文', doi: '', issue_summary: '字段校验未通过。', errors: {} }],
  })
  assert(feedbackLines.length >= 5, 'BibTeX 导入反馈应包含统计和首条异常说明')
}

const verifyGraphFallbackSummary = () => {
  const summary = buildGraphSourceSummary({
    source: 'mysql',
    fallback_used: true,
    notice: '当前图谱已自动回退到 MySQL 关系数据展示。',
    fallback_tip: '当前已使用 MySQL 关系数据继续展示图谱主体与轻量分析。',
    calculation_note: '当前图分析主要依据教师成果、合作作者与论文关键词进行轻量统计。',
    source_scope_note: '当前图谱覆盖教师、论文、合作者、关键词以及项目、知识产权、教学成果和学术服务等节点。',
    degradation_note: '当前图谱已按 MySQL 回退链路提供主体展示与轻量分析，不执行复杂图计算。',
    interaction_note: '当前节点交互、路径说明与圈层概览只在当前已加载子图内解释。',
  })
  assert(summary.title === 'MySQL 回退链路', '图谱回退时应显示 MySQL 回退说明')
  assert(summary.source === 'MYSQL', '图谱数据来源标签应标准化输出')
  assert(summary.badge === '已降级', '图谱回退时应显示降级标记')
  assert(summary.fallbackTip.includes('轻量分析'), '图谱回退时应明确说明降级后仍可使用的能力')
  assert(summary.sourceScopeNote.includes('项目'), '图谱来源摘要应说明当前节点覆盖范围')
  assert(summary.degradationNote.includes('MySQL'), '图谱来源摘要应说明当前降级链路')
  assert(summary.interactionNote.includes('路径说明'), '图谱来源摘要应说明当前交互与路径解释边界')
}

const verifyPortraitInsights = () => {
  const papers = [
    {
      id: 1,
      date_acquired: '2026-03-01',
      keywords: ['教师画像', '知识图谱', '教师画像'],
    },
    {
      id: 2,
      date_acquired: '2025-05-01',
      keywords: ['知识图谱', '科研评价'],
    },
    {
      id: 3,
      date_acquired: '2025-06-01',
      keywords: ['教师画像'],
    },
  ]

  const keywordEvolution = buildKeywordEvolution(papers)
  assert(keywordEvolution[0].year === 2026, '关键词演化应按年份倒序输出')
  assert(keywordEvolution[0].keywords[0].name === '教师画像', '关键词演化应统计当年高频主题')

  const focusSummary = buildThemeFocusSummary(papers)
  assert(focusSummary.ratio > 0, '主题聚焦摘要应输出集中度比例')
  assert(focusSummary.topKeywords[0].name === '教师画像', '主题聚焦摘要应给出高频主题')

  const narrative = buildDimensionTrendNarrative([
    { year: 2025, total_score: 52.4 },
    { year: 2026, total_score: 61.1 },
  ])
  assert(narrative.includes('提升'), '画像趋势叙述应反映最近一年走势')
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
      guide_level: 'PROVINCIAL',
      priority_label: '重点关注',
      recommendation_labels: ['主题贴合', '高匹配'],
      compare_delta: 14,
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
      guide_level: 'ENTERPRISE',
      priority_label: '可作备选',
      recommendation_labels: ['可作备选'],
      compare_delta: -6,
      match_category_tags: ['活跃度支撑型'],
    },
  ]

  const filtered = filterRecommendationItems(items, '科研画像', '主题匹配型')
  assert(filtered.length === 1 && filtered[0].id === 1, '推荐列表应支持按关键词和分类筛选')

  const filteredByOptions = filterRecommendationItems(items, '科研画像', '主题匹配型', {
    level: 'PROVINCIAL',
    priority: '重点关注',
    label: '主题贴合',
    favoritesOnly: true,
    favoriteIds: [1],
  })
  assert(filteredByOptions.length === 1 && filteredByOptions[0].id === 1, '推荐列表应支持级别、优先级、标签和收藏联动筛选')

  const sortedByDeadline = sortRecommendationItems(items, 'deadline')
  assert(sortedByDeadline[0].id === 2, '推荐列表应支持按申报窗口排序')

  const sortedByCompareDelta = sortRecommendationItems(items, 'compare_delta')
  assert(sortedByCompareDelta[0].id === 1, '推荐列表应支持按教师对比分差排序')

  const cards = buildDistributionCards({
    recommended_count: 2,
    priority_distribution: { 重点关注: 1, 可作备选: 1 },
    rule_profile_distribution: { 主题优先: 1, 均衡规则: 1 },
    response_rate: 50,
    responded_guide_count: 1,
    plan_to_apply_count: 1,
    applied_count: 0,
    feedback_record_count: 2,
    top_labels: [{ label: '主题贴合', count: 2 }],
  })
  assert(cards.length >= 5, '管理员分析摘要应输出更完整的反馈闭环卡片')
  assert(cards[0].value === 2, '管理员分析摘要应包含推荐总量')
  assert(cards[1].value === '50%', '管理员分析摘要应包含反馈覆盖率')
}

const verifyAuthPresentation = () => {
  assert(resolveRoleLabel({ is_admin: true }) === '系统管理员', '管理员身份应显示为系统管理员')
  assert(resolveRoleLabel({ is_admin: false }) === '教师账户', '教师身份应显示为教师账户')

  assert(
    buildPasswordSecurityNotice({ password_reset_required: true }).includes('临时密码'),
    '临时密码状态应提示尽快修改密码',
  )
  assert(
    buildPasswordSecurityNotice({ is_active: false }).includes('停用'),
    '停用账户应提示联系管理员恢复',
  )
  assert(
    buildAccountLifecycleHint({ password_reset_required: true }).includes('尽快'),
    '账户生命周期提示应提醒教师尽快修改临时密码',
  )
  assert(
    buildAccountLifecycleHint({ is_active: false }).includes('恢复启用'),
    '停用账户的生命周期提示应说明恢复启用要求',
  )
  assert(
    buildAdminRouteNotice('教师管理入口') === '当前账号为教师身份，不能访问教师管理入口。',
    '管理员入口提示应支持按功能统一生成',
  )
  assert(buildAdminPortraitSelectionNotice().includes('教师管理'), '管理员画像引导提示仍应保留教师管理入口说明')
  assert(
    buildSelfOnlyNotice('本人的画像与账户信息') === '教师账号只能查看本人的画像与账户信息',
    '教师自助范围提示应支持按资源统一生成',
  )

  const inactiveError = {
    response: {
      data: {
        detail: '账户已停用，请联系管理员处理。',
      },
    },
  }
  assert(
    resolveLoginFailureMessage(inactiveError) === '账户已停用，请联系管理员处理。',
    '登录失败提示应优先使用后端返回的明确原因',
  )
  assert(
    buildSessionRecoveryNotice('登录状态已失效，请重新登录。', true).includes('返回刚才访问的页面'),
    '会话恢复提示应说明重新登录后的恢复路径',
  )
  assert(resolveContactVisibilityLabel('both') === '公开邮箱和电话', '联系方式展示策略标签应支持双通道公开')
  assert(
    buildPublicContactSummary({
      public_contact_channels: [
        { label: '联系邮箱', value: 'teacher@example.com' },
        { label: '联系电话', value: '13800000000' },
      ],
    }).includes('联系电话'),
    '公开联系方式摘要应展示当前允许公开的联系渠道',
  )
  assert(
    buildPublicContactSummary({ contact_visibility: 'internal_only', public_contact_channels: [] }).includes('仅内部管理使用'),
    '联系方式仅内部可见时应明确提示边界',
  )

  const htmlError = {
    response: {
      data: '<!DOCTYPE html><html><body><h1>Traceback</h1></body></html>',
    },
  }
  assert(
    resolveLoginFailureMessage(htmlError) === '登录失败，请检查工号/账号和密码。',
    '登录失败提示不应原样展示后端 HTML 调试页',
  )

  const structuredError = {
    response: {
      data: {
        detail: '图谱加载失败，请稍后重试。',
        request_id: 'req-123',
        error: {
          message: '图谱加载失败，请稍后重试。',
          next_step: '可稍后重试，或先继续使用画像页其他模块。',
          request_id: 'req-123',
        },
      },
    },
  }

  assert(
    resolveApiErrorMessage(structuredError) === '图谱加载失败，请稍后重试。',
    '统一错误解析应优先读取后端标准错误消息',
  )

  const notice = buildApiErrorNotice(structuredError)
  assert(notice.requestHint.includes('req-123'), '统一错误提示应带出请求编号，便于排查')
  assert(notice.guidance.includes('继续使用画像页其他模块'), '统一错误提示应带出下一步建议')
}

const verifyAssistantHelpers = () => {
  assert(assistantQuestionOptions.length >= 9, '问答页面应提供更完整的受控模板集合')
  assert(
    assistantQuestionOptions.some(item => item.value === 'portrait_data_governance'),
    '问答页面应提供画像数据治理模板',
  )
  assert(
    assistantQuestionOptions.some(item => item.value === 'achievement_recommendation_link'),
    '问答页面应提供成果与推荐联动模板',
  )
  assert(
    assistantQuestionOptions.some(item => item.value === 'graph_status'),
    '问答页面应提供图谱链路状态模板',
  )

  const fallback = buildAssistantFallbackAnswer('portrait_summary', '接口暂不可用')
  assert(fallback.status === 'fallback', '问答异常时应生成结构化回退结果')
  assert(fallback.source_details[0].value.includes('接口暂不可用'), '问答回退结果应带出失败原因说明')
  assert(fallback.source_details[0].module_label === '问答模块', '问答回退结果应保留来源模块标签')
  assert(fallback.source_governance.answer_mode === '前端安全回退', '问答回退结果应保留来源治理说明')
}

const run = () => {
  verifyRedirectRecovery()
  verifyAchievementListUpdate()
  verifyPaperLifecycleHelpers()
  verifyGraphFallbackSummary()
  verifyPortraitInsights()
  verifyRecommendationFiltering()
  verifyAuthPresentation()
  verifyAssistantHelpers()
  console.log('Third-round UI verification passed.')
}

run()
