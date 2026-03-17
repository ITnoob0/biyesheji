export type TabName =
  | 'papers'
  | 'projects'
  | 'intellectual-properties'
  | 'teaching-achievements'
  | 'academic-services'

export type BibtexPreviewStatus = 'ready' | 'duplicate' | 'invalid'

export interface PaperRecord {
  id: number
  title: string
  abstract: string
  date_acquired: string
  paper_type_display: string
  journal_name: string
  keywords: string[]
}

export interface ProjectRecord {
  id: number
  title: string
  date_acquired: string
  level_display: string
  role_display: string
  funding_amount: string
  status: string
}

export interface IpRecord {
  id: number
  title: string
  date_acquired: string
  ip_type_display: string
  registration_number: string
  is_transformed: boolean
}

export interface TeachingRecord {
  id: number
  title: string
  date_acquired: string
  achievement_type_display: string
  level: string
}

export interface ServiceRecord {
  id: number
  title: string
  date_acquired: string
  service_type_display: string
  organization: string
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
