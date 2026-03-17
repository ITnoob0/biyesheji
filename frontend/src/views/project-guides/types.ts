export type GuideStatus = 'DRAFT' | 'OPEN' | 'CLOSED'
export type GuideLevel = 'NATIONAL' | 'PROVINCIAL' | 'MUNICIPAL' | 'ENTERPRISE'

export type ProjectGuideRecord = {
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

export type RecommendationItem = ProjectGuideRecord & {
  recommendation_score: number
  recommendation_reasons: string[]
  matched_keywords: string[]
  matched_disciplines: string[]
}

export type RecommendationResponse = {
  recommendations: RecommendationItem[]
  teacher_snapshot: {
    user_id: number
    teacher_name: string
    keywords: string[]
    disciplines: string[]
    recent_activity_count: number
  }
  data_meta: {
    source_note: string
    acceptance_scope: string
    future_extension_hint: string
  }
  empty_state: string
}
