export type AssistantQuestionType =
  | 'portrait_summary'
  | 'portrait_dimension_reason'
  | 'portrait_data_governance'
  | 'achievement_summary'
  | 'achievement_portrait_link'
  | 'achievement_recommendation_link'
  | 'guide_reason'
  | 'guide_overview'
  | 'graph_status'
  | 'academy_summary'

export interface AssistantEvidenceLink {
  label: string
  page: 'portrait' | 'recommendations' | 'achievement-entry' | 'assistant' | 'academy-dashboard'
  section?:
    | 'portrait-dimensions'
    | 'portrait-achievements'
    | 'portrait-explanation'
    | 'portrait-graph'
    | 'recommendation-evidence'
    | 'achievement-records'
    | 'assistant-answer'
    | 'academy-ranking'
    | 'academy-drilldown'
  highlight?: string
  dimension_key?: string
  guide_id?: number
  record_type?: string
  record_id?: number
  department?: string
  year?: number | null
  note?: string
}

export interface AssistantTeacherSnapshot {
  user_id: number
  teacher_name: string
  department: string
  title: string
}

export interface AssistantGuideSnapshot {
  guide_id: number
  title: string
}

export interface AssistantSourceDetail {
  label: string
  value: string
  note: string
  module?: string
  module_label?: string
  page_label?: string
  availability_status?: 'ok' | 'limited' | 'fallback'
  availability_label?: string
  verification_text?: string
  link?: AssistantEvidenceLink
}

export interface AssistantSourceGovernance {
  answer_mode: string
  scope_label: string
  verification_note: string
  degraded_flags: string[]
  unavailable_flags: string[]
}

export interface AssistantAcademySnapshot {
  department: string
  year?: number | null
  teacher_total: number
  achievement_total: number
}

export interface AssistantAnswerResponse {
  status?: 'ok' | 'fallback'
  title: string
  answer: string
  data_sources: string[]
  source_details: AssistantSourceDetail[]
  scope_note: string
  non_coverage_note: string
  acceptance_scope: string
  boundary_notes?: string[]
  failure_notice?: string
  teacher_snapshot?: AssistantTeacherSnapshot
  question_type: AssistantQuestionType
  related_reasons?: string[]
  guide_snapshot?: AssistantGuideSnapshot
  academy_snapshot?: AssistantAcademySnapshot
  source_governance?: AssistantSourceGovernance
}

export interface AssistantChatSource {
  id: string
  title: string
  module: string
  snippet: string
  score: number
  link?: AssistantEvidenceLink
}

export interface AssistantChatResponse {
  status: 'ok' | 'fallback'
  title: string
  answer: string
  assistant_mode: 'rag-chat'
  model: string
  question: string
  context_hint?: string
  scope_note: string
  non_coverage_note: string
  acceptance_scope: string
  boundary_notes: string[]
  teacher_snapshot: AssistantTeacherSnapshot
  sources: AssistantChatSource[]
}

export interface DifyAssistantChatResponse {
  status: 'ok' | 'fallback'
  assistant_mode: 'dify-proxy'
  answer: string
  conversation_id: string
  model: string
  question: string
  message_id?: string
  error?: string
}
