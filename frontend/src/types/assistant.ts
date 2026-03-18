export type AssistantQuestionType = 'portrait_summary' | 'achievement_summary' | 'guide_reason'

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

export interface AssistantAnswerResponse {
  title: string
  answer: string
  data_sources: string[]
  scope_note: string
  non_coverage_note: string
  acceptance_scope: string
  teacher_snapshot: AssistantTeacherSnapshot
  question_type: AssistantQuestionType
  related_reasons?: string[]
  guide_snapshot?: AssistantGuideSnapshot
}
