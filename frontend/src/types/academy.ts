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
  achievement_total: number
}

export interface DepartmentDistributionRecord {
  name: string
  value: number
}

export interface TopActiveTeacherRecord {
  user_id: number
  teacher_name: string
  department: string
  paper_count: number
  project_count: number
  achievement_total: number
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
}

export interface AcademyTeacherOption {
  user_id: number
  teacher_name: string
  department: string
}

export interface AcademyFilterOptions {
  departments: string[]
  teachers: AcademyTeacherOption[]
  years: number[]
}

export interface AcademyActiveFilters {
  department: string
  teacher_id: number | null
  year: number | null
}

export interface AcademyOverviewResponse {
  statistics: AcademyStatisticItem[]
  yearly_trend: YearlyTrendRecord[]
  department_distribution: DepartmentDistributionRecord[]
  top_active_teachers: TopActiveTeacherRecord[]
  collaboration_overview: CollaborationOverview
  data_meta: AcademyDataMeta
  active_filters: AcademyActiveFilters
  filter_options: AcademyFilterOptions
}
