import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import type { Router } from 'vue-router'
import { resolveApiErrorMessage } from './apiFeedback.js'
import {
  clearSessionAuth,
  getSessionRefreshToken,
  getSessionToken,
  setAuthRedirectTarget,
  setSessionExpiredReason,
  setSessionRefreshToken,
  setSessionToken,
} from './sessionAuth'

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
  _skipAuthHandling?: boolean
}

const AUTH_FREE_PATHS = [
  '/api/token/',
  '/api/token/refresh/',
  '/api/users/register/',
  '/api/users/forgot-password/',
  '/api/users/forgot-password/code/',
  '/api/users/forgot-password/reset/',
]

let httpInitialized = false
let appRouter: Router | null = null
let refreshPromise: Promise<string | null> | null = null

const isAuthFreeRequest = (url?: string): boolean => AUTH_FREE_PATHS.some(path => (url || '').includes(path))

const resolveCurrentLocation = (): string => {
  if (typeof window === 'undefined') {
    return '/dashboard'
  }

  const target = `${window.location.pathname}${window.location.search}${window.location.hash}`.trim()
  return target && target !== '/login' ? target : '/dashboard'
}

const redirectToLogin = async (): Promise<void> => {
  const redirect = resolveCurrentLocation()
  setAuthRedirectTarget(redirect)

  if (appRouter) {
    await appRouter.replace({
      name: 'login',
      query: redirect && redirect !== '/dashboard' ? { redirect } : undefined,
    })
    return
  }

  if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
    const query = redirect && redirect !== '/dashboard' ? `?redirect=${encodeURIComponent(redirect)}` : ''
    window.location.replace(`/login${query}`)
  }
}

const invalidateSession = async (reason = '登录状态已失效，请重新登录后继续操作。'): Promise<void> => {
  clearSessionAuth()
  setSessionExpiredReason(reason)
  await redirectToLogin()
}

const refreshSessionToken = async (): Promise<string | null> => {
  const refreshToken = getSessionRefreshToken()
  if (!refreshToken) {
    return null
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post<{ access: string; refresh?: string }>(
        '/api/token/refresh/',
        { refresh: refreshToken },
        {
          _skipAuthHandling: true,
        } as AxiosRequestConfig,
      )
      .then(response => {
        const nextAccessToken = response.data.access
        setSessionToken(nextAccessToken)
        if (response.data.refresh) {
          setSessionRefreshToken(response.data.refresh)
        }
        return nextAccessToken
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

const applyAuthorizationHeader = (config: RetriableRequestConfig): RetriableRequestConfig => {
  if (isAuthFreeRequest(config.url)) {
    return config
  }

  const token = getSessionToken()
  if (!token) {
    return config
  }

  config.headers = config.headers || {}
  if (!config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
}

export const initializeHttpClient = (router?: Router): void => {
  if (router) {
    appRouter = router
  }

  if (httpInitialized) {
    return
  }

  httpInitialized = true

  axios.interceptors.request.use((config: InternalAxiosRequestConfig) => applyAuthorizationHeader(config as RetriableRequestConfig))

  axios.interceptors.response.use(
    response => response,
    async (error: AxiosError) => {
      const requestConfig = (error.config || {}) as RetriableRequestConfig
      const status = error.response?.status

      if (requestConfig._skipAuthHandling || status !== 401 || isAuthFreeRequest(requestConfig.url)) {
        return Promise.reject(error)
      }

      if (!requestConfig._retry) {
        requestConfig._retry = true
        const nextAccessToken = await refreshSessionToken()

        if (nextAccessToken) {
          requestConfig.headers = requestConfig.headers || {}
          requestConfig.headers.Authorization = `Bearer ${nextAccessToken}`
          return axios(requestConfig)
        }
      }

      await invalidateSession(resolveApiErrorMessage(error, '登录状态已失效，请重新登录后继续操作。'))
      return Promise.reject(error)
    },
  )
}
