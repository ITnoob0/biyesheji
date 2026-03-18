export type TabName =
  | 'papers'
  | 'projects'
  | 'intellectual-properties'
  | 'teaching-achievements'
  | 'academic-services'

export type BibtexPreviewStatus = 'ready' | 'duplicate' | 'invalid'

export interface CoAuthorDetail {
  id: number
  name: string
  organization: string
  is_internal: boolean
  internal_teacher: number | null
}

export interface TeacherOwnedAchievementRecord {
  id: number
  teacher: number
  teacher_name: string
  title: string
  date_acquired: string
  created_at?: string
}

export interface PaperRecord extends TeacherOwnedAchievementRecord {
  abstract: string
  paper_type: string
  paper_type_display: string
  journal_name: string
  journal_level: string
  citation_count: number
  is_first_author: boolean
  doi: string
  keywords: string[]
  coauthor_details: CoAuthorDetail[]
}

export interface ProjectRecord extends TeacherOwnedAchievementRecord {
  level: string
  level_display: string
  role: string
  role_display: string
  funding_amount: string
  status: string
}

export interface IpRecord extends TeacherOwnedAchievementRecord {
  ip_type: string
  ip_type_display: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingRecord extends TeacherOwnedAchievementRecord {
  achievement_type: string
  achievement_type_display: string
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
  citation_count: number
  is_first_author: boolean
  doi: string
  coauthorInput: string
}

export interface ProjectFormState {
  title: string
  date_acquired: string
  level: string
  role: string
  funding_amount: number
  status: string
}

export interface IpFormState {
  title: string
  date_acquired: string
  ip_type: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingFormState {
  title: string
  date_acquired: string
  achievement_type: string
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
  citation_count: number
  is_first_author: boolean
  doi: string
  coauthors: string[]
}

export interface ProjectMutationPayload {
  title: string
  date_acquired: string
  level: string
  role: string
  funding_amount: number
  status: string
}

export interface IpMutationPayload {
  title: string
  date_acquired: string
  ip_type: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingMutationPayload {
  title: string
  date_acquired: string
  achievement_type: string
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
  citation_count: number
  is_first_author: boolean
  doi: string
  coauthors: string[]
  preview_status: BibtexPreviewStatus
  issues: string[]
}

export interface BibtexPreviewSummary {
  total_count: number
  ready_count: number
  duplicate_count: number
  invalid_count: number
}

export interface BibtexPreviewResponse {
  entries: BibtexPreviewEntry[]
  summary: BibtexPreviewSummary
  parser: string
  pdf_import_note: string
  acceptance_scope: string
}

export interface BibtexImportResponse {
  imported_count: number
  skipped_count: number
  failed_count: number
  imported_records: Array<{ id: number; title: string; doi: string }>
  skipped_entries: Array<{ source_index?: number; title: string; doi: string; errors: Record<string, string[] | string> }>
  failed_entries: Array<{ source_index?: number; title: string; doi: string; errors: Record<string, string[] | string> }>
}
