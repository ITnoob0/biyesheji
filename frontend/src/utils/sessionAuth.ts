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
  | 'contact_visibility'
  | 'contact_visibility_label'
  | 'public_contact_channels'
  | 'avatar_url'
  | 'research_direction'
  | 'bio'
  | 'discipline'
  | 'research_interests'
  | 'is_active'
  | 'is_admin'
  | 'role_code'
  | 'role_label'
  | 'permission_scope'
  | 'password_reset_required'
  | 'password_updated_at'
  | 'security_notice'
  | 'account_status_label'
  | 'password_status_label'
  | 'next_action_hint'
>

type SessionUserPayload = Omit<Partial<TeacherAccountResponse>, 'id'> & {
  id?: number | string
}

const buildDefaultPermissionScope = (raw: SessionUserPayload | null | undefined): TeacherPermissionScope => {
  const roleCode =
    raw?.role_code === 'college_admin'
      ? 'college_admin'
      : raw?.role_code === 'admin'
        ? 'admin'
        : 'teacher'

  if (roleCode === 'admin') {
    return {
      entry_role: 'admin',
      scope_summary: '系统管理员可在全校范围管理教师账户、查看学院看板、维护项目指南，并查看教师画像、成果与管理分析结果。',
      allowed_actions: ['管理教师账户', '重置教师密码', '维护项目指南', '查看学院看板', '查看指定教师数据'],
      restricted_actions: ['不通过教师成果入口直接代教师新增、修改或删除成果'],
      future_extension_hint: '后续如继续扩展管理角色，应优先在统一权限入口中扩展，而不是在页面和接口中分散判断。',
    }
  }

  if (roleCode === 'college_admin') {
    return {
      entry_role: 'college_admin',
      scope_summary: '学院管理员保留教师本人账户能力，并可在本学院范围内查看教师信息、学院看板和项目指南管理结果，不具备全校管理范围。',
      allowed_actions: ['查看本学院教师信息', '查看本学院学院看板', '管理本学院教师账户', '查看本学院教师画像与成果'],
      restricted_actions: ['不能查看其他学院教师数据', '不能访问系统管理员全校范围管理能力'],
      future_extension_hint: '如后续继续扩展学院管理员能力，应继续保持学院范围约束，不上收为全校管理权限。',
    }
  }

  return {
    entry_role: 'teacher',
    scope_summary: '教师可维护本人资料与成果，并查看本人的画像、图谱、推荐与问答结果，不可访问管理员入口或其他教师数据。',
    allowed_actions: ['维护本人资料', '修改本人密码', '录入、编辑和删除本人成果', '查看本人画像、图谱、推荐与问答结果'],
    restricted_actions: ['不能访问管理员入口', '不能管理教师账户', '不能查看其他教师数据', '不能使用学院级统计和教师对比能力'],
    future_extension_hint: '后续如扩展更多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中分散判断。',
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
  contact_visibility: raw?.contact_visibility ?? 'email_only',
  contact_visibility_label: raw?.contact_visibility_label ?? '仅公开邮箱',
  public_contact_channels: Array.isArray(raw?.public_contact_channels) ? raw.public_contact_channels : [],
  avatar_url: raw?.avatar_url ?? '',
  research_direction: Array.isArray(raw?.research_direction) ? raw.research_direction : [],
  bio: raw?.bio ?? '',
  discipline: raw?.discipline ?? '',
  research_interests: raw?.research_interests ?? '',
  is_active: raw?.is_active ?? true,
  is_admin: Boolean(raw?.is_admin),
  role_code: raw?.role_code === 'college_admin' ? 'college_admin' : raw?.role_code === 'admin' ? 'admin' : 'teacher',
  role_label: raw?.role_label ?? (raw?.role_code === 'college_admin' ? '学院管理员' : raw?.is_admin ? '系统管理员' : '教师账户'),
  permission_scope: raw?.permission_scope ?? buildDefaultPermissionScope(raw),
  password_reset_required: Boolean(raw?.password_reset_required),
  password_updated_at: raw?.password_updated_at ?? null,
  security_notice:
    raw?.security_notice ??
    (raw?.password_reset_required
      ? '当前密码为管理员初始化或重置后的临时密码，请登录后尽快修改。'
      : '请妥善保管工号与密码，建议使用高强度密码并定期更新。'),
  account_status_label: raw?.account_status_label ?? (raw?.is_active === false ? '账户停用' : '账户可用'),
  password_status_label: raw?.password_status_label ?? (raw?.password_reset_required ? '待修改密码' : '状态正常'),
  next_action_hint:
    raw?.next_action_hint ??
    (raw?.is_active === false
      ? '当前账户已停用，需由管理员恢复启用后才能继续登录和修改密码。'
      : raw?.password_reset_required
        ? '当前密码为初始化或重置后的临时密码，请登录后尽快前往个人中心修改密码。'
        : '当前账户状态正常，可继续维护资料、成果和密码。'),
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
