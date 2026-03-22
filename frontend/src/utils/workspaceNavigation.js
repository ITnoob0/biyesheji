const WORKSPACE_HOME_PATH = '/dashboard'

export const resolveWorkspaceHomePath = () => WORKSPACE_HOME_PATH

export const resolvePostLoginLandingPath = resolvedTarget => {
  const normalizedTarget = typeof resolvedTarget === 'string' ? resolvedTarget.trim() : ''
  return normalizedTarget || WORKSPACE_HOME_PATH
}

export const shouldRedirectAdminPortraitRoute = () => false
