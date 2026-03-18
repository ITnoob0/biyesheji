export type GuideStatus = 'DRAFT' | 'OPEN' | 'CLOSED'
export type GuideLevel = 'NATIONAL' | 'PROVINCIAL' | 'MUNICIPAL' | 'ENTERPRISE'

export interface ProjectGuideRecord {
  id: number
  title: string
  issuing_agency: string
  guide_level: GuideLevel
  guide_level_display: string
  status: GuideStatus
  status_display: string
  application_deadline?: string | null
  summary: string
  target_keywords: string[]
  target_disciplines: string[]
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
}

export interface RecommendationMeta {
  source_note: string
  acceptance_scope: string
  future_extension_hint: string
  sorting_note: string
  current_strategy: string
}

export interface RecommendationItem extends ProjectGuideRecord {
  recommendation_score: number
  recommendation_reasons: string[]
  matched_keywords: string[]
  matched_disciplines: string[]
  match_category_tags: string[]
  priority_label: string
  recommendation_summary: string
}

export interface RecommendationResponse {
  recommendations: RecommendationItem[]
  teacher_snapshot: RecommendationTeacherSnapshot
  data_meta: RecommendationMeta
  empty_state: string
}
