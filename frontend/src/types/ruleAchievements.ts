export interface RuleAchievementFormFieldOption {
  label: string
  value: string
}

export interface RuleAchievementFormFieldSchema {
  key: string
  storage: 'root' | 'factual_payload'
  component: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'boolean'
  label: string
  required: boolean
  placeholder: string
  help_text: string
  options: RuleAchievementFormFieldOption[]
  column_span: number
  min?: number
  precision?: number
}

export interface RuleAchievementFormSectionSchema {
  key: string
  title: string
  description: string
  fields: RuleAchievementFormFieldSchema[]
}

export interface RuleAchievementCategoryOption {
  id: number
  code: string
  name: string
  description: string
  dimension_key: string
  dimension_label: string
  include_in_total: boolean
  include_in_radar: boolean
}

export interface RuleAchievementItemOption {
  id: number
  category_id: number
  rule_code: string
  title: string
  score_text: string
  score_mode: 'FIXED' | 'PER_AMOUNT' | 'MANUAL'
  base_score: string
  score_per_unit: string
  score_unit_label: string
  requires_amount_input: boolean
  is_team_rule: boolean
  team_distribution_note: string
  team_max_member_ratio: string
  description: string
  note: string
  evidence_requirements: string
  include_in_total: boolean
  include_in_radar: boolean
  entry_form_schema: Array<Record<string, unknown>>
  resolved_entry_form_schema: RuleAchievementFormSectionSchema[]
}

export interface RuleAchievementEntryConfigResponse {
  active_version: {
    id: number
    code: string
    name: string
  }
  categories: RuleAchievementCategoryOption[]
  items: RuleAchievementItemOption[]
}

export interface RuleAchievementScorePreview {
  score_mode: 'FIXED' | 'PER_AMOUNT' | 'MANUAL'
  score_text: string
  base_score: string
  score_per_unit: string
  score_unit_label: string
  requires_amount_input: boolean
  is_team_rule: boolean
  preview_score: string
  notes: string[]
}

export interface RuleAchievementAttachment {
  id: number
  original_name: string
  file: string
  file_url: string
  created_at: string
}

export interface RuleAchievementRecord {
  id: number
  teacher_name: string
  version: number
  category: number
  category_code: string
  category_name: string
  rule_item: number
  rule_item_code: string
  rule_item_title: string
  title: string
  external_reference: string
  date_acquired: string
  status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED'
  status_label: string
  issuing_organization: string
  publication_name: string
  role_text: string
  author_rank: number | null
  is_corresponding_author: boolean
  is_representative: boolean
  school_unit_order: string
  amount_value: string | number | null
  amount_unit: string
  keywords_text: string
  coauthor_names: string[]
  team_identifier: string
  team_total_members: number | null
  team_allocated_score: string | number | null
  team_contribution_note: string
  evidence_note: string
  factual_payload: Record<string, unknown>
  provisional_score: string
  final_score: string
  score_detail: Record<string, unknown>
  score_preview: RuleAchievementScorePreview
  review_comment: string
  reviewed_at: string | null
  attachments: RuleAchievementAttachment[]
  created_at: string
  updated_at: string
}

export interface RuleAchievementWorkflowHistory {
  history: Array<{
    id: number
    action: string
    action_label: string
    source: string
    source_label: string
    summary: string
    changed_fields: string[]
    snapshot_payload: Record<string, unknown>
    review_comment: string
    created_at: string
    operator_name: string
  }>
}
