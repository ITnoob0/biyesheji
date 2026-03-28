export type GuideStatus = 'DRAFT' | 'OPEN' | 'CLOSED' | 'ARCHIVED'
export type GuideLevel = 'NATIONAL' | 'PROVINCIAL' | 'MUNICIPAL' | 'ENTERPRISE'
export type RecommendationFeedbackSignal = '' | 'INTERESTED' | 'NOT_RELEVANT' | 'PLAN_TO_APPLY' | 'APPLIED'
export type GuideRuleProfile =
  | 'BALANCED'
  | 'KEYWORD_FIRST'
  | 'DISCIPLINE_FIRST'
  | 'WINDOW_FIRST'
  | 'ACTIVITY_FIRST'
  | 'PORTRAIT_FIRST'
  | 'FOUNDATION_FIRST'

export interface GuideRuleConfig {
  keyword_bonus?: number
  discipline_bonus?: number
  activity_bonus?: number
  window_bonus?: number
  support_bonus?: number
  portrait_bonus?: number
}

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
  rule_config: GuideRuleConfig
  application_deadline?: string | null
  summary: string
  target_keywords: string[]
  target_disciplines: string[]
  recommendation_tags: string[]
  support_amount: string
  eligibility_notes: string
  source_url: string
  lifecycle_note: string
  published_at?: string | null
  closed_at?: string | null
  archived_at?: string | null
  status_timeline: Array<{ key: string; label: string; time: string }>
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
  portrait_total_score?: number
  portrait_top_dimensions?: Array<{ key: string; name: string; value: number }>
}

export interface RecommendationMeta {
  source_note: string
  acceptance_scope: string
  future_extension_hint: string
  sorting_note: string
  current_strategy: string
  feedback_scope_note: string
  history_scope_note: string
  favorite_scope_note: string
  portrait_link_note: string
  feedback_ranking_boundary: string
  interaction_enabled: boolean
}

export interface RecommendationExplanationDimension {
  key: string
  label: string
  score: number
  max_score: number
  share_percent: number
  detail: string
}

export interface RecommendationPortraitLink {
  key: string
  label: string
  relation: string
  current_value: number
  detail: string
}

export interface RecommendationSupportingRecord {
  id: number
  type: string
  title: string
  detail: string
  date_acquired: string
  reason: string
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
  feedback_distribution: Record<string, number>
  favorited_count: number
  responded_guide_count: number
  response_rate: number
  positive_feedback_count: number
  negative_feedback_count: number
  plan_to_apply_count: number
  applied_count: number
  feedback_record_count: number
  latest_feedback_at: string
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
  portrait_dimension_links: RecommendationPortraitLink[]
  supporting_records: RecommendationSupportingRecord[]
  priority_label: string
  recommendation_summary: string
  compare_score: number
  compare_delta: number
  comparison_summary: string
  is_favorited: boolean
  latest_feedback_signal: RecommendationFeedbackSignal
  latest_feedback_label: string
  latest_feedback_note: string
  last_feedback_at?: string | null
}

export interface RecommendationHistoryItem {
  id: number
  batch_token: string
  guide_id?: number | null
  guide_title_snapshot: string
  guide_status_snapshot: string
  rule_profile_snapshot: string
  recommendation_score: number
  priority_label: string
  recommendation_labels: string[]
  portrait_dimension_links: RecommendationPortraitLink[]
  is_favorited_snapshot: boolean
  feedback_signal: RecommendationFeedbackSignal
  feedback_label: string
  feedback_note: string
  generated_at: string
  last_feedback_at?: string | null
  requested_by_name: string
}

export interface RecommendationFeedbackPreviewItem {
  guide_id?: number | null
  guide_title: string
  feedback_signal: RecommendationFeedbackSignal
  feedback_label: string
  feedback_note: string
  last_feedback_at: string
}

export interface RecommendationFeedbackSummary {
  distribution: Record<string, number>
  feedback_record_count: number
  responded_guide_count: number
  current_recommendation_count: number
  response_rate: number
  favorite_count: number
  interested_count: number
  plan_to_apply_count: number
  applied_count: number
  not_relevant_count: number
  positive_feedback_count: number
  negative_feedback_count: number
  latest_feedback_at: string
  recent_feedback_items: RecommendationFeedbackPreviewItem[]
  strategy_note: string
}

export interface RecommendationFavorites {
  guide_ids: number[]
  total_count: number
}

export interface RecommendationPortraitLinkSummary {
  teacher_total_score: number
  top_dimensions: Array<{ key: string; name: string; value: number }>
  link_note: string
}

export interface GuideLifecycleSummary {
  total_count: number
  draft_count: number
  open_count: number
  closed_count: number
  archived_count: number
  deadline_warning_count: number
  stale_open_count: number
  config_coverage_count: number
  status_distribution: Record<string, number>
  rule_profile_distribution: Record<string, number>
}

export interface RecommendationResponse {
  recommendations: RecommendationItem[]
  teacher_snapshot: RecommendationTeacherSnapshot
  comparison_teacher_snapshot?: RecommendationTeacherSnapshot | null
  comparison_summary?: RecommendationComparisonSummary | null
  admin_analysis?: RecommendationAdminAnalysis | null
  favorites: RecommendationFavorites
  history_preview: RecommendationHistoryItem[]
  feedback_summary: RecommendationFeedbackSummary
  portrait_link_summary: RecommendationPortraitLinkSummary
  history_batch_token: string
  data_meta: RecommendationMeta
  empty_state: string
}
