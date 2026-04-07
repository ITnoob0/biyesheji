export type TabName =
  | 'papers'
  | 'projects'
  | 'intellectual-properties'
  | 'teaching-achievements'
  | 'academic-services'

export type AchievementReviewStatus = 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED'

export type BibtexPreviewStatus = 'ready' | 'duplicate' | 'invalid'

export interface BibtexIssueDetail {
  code: string
  category: string
  field?: string
  severity: string
  message: string
}

export interface CoAuthorDetail {
  id: number
  name: string
  author_rank: number | null
  is_corresponding: boolean
  organization: string
  is_internal: boolean
  internal_teacher: number | null
  user_id?: number | null
}

export interface CoAuthorRecordInput {
  name: string
  user_id?: number | null
  is_internal?: boolean
  order?: number | null
  author_rank?: number | null
  is_corresponding?: boolean
}

export interface MetadataAlertDetail {
  code: string
  field: string
  label: string
  severity: string
  message: string
}

export interface TeacherOwnedAchievementRecord {
  id: number
  teacher: number
  teacher_name: string
  title: string
  date_acquired: string
  status: AchievementReviewStatus
  status_label: string
  created_at?: string
}

export interface PaperRecord extends TeacherOwnedAchievementRecord {
  abstract: string
  paper_type: string
  paper_type_display: string
  journal_name: string
  journal_level: string
  published_volume: string
  published_issue: string
  pages: string
  source_url: string
  citation_count: number
  is_first_author: boolean
  is_corresponding_author: boolean
  is_representative: boolean
  doi: string
  publication_year: number | null
  keywords: string[]
  coauthor_details: CoAuthorDetail[]
  metadata_alerts: string[]
  metadata_alert_details: MetadataAlertDetail[]
}

export interface ProjectRecord extends TeacherOwnedAchievementRecord {
  level: string
  level_display: string
  role: string
  role_display: string
  funding_amount: string
  project_status: string
}

export interface IpRecord extends TeacherOwnedAchievementRecord {
  ip_type: string
  ip_type_display: string
  role: string
  role_display: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingRecord extends TeacherOwnedAchievementRecord {
  achievement_type: string
  achievement_type_display: string
  role: string
  role_display: string
  level: string
}

export interface ServiceRecord extends TeacherOwnedAchievementRecord {
  service_type: string
  service_type_display: string
  organization: string
}

export interface PaperFormState {
  title: string
  abstract: string
  date_acquired: string
  paper_type: string
  journal_name: string
  journal_level: string
  published_volume: string
  published_issue: string
  pages: string
  source_url: string
  citation_count: number
  is_first_author: boolean
  is_corresponding_author: boolean
  is_representative: boolean
  doi: string
  coauthor_records: CoAuthorRecordInput[]
}

export interface ProjectFormState {
  title: string
  date_acquired: string
  level: string
  role: string
  funding_amount: number
  project_status: string
}

export interface IpFormState {
  title: string
  date_acquired: string
  ip_type: string
  role: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingFormState {
  title: string
  date_acquired: string
  achievement_type: string
  role: string
  level: string
}

export interface ServiceFormState {
  title: string
  date_acquired: string
  service_type: string
  organization: string
}

export interface PaperMutationPayload {
  title: string
  abstract: string
  date_acquired: string
  paper_type: string
  journal_name: string
  journal_level: string
  published_volume: string
  published_issue: string
  pages: string
  source_url: string
  citation_count: number
  is_first_author: boolean
  is_corresponding_author: boolean
  is_representative: boolean
  doi: string
  coauthors: string[]
  coauthor_records?: CoAuthorRecordInput[]
}

export interface ProjectMutationPayload {
  title: string
  date_acquired: string
  level: string
  role: string
  funding_amount: number
  project_status: string
}

export interface IpMutationPayload {
  title: string
  date_acquired: string
  ip_type: string
  role: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingMutationPayload {
  title: string
  date_acquired: string
  achievement_type: string
  role: string
  level: string
}

export interface ServiceMutationPayload {
  title: string
  date_acquired: string
  service_type: string
  organization: string
}

export interface AchievementListResponseMap {
  papers: PaperRecord[]
  projects: ProjectRecord[]
  'intellectual-properties': IpRecord[]
  'teaching-achievements': TeachingRecord[]
  'academic-services': ServiceRecord[]
}

export interface AchievementRecordMap {
  papers: PaperRecord
  projects: ProjectRecord
  'intellectual-properties': IpRecord
  'teaching-achievements': TeachingRecord
  'academic-services': ServiceRecord
}

export interface AchievementMutationPayloadMap {
  papers: PaperMutationPayload
  projects: ProjectMutationPayload
  'intellectual-properties': IpMutationPayload
  'teaching-achievements': TeachingMutationPayload
  'academic-services': ServiceMutationPayload
}

export interface AchievementQueryState {
  papers: {
    search: string
    paper_type: string
    year: string
    is_representative: string
    sort_by: string
  }
  projects: {
    search: string
  }
  'intellectual-properties': {
    search: string
  }
  'teaching-achievements': {
    search: string
  }
  'academic-services': {
    search: string
  }
}

export interface BibtexPreviewEntry {
  source_index: number
  citation_key: string
  entry_type: string
  title: string
  abstract: string
  date_acquired: string
  paper_type: string
  journal_name: string
  journal_level: string
  published_volume: string
  published_issue: string
  pages: string
  source_url: string
  citation_count: number
  is_first_author: boolean
  is_representative: boolean
  doi: string
  coauthors: string[]
  preview_status: BibtexPreviewStatus
  issues: string[]
  issue_details: BibtexIssueDetail[]
  issue_categories: string[]
}

export interface BibtexPreviewSummary {
  total_count: number
  ready_count: number
  duplicate_count: number
  invalid_count: number
  category_counts?: Record<string, number>
}

export interface BibtexPreviewResponse {
  entries: BibtexPreviewEntry[]
  summary: BibtexPreviewSummary
  parser: string
  pdf_import_note: string
  acceptance_scope: string
}

export interface BibtexImportFailureRecord {
  source_index?: number
  title: string
  doi: string
  reason_code?: string
  reason_label?: string
  reason_category?: string
  issue_summary?: string
  errors: Record<string, string[] | string>
}

export interface BibtexImportResponse {
  imported_count: number
  skipped_count: number
  failed_count: number
  classified_counts?: Record<string, number>
  imported_records: Array<{ id: number; title: string; doi: string }>
  skipped_entries: BibtexImportFailureRecord[]
  failed_entries: BibtexImportFailureRecord[]
}

export interface PaperSummaryRecord {
  id: number
  title: string
  date_acquired: string
  paper_type: string
  paper_type_display: string
  journal_name: string
  citation_count: number
  is_representative: boolean
  metadata_alerts: string[]
  metadata_alert_details: MetadataAlertDetail[]
}

export interface PaperSummaryResponse {
  total_count: number
  representative_count: number
  recent_count: number
  missing_doi_count: number
  missing_source_url_count: number
  incomplete_metadata_count: number
  duplicate_doi_count: number
  yearly_distribution: Array<{ year: number; count: number }>
  type_distribution: Array<{ paper_type: string; label: string; count: number }>
  recent_records: PaperSummaryRecord[]
  metadata_alert_breakdown?: Array<{ code: string; label: string; severity: string; count: number }>
}

export interface PaperOperationLogRecord {
  id: number
  paper: number | null
  action: string
  action_label: string
  source: string
  source_label: string
  summary: string
  changed_fields: string[]
  metadata_flags: string[]
  paper_title_snapshot: string
  paper_doi_snapshot: string
  created_at: string
}

export interface AchievementOperationLogRecord {
  id: number
  achievement_type: TabName
  achievement_type_label: string
  achievement_id: number | null
  action: string
  action_label: string
  source: string
  source_label: string
  operator: number | null
  operator_name: string
  summary: string
  changed_fields: string[]
  change_details: Array<{
    field: string
    from: string
    to: string
    summary: string
  }>
  title_snapshot: string
  detail_snapshot: string
  snapshot_payload: Record<string, string>
  review_comment: string
  created_at: string
}

export interface AchievementWorkflowHistoryResponse {
  achievement_id: number
  history: AchievementOperationLogRecord[]
}

export interface AchievementReviewActionResponse {
  id: number
  teacher: number
  teacher_name: string
  title: string
  status: AchievementReviewStatus
  status_label: string
}

export interface CleanupSuggestion {
  key: string
  label: string
  description: string
  count: number
  example_ids: number[]
}

export interface RepresentativeOverview {
  count: number
  top_items: Array<{
    id: number
    title: string
    journal_name: string
    date_acquired: string
    citation_count: number
    metadata_alerts: string[]
  }>
}

export interface PaperGovernanceResponse {
  summary: PaperSummaryResponse
  representative_overview: RepresentativeOverview
  cleanup_suggestions: CleanupSuggestion[]
  compare_candidates: Array<{
    id: number
    title: string
    journal_name: string
    date_acquired: string
    citation_count: number
    is_representative: boolean
  }>
  recent_operations: PaperOperationLogRecord[]
}

export interface PaperCompareRow {
  field: string
  label: string
  left: string | number
  right: string | number
}

export interface PaperComparisonResponse {
  left: {
    id: number
    title: string
    metadata_alerts: MetadataAlertDetail[]
    keywords: string[]
    coauthors: string[]
  }
  right: {
    id: number
    title: string
    metadata_alerts: MetadataAlertDetail[]
    keywords: string[]
    coauthors: string[]
  }
  comparison_rows: PaperCompareRow[]
  summary: {
    citation_gap: number
    metadata_completeness_gap: number
    shared_keywords: string[]
    shared_coauthors: string[]
    left_alert_count: number
    right_alert_count: number
  }
}

export interface PaperHistoryResponse {
  paper_id: number
  history: PaperOperationLogRecord[]
}

export interface AchievementOperationHistoryResponse {
  history: AchievementOperationLogRecord[]
}

export interface PaperRepresentativeBatchResponse {
  updated_count: number
  updated_ids: number[]
  is_representative: boolean
}

export interface PaperCleanupResponse {
  updated_count: number
  updated_ids: number[]
  action: string
}

export interface PortraitSnapshot {
  id?: number
  user: number
  year: number
  dimension_scores: Record<string, number>
  total_score: number
  created_at: string
}
