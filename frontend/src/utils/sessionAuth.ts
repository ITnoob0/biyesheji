import axios from 'axios'
import type { Router } from 'vue-router'
import type { TeacherAccountResponse } from '../types/users'

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_ID_KEY = 'user_id'
const IS_ADMIN_KEY = 'is_admin'
const USER_PROFILE_KEY = 'user_profile'
const AUTH_REDIRECT_KEY = 'auth_redirect_target'
const AUTH_FAILURE_REASON_KEY = 'auth_failure_reason'
export const SESSION_AUTH_CHANGED_EVENT = 'session-auth-changed'

export type SessionUser = Pick<
  TeacherAccountResponse,
  | 'id'
  | 'username'
  | 'real_name'
  | 'department'
  | 'title'
  | 'research_direction'
  | 'bio'
  | 'discipline'
  | 'research_interests'
  | 'h_index'
  | 'is_active'
  | 'is_admin'
>

type SessionUserPayload = Omit<Partial<TeacherAccountResponse>, 'id'> & {
  id?: number | string
}

const normalizeSessionUser = (raw: SessionUserPayload | null | undefined): SessionUser => ({
  id: Number(raw?.id ?? 0),
  username: raw?.username ?? '',
  real_name: raw?.real_name ?? '',
  department: raw?.department ?? '',
  title: raw?.title ?? '',
  research_direction: Array.isArray(raw?.research_direction) ? raw.research_direction : [],
  bio: raw?.bio ?? '',
  discipline: raw?.discipline ?? '',
  research_interests: raw?.research_interests ?? '',
  h_index: Number(raw?.h_index ?? 0),
  is_active: raw?.is_active ?? true,
  is_admin: Boolean(raw?.is_admin),
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

export const resetSessionFlowState = (): void => {
  sessionStorage.removeItem(AUTH_REDIRECT_KEY)
  sessionStorage.removeItem(AUTH_FAILURE_REASON_KEY)
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
