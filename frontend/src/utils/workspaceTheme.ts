export type WorkspaceTheme = 'light' | 'dark'

export const WORKSPACE_THEME_CHANGED_EVENT = 'workspace-theme-changed'

const STORAGE_KEY = 'workspace-theme'
const THEME_ATTRIBUTE = 'data-workspace-theme'
const THEME_TRANSITION_CLASS = 'workspace-theme-transitioning'
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

let lastToggleOrigin: { x: number; y: number } | null = null

const isWorkspaceTheme = (value: string | null | undefined): value is WorkspaceTheme =>
  value === 'light' || value === 'dark'

const getDocumentRoot = () => document.documentElement

const persistTheme = (theme: WorkspaceTheme) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Ignore storage failures and continue with the in-memory theme state.
  }
}

const emitThemeChanged = (theme: WorkspaceTheme) => {
  window.dispatchEvent(new CustomEvent(WORKSPACE_THEME_CHANGED_EVENT, { detail: theme }))
}

const scheduleThemeChanged = (theme: WorkspaceTheme) => {
  window.setTimeout(() => {
    emitThemeChanged(theme)
  }, 0)
}

const setThemeAttribute = (theme: WorkspaceTheme) => {
  getDocumentRoot().setAttribute(THEME_ATTRIBUTE, theme)
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia(REDUCED_MOTION_QUERY).matches

const getThemeOrigin = (origin?: { x: number; y: number } | null) => {
  const fallback = {
    x: typeof window !== 'undefined' ? window.innerWidth - 88 : 0,
    y: 40,
  }
  return origin || lastToggleOrigin || fallback
}

const getRevealRadius = (origin: { x: number; y: number }) => {
  const points = [
    { x: 0, y: 0 },
    { x: window.innerWidth, y: 0 },
    { x: 0, y: window.innerHeight },
    { x: window.innerWidth, y: window.innerHeight },
  ]

  return Math.max(
    ...points.map((point) => Math.hypot(point.x - origin.x, point.y - origin.y)),
  )
}

const applyThemeGeometry = (origin: { x: number; y: number }) => {
  const root = getDocumentRoot()
  root.style.setProperty('--theme-origin-x', `${origin.x}px`)
  root.style.setProperty('--theme-origin-y', `${origin.y}px`)
  root.style.setProperty('--theme-reveal-radius', `${getRevealRadius(origin)}px`)
}

export const getStoredWorkspaceTheme = (): WorkspaceTheme => {
  if (typeof window === 'undefined') {
    return 'light'
  }

  try {
    const storedTheme = window.localStorage.getItem(STORAGE_KEY)
    if (isWorkspaceTheme(storedTheme)) {
      return storedTheme
    }
  } catch {
    // Ignore storage read failures and fall back to the default theme.
  }

  return 'light'
}

export const setWorkspaceThemeToggleOrigin = (origin: { x: number; y: number } | null) => {
  lastToggleOrigin = origin
}

export const applyWorkspaceTheme = (theme: WorkspaceTheme): WorkspaceTheme => {
  if (typeof window === 'undefined') {
    return theme
  }

  setThemeAttribute(theme)
  persistTheme(theme)
  emitThemeChanged(theme)
  return theme
}

export const initializeWorkspaceTheme = () => {
  if (typeof window === 'undefined') {
    return
  }

  setThemeAttribute(getStoredWorkspaceTheme())
}

export const transitionWorkspaceTheme = async (
  theme: WorkspaceTheme,
  origin?: { x: number; y: number } | null,
): Promise<WorkspaceTheme> => {
  if (typeof window === 'undefined') {
    return theme
  }

  const currentTheme = getDocumentRoot().getAttribute(THEME_ATTRIBUTE)
  if (currentTheme === theme) {
    return theme
  }

  const root = getDocumentRoot()
  const targetOrigin = getThemeOrigin(origin)
  applyThemeGeometry(targetOrigin)

  if (prefersReducedMotion()) {
    return applyWorkspaceTheme(theme)
  }

  const themedDocument = document as Document & {
    startViewTransition?: (updateCallback: () => void | Promise<void>) => ViewTransition
  }
  root.classList.add(THEME_TRANSITION_CLASS)

  if (!themedDocument.startViewTransition) {
    applyWorkspaceTheme(theme)
    root.classList.remove(THEME_TRANSITION_CLASS)
    return theme
  }

  try {
    const transition = themedDocument.startViewTransition(() => {
      setThemeAttribute(theme)
      persistTheme(theme)
    })

    await transition.finished
    scheduleThemeChanged(theme)
    return theme
  } finally {
    root.classList.remove(THEME_TRANSITION_CLASS)
  }
}
