export type EvaluationRuleVersionStatus = 'DRAFT' | 'ACTIVE' | 'ARCHIVED'
export type EvaluationRuleDiscipline = 'NATURAL' | 'HUMANITIES' | 'GENERAL'
export type EvaluationRuleEntryPolicy = 'REQUIRED' | 'FORBIDDEN'
export type EvaluationRuleScoreMode = 'FIXED' | 'PER_AMOUNT' | 'MANUAL'
export type EvaluationRuleMultiMatchPolicy = 'EXCLUSIVE_HIGHER' | 'STACKABLE' | 'MANUAL_REVIEW'
export type FilingWorkflowActor = 'TEACHER' | 'COLLEGE_ADMIN' | 'SYSTEM_ADMIN' | 'SYSTEM'

export interface EvaluationRuleVersionRecord {
  id: number
  code: string
  name: string
  source_document: string
  summary: string
  status: EvaluationRuleVersionStatus
  status_display: string
  created_by_name: string
  created_at: string
  updated_at: string
}

export interface EvaluationRuleCategoryRecord {
  id: number
  version: number
  version_name: string
  code: string
  name: string
  description: string
  dimension_key: string
  dimension_label: string
  entry_enabled: boolean
  include_in_total: boolean
  include_in_radar: boolean
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EvaluationRuleItemRecord {
  id: number
  version: number
  version_name: string
  category_ref: number | null
  category_code: string
  category_name: string
  category_dimension_key: string
  category_dimension_label: string
  rule_code: string
  category: string
  category_display: string
  discipline: EvaluationRuleDiscipline
  discipline_display: string
  entry_policy: EvaluationRuleEntryPolicy
  entry_policy_display: string
  score_mode: EvaluationRuleScoreMode
  score_mode_display: string
  base_score: string | number | null
  score_per_unit: string | number | null
  score_unit_label: string
  requires_amount_input: boolean
  is_team_rule: boolean
  team_distribution_note: string
  team_max_member_ratio: string | number
  conflict_group: string
  multi_match_policy: EvaluationRuleMultiMatchPolicy
  multi_match_policy_display: string
  entry_form_schema: Array<Record<string, unknown>>
  title: string
  description: string
  score_text: string
  note: string
  evidence_requirements: string
  include_in_total: boolean
  include_in_radar: boolean
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FilingWorkflowStepRecord {
  id: number
  version: number
  version_name: string
  step_order: number
  actor: FilingWorkflowActor
  actor_display: string
  title: string
  description: string
  material_requirements: string
  operation_note: string
  is_required: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EvaluationRuleGroup {
  id: number
  key: string
  label: string
  dimension_key: string
  dimension_label: string
  entry_enabled: boolean
  include_in_total: boolean
  include_in_radar: boolean
  items: EvaluationRuleItemRecord[]
}

export interface EvaluationRuleDashboardResponse {
  active_version: EvaluationRuleVersionRecord
  available_versions: EvaluationRuleVersionRecord[]
  summary: {
    rule_count: number
    included_count: number
    category_count: number
    workflow_step_count: number
  }
  categories: EvaluationRuleCategoryRecord[]
  grouped_rules: EvaluationRuleGroup[]
  workflow_steps: FilingWorkflowStepRecord[]
  permissions: {
    can_edit: boolean
    read_mode: 'editable' | 'readonly'
  }
}
