import axios from 'axios'
import type { Router } from 'vue-router'
import type { TeacherAccountResponse, TeacherPermissionScope } from '../types/users'

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_ID_KEY = 'user_id'
const IS_ADMIN_KEY = 'is_admin'
const USER_PROFILE_KEY = 'user_profile'
const AUTH_REDIRECT_KEY = 'auth_redirect_target'
const AUTH_FAILURE_REASON_KEY = 'auth_failure_reason'
const AUTH_NOTICE_KEY = 'auth_notice'
export const SESSION_AUTH_CHANGED_EVENT = 'session-auth-changed'

export type SessionUser = Pick<
  TeacherAccountResponse,
  | 'id'
  | 'username'
  | 'real_name'
  | 'department'
  | 'title'
  | 'email'
  | 'contact_phone'
  | 'avatar_url'
  | 'research_direction'
  | 'bio'
  | 'discipline'
  | 'research_interests'
  | 'h_index'
  | 'is_active'
  | 'is_admin'
  | 'role_code'
  | 'role_label'
  | 'permission_scope'
  | 'password_reset_required'
  | 'password_updated_at'
  | 'security_notice'
>

type SessionUserPayload = Omit<Partial<TeacherAccountResponse>, 'id'> & {
  id?: number | string
}

const buildDefaultPermissionScope = (raw: SessionUserPayload | null | undefined): TeacherPermissionScope => {
  const isAdmin = Boolean(raw?.is_admin)
  if (isAdmin) {
    return {
      entry_role: 'admin',
      scope_summary: '管理员可管理教师账户、项目指南和学院看板，并可查看指定教师的画像、图谱、推荐与问答结果。',
      allowed_actions: ['管理教师账户', '重置教师密码', '维护项目指南', '查看学院级统计看板', '查看指定教师数据'],
      restricted_actions: ['不通过教师成果入口直接代教师新增、修改或删除成果'],
      future_extension_hint: '后续如扩展多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中散落判断。',
    }
  }

  return {
    entry_role: 'teacher',
    scope_summary: '教师可维护本人资料与成果，并查看本人的画像、图谱、推荐与问答结果，不能访问管理员入口或其他教师数据。',
    allowed_actions: ['维护本人资料', '修改本人密码', '录入、编辑和删除本人成果', '查看本人的画像、图谱、推荐与问答结果'],
    restricted_actions: ['不能访问管理员入口', '不能管理教师账户', '不能查看其他教师的数据', '不能使用学院级统计和教师对比能力'],
    future_extension_hint: '后续如扩展多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中散落判断。',
  }
}

const normalizeSessionUser = (raw: SessionUserPayload | null | undefined): SessionUser => ({
  id: Number(raw?.id ?? 0),
  username: raw?.username ?? '',
  real_name: raw?.real_name ?? '',
  department: raw?.department ?? '',
  title: raw?.title ?? '',
  email: raw?.email ?? '',
  contact_phone: raw?.contact_phone ?? '',
  avatar_url: raw?.avatar_url ?? '',
  research_direction: Array.isArray(raw?.research_direction) ? raw.research_direction : [],
  bio: raw?.bio ?? '',
  discipline: raw?.discipline ?? '',
  research_interests: raw?.research_interests ?? '',
  h_index: Number(raw?.h_index ?? 0),
  is_active: raw?.is_active ?? true,
  is_admin: Boolean(raw?.is_admin),
  role_code: raw?.role_code === 'admin' ? 'admin' : 'teacher',
  role_label: raw?.role_label ?? (raw?.is_admin ? '系统管理员' : '教师账户'),
  permission_scope: raw?.permission_scope ?? buildDefaultPermissionScope(raw),
  password_reset_required: Boolean(raw?.password_reset_required),
  password_updated_at: raw?.password_updated_at ?? null,
  security_notice:
    raw?.security_notice ??
    (raw?.password_reset_required
      ? '当前密码为管理员初始化或重置后的临时密码，请登录后尽快修改。'
      : '请妥善保管工号与密码，建议使用高强度密码并定期更新。'),
})

const emitSessionAuthChanged = (): void => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(SESSION_AUTH_CHANGED_EVENT))
  }
}

export const getSessionToken = (): string | null => {
  const token = sessionStorage.getItem(TOKEN_KEY)?.trim()
  return token ? token : null
}

export const getSessionRefreshToken = (): string | null => {
  const token = sessionStorage.getItem(REFRESH_TOKEN_KEY)?.trim()
  return token ? token : null
}

export const clearSessionAuth = (): void => {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(USER_ID_KEY)
  sessionStorage.removeItem(IS_ADMIN_KEY)
  sessionStorage.removeItem(USER_PROFILE_KEY)
  emitSessionAuthChanged()
}

export const setAuthRedirectTarget = (target: string | null | undefined): void => {
  const normalized = typeof target === 'string' ? target.trim() : ''
  if (!normalized || normalized === '/login') {
    sessionStorage.removeItem(AUTH_REDIRECT_KEY)
    return
  }

  sessionStorage.setItem(AUTH_REDIRECT_KEY, normalized)
}

export const consumeAuthRedirectTarget = (): string | null => {
  const target = sessionStorage.getItem(AUTH_REDIRECT_KEY)?.trim() || null
  sessionStorage.removeItem(AUTH_REDIRECT_KEY)
  return target
}

export const setSessionExpiredReason = (reason: string | null | undefined): void => {
  const normalized = typeof reason === 'string' ? reason.trim() : ''
  if (!normalized) {
    sessionStorage.removeItem(AUTH_FAILURE_REASON_KEY)
    return
  }

  sessionStorage.setItem(AUTH_FAILURE_REASON_KEY, normalized)
}

export const consumeSessionExpiredReason = (): string | null => {
  const reason = sessionStorage.getItem(AUTH_FAILURE_REASON_KEY)?.trim() || null
  sessionStorage.removeItem(AUTH_FAILURE_REASON_KEY)
  return reason
}

export const setSessionNotice = (message: string | null | undefined): void => {
  const normalized = typeof message === 'string' ? message.trim() : ''
  if (!normalized) {
    sessionStorage.removeItem(AUTH_NOTICE_KEY)
    return
  }

  sessionStorage.setItem(AUTH_NOTICE_KEY, normalized)
}

export const consumeSessionNotice = (): string | null => {
  const message = sessionStorage.getItem(AUTH_NOTICE_KEY)?.trim() || null
  sessionStorage.removeItem(AUTH_NOTICE_KEY)
  return message
}

export const resetSessionFlowState = (): void => {
  sessionStorage.removeItem(AUTH_REDIRECT_KEY)
  sessionStorage.removeItem(AUTH_FAILURE_REASON_KEY)
  sessionStorage.removeItem(AUTH_NOTICE_KEY)
}

export const logoutSession = async (router?: Router): Promise<void> => {
  clearSessionAuth()
  resetSessionFlowState()

  if (router) {
    await router.replace({ name: 'login' })
  }
}

export const setSessionToken = (token: string, refreshToken?: string | null): void => {
  sessionStorage.setItem(TOKEN_KEY, token)
  if (refreshToken) {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  }
  emitSessionAuthChanged()
}

export const setSessionRefreshToken = (token: string): void => {
  sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
  emitSessionAuthChanged()
}

export const setSessionUser = (rawUser: Partial<TeacherAccountResponse>): SessionUser => {
  const user = normalizeSessionUser(rawUser)

  sessionStorage.setItem(USER_ID_KEY, String(user.id))
  sessionStorage.setItem(IS_ADMIN_KEY, user.is_admin ? 'true' : 'false')
  sessionStorage.setItem(USER_PROFILE_KEY, JSON.stringify(user))
  emitSessionAuthChanged()

  return user
}

export const getSessionUser = (): SessionUser | null => {
  const storedProfile = sessionStorage.getItem(USER_PROFILE_KEY)

  if (storedProfile) {
    try {
      return normalizeSessionUser(JSON.parse(storedProfile))
    } catch {
      sessionStorage.removeItem(USER_PROFILE_KEY)
    }
  }

  const storedUserId = sessionStorage.getItem(USER_ID_KEY)
  if (!storedUserId) {
    return null
  }

  return normalizeSessionUser({
    id: storedUserId,
    is_admin: sessionStorage.getItem(IS_ADMIN_KEY) === 'true',
  })
}

export const fetchCurrentSessionUser = async (): Promise<SessionUser> => {
  const response = await axios.get<TeacherAccountResponse>('/api/users/me/')
  return setSessionUser(response.data)
}

export const ensureSessionUserContext = async (): Promise<SessionUser | null> => {
  if (!getSessionToken()) {
    clearSessionAuth()
    return null
  }

  try {
    return await fetchCurrentSessionUser()
  } catch {
    clearSessionAuth()
    return null
  }
}
