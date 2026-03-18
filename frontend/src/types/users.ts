export interface TeacherAccountResponse {
  id: number
  employee_id: number
  username: string
  real_name: string
  department: string
  title: string
  research_direction: string[]
  bio: string
  discipline: string
  research_interests: string
  h_index: number
  is_active: boolean
  is_admin: boolean
}

export interface TeacherCreateResponse extends TeacherAccountResponse {
  initial_password?: string
}

export interface TeacherPasswordResetResponse {
  detail: string
  password: string
}
