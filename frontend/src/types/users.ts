export type TeacherAccountRoleCode = 'admin' | 'teacher'
export type TeacherContactVisibility = 'email_only' | 'phone_only' | 'both' | 'internal_only'

export interface TeacherPermissionScope {
  entry_role: TeacherAccountRoleCode
  scope_summary: string
  allowed_actions: string[]
  restricted_actions: string[]
  future_extension_hint: string
}

export interface TeacherAccountResponse {
  id: number
  employee_id: number
  username: string
  real_name: string
  department: string
  title: string
  email: string
  contact_phone: string
  contact_visibility: TeacherContactVisibility
  contact_visibility_label: string
  public_contact_channels: Array<{
    key: 'email' | 'phone'
    label: string
    value: string
  }>
  avatar_url: string
  research_direction: string[]
  bio: string
  discipline: string
  research_interests: string
  h_index: number
  is_active: boolean
  is_admin: boolean
  role_code: TeacherAccountRoleCode
  role_label: string
  permission_scope: TeacherPermissionScope
  password_reset_required: boolean
  password_updated_at: string | null
  security_notice: string
  account_status_label: string
  password_status_label: string
  next_action_hint: string
}

export interface TeacherCreateResponse extends TeacherAccountResponse {
  initial_password?: string
}

export interface TeacherPasswordResetResponse {
  detail: string
  temporary_password: string
  password?: string
  role_label: string
  password_reset_required: boolean
  security_notice: string
}

export interface PasswordChangeResponse {
  detail: string
  security_notice: string
  user: TeacherAccountResponse
}

export interface TeacherManagementSummaryResponse {
  total_count: number
  active_count: number
  inactive_count: number
  password_reset_required_count: number
  stable_password_count: number
  recovery_guidance: string
  future_extension_hint: string
}

export interface TeacherBulkActionResponse {
  detail: string
  action: 'activate' | 'deactivate' | 'reset_password'
  processed_count: number
  skipped_count: number
  processed_items: Array<{
    user_id: number
    username: string
    real_name: string
    account_status_label: string
    password_status_label: string
  }>
  skipped_items: Array<{
    user_id: number
    reason: string
  }>
  temporary_password: string
  management_summary: TeacherManagementSummaryResponse
  recovery_notice: string
}
