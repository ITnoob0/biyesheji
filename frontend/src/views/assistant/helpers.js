export const assistantQuestionOptions = [
  { label: '教师科研画像总结', value: 'portrait_summary' },
  { label: '教师画像如何形成', value: 'portrait_dimension_reason' },
  { label: '教师近年成果结构概括', value: 'achievement_summary' },
  { label: '当前推荐概览', value: 'guide_overview' },
  { label: '项目指南推荐原因说明', value: 'guide_reason' },
  { label: '学院统计概览', value: 'academy_summary' },
]

export const supportedQuestionTypes = assistantQuestionOptions.map(item => item.value)

export const buildAssistantFallbackAnswer = (questionType, reason = '当前问答接口暂时不可用。') => ({
  status: 'fallback',
  title: '问答结果已降级为说明模式',
  answer: '当前智能辅助结果暂时无法完整生成，系统已回退为基础说明模式。你仍可继续使用画像、成果、推荐和学院看板等主链路页面。',
  data_sources: ['当前系统页面与实时聚合结果'],
  source_details: [
    {
      label: '回退原因',
      value: reason,
      note: '当前仅返回受控的说明性结果，不影响其他页面继续访问。',
    },
  ],
  scope_note: '当前结果为前端安全回退说明，不是新的知识推理结果。',
  non_coverage_note: '当前不支持在接口失败时继续执行开放式问答。',
  acceptance_scope: '本能力属于当前阶段增强项，以模板化、可解释、可回退方式交付。',
  boundary_notes: ['当前为页面级安全回退说明。'],
  failure_notice: '问答异常已被拦截，页面仍可继续操作。',
  question_type: questionType,
})
