import axios from 'axios'
import type { Router } from 'vue-router'

const TOKEN_KEY = 'token'
const USER_ID_KEY = 'user_id'
const IS_ADMIN_KEY = 'is_admin'
const USER_PROFILE_KEY = 'user_profile'
export const SESSION_AUTH_CHANGED_EVENT = 'session-auth-changed'

export interface SessionUser {
  id: number
  username: string
  real_name?: string | null
  department?: string | null
  title?: string | null
  research_direction?: string[]
  bio?: string | null
  discipline?: string | null
  research_interests?: string | null
  h_index?: number
  is_active?: boolean
  is_admin: boolean
}

const normalizeSessionUser = (raw: any): SessionUser => ({
  id: Number(raw?.id ?? 0),
  username: raw?.username ?? '',
  real_name: raw?.real_name ?? raw?.name ?? '',
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

export const clearSessionAuth = (): void => {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_ID_KEY)
  sessionStorage.removeItem(IS_ADMIN_KEY)
  sessionStorage.removeItem(USER_PROFILE_KEY)
  emitSessionAuthChanged()
}

export const logoutSession = async (router?: Router): Promise<void> => {
  clearSessionAuth()

  if (router) {
    await router.replace({ name: 'login' })
  }
}

export const setSessionToken = (token: string): void => {
  sessionStorage.setItem(TOKEN_KEY, token)
  emitSessionAuthChanged()
}

export const setSessionUser = (rawUser: any): SessionUser => {
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
  const response = await axios.get('/api/users/me/')
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
