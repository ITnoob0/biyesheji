export type AssistantQuestionType =
  | 'portrait_summary'
  | 'portrait_dimension_reason'
  | 'achievement_summary'
  | 'guide_reason'
  | 'guide_overview'
  | 'academy_summary'

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
}
