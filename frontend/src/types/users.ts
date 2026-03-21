export type TeacherAccountRoleCode = 'admin' | 'teacher'

export interface TeacherAccountResponse {
  id: number
  employee_id: number
  username: string
  real_name: string
  department: string
  title: string
  email: string
  contact_phone: string
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
  password_reset_required: boolean
  password_updated_at: string | null
  security_notice: string
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
