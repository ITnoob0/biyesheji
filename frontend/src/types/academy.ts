export interface AcademyStatisticItem {
  title: string
  value: number
  suffix?: string
  icon: string
  iconClass: string
  helper?: string
}

export interface YearlyTrendRecord {
  year: number
  paper_count: number
  project_count: number
  ip_count: number
  teaching_count: number
  service_count: number
  achievement_total: number
}

export interface ScopeComparisonTrendRecord {
  year: number
  scope_achievement_total: number
  baseline_achievement_total: number
  scope_paper_count: number
  baseline_paper_count: number
}

export interface DepartmentDistributionRecord {
  name: string
  value: number
}

export interface TopActiveTeacherRecord {
  user_id: number
  teacher_name: string
  department: string
  title: string
  paper_count: number
  project_count: number
  ip_count: number
  teaching_count: number
  service_count: number
  collaboration_count: number
  citation_total: number
  achievement_total: number
  latest_active_year: number | null
  rank_value: number
  rank_label: string
}

export interface CollaborationOverview {
  coauthor_relation_total: number
  teachers_with_collaboration: number
  paper_with_collaboration: number
  average_coauthors_per_paper: number
}

export interface AcademyDataMeta {
  source_note: string
  acceptance_scope: string
  future_extension_hint: string
  realtime_metrics: string[]
  offline_candidate_metrics: string[]
  export_note: string
  drilldown_scope_note: string
  statistics_boundary_note: string
}

export interface AcademyTeacherOption {
  user_id: number
  teacher_name: string
  department: string
  title: string
}

export interface AcademyFilterOptions {
  departments: string[]
  teacher_titles: string[]
  teachers: AcademyTeacherOption[]
  years: number[]
  achievement_types: Array<{ value: string; label: string }>
  ranking_modes: Array<{ value: string; label: string }>
}

export interface AcademyActiveFilters {
  department: string
  compare_department?: string
  teacher_id: number | null
  teacher_title: string
  year: number | null
  has_collaboration: boolean | null
  achievement_type: string
  rank_by: string
}

export interface DepartmentBreakdownRecord {
  department: string
  teacher_count: number
  achievement_total: number
  paper_count: number
  project_count: number
  ip_count: number
  teaching_count: number
  service_count: number
  collaboration_count: number
  citation_total: number
}

export interface AcademyTrendSummary {
  latest_year: number | null
  previous_year: number | null
  latest_total: number
  previous_total: number
  total_delta: number
  paper_delta: number
  project_delta: number
  direction: string
  description: string
}

export interface AcademyComparisonSummary {
  scope_label: string
  compare_label: string
  teacher_total: number
  teacher_share: number
  achievement_total: number
  achievement_share: number
  collaboration_total: number
  collaboration_density: number
  description: string
}

export interface AcademyOverviewResponse {
  statistics: AcademyStatisticItem[]
  yearly_trend: YearlyTrendRecord[]
  comparison_trend: ScopeComparisonTrendRecord[]
  trend_summary: AcademyTrendSummary
  comparison_summary: AcademyComparisonSummary
  department_distribution: DepartmentDistributionRecord[]
  comparison_department_distribution?: DepartmentDistributionRecord[]
  department_breakdown: DepartmentBreakdownRecord[]
  top_active_teachers: TopActiveTeacherRecord[]
  collaboration_overview: CollaborationOverview
  ranking_meta: {
    current_rank_by: string
    current_rank_label: string
  }
  drilldown: {
    selected_department_summary?: {
      department: string
      teacher_count: number
      top_teacher_count: number
      recent_record_count: number
    } | null
    department_top_teachers: TopActiveTeacherRecord[]
    department_recent_achievements: Array<{
      type: string
      title: string
      teacher_name: string
      department: string
      date_acquired: string
      detail: string
    }>
    selected_teacher_summary?: {
      user_id: number
      teacher_name: string
      department: string
      title: string
      achievement_total: number
      paper_count: number
      project_count: number
      ip_count: number
      teaching_count: number
      service_count: number
      citation_total: number
      collaboration_count: number
    } | null
    teacher_recent_achievements: Array<{
      type: string
      title: string
      teacher_name: string
      department: string
      date_acquired: string
      detail: string
    }>
  }
  recent_scope_records: Array<{
    type: string
    title: string
    teacher_name: string
    department: string
    date_acquired: string
    detail: string
  }>
  data_meta: AcademyDataMeta
  active_filters: AcademyActiveFilters
  filter_options: AcademyFilterOptions
}
