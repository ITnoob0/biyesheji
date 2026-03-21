export type GuideStatus = 'DRAFT' | 'OPEN' | 'CLOSED'
export type GuideLevel = 'NATIONAL' | 'PROVINCIAL' | 'MUNICIPAL' | 'ENTERPRISE'
export type GuideRuleProfile = 'BALANCED' | 'KEYWORD_FIRST' | 'DISCIPLINE_FIRST' | 'WINDOW_FIRST' | 'ACTIVITY_FIRST'

export interface ProjectGuideRecord {
  id: number
  title: string
  issuing_agency: string
  guide_level: GuideLevel
  guide_level_display: string
  status: GuideStatus
  status_display: string
  rule_profile: GuideRuleProfile
  rule_profile_display: string
  application_deadline?: string | null
  summary: string
  target_keywords: string[]
  target_disciplines: string[]
  recommendation_tags: string[]
  support_amount: string
  eligibility_notes: string
  source_url: string
  created_by_name: string
  created_at: string
  updated_at: string
}

export interface RecommendationTeacherSnapshot {
  user_id: number
  teacher_name: string
  keywords: string[]
  disciplines: string[]
  recent_activity_count: number
  activity_level?: string
}

export interface RecommendationMeta {
  source_note: string
  acceptance_scope: string
  future_extension_hint: string
  sorting_note: string
  current_strategy: string
}

export interface RecommendationExplanationDimension {
  key: string
  label: string
  score: number
  detail: string
}

export interface RecommendationComparisonSummary {
  primary_better_count: number
  compare_better_count: number
  tie_count: number
  biggest_gap_title: string
}

export interface RecommendationAdminAnalysis {
  teacher_name: string
  comparison_teacher_name: string
  priority_distribution: Record<string, number>
  rule_profile_distribution: Record<string, number>
  top_labels: Array<{ label: string; count: number }>
  recommended_count: number
}

export interface RecommendationItem extends ProjectGuideRecord {
  recommendation_score: number
  recommendation_reasons: string[]
  matched_keywords: string[]
  matched_disciplines: string[]
  match_category_tags: string[]
  recommendation_labels: string[]
  explanation_dimensions: RecommendationExplanationDimension[]
  priority_label: string
  recommendation_summary: string
  compare_score: number
  compare_delta: number
  comparison_summary: string
}

export interface RecommendationResponse {
  recommendations: RecommendationItem[]
  teacher_snapshot: RecommendationTeacherSnapshot
  comparison_teacher_snapshot?: RecommendationTeacherSnapshot | null
  comparison_summary?: RecommendationComparisonSummary | null
  admin_analysis?: RecommendationAdminAnalysis | null
  data_meta: RecommendationMeta
  empty_state: string
}
