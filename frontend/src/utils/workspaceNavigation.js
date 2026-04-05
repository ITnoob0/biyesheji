const ADMIN_WORKSPACE_HOME_PATH = '/teachers'
const COLLEGE_ADMIN_WORKSPACE_HOME_PATH = '/teachers'
const TEACHER_WORKSPACE_HOME_PATH = '/profile-editor'

export const resolveWorkspaceHomePath = user =>
  user?.role_code === 'college_admin'
    ? COLLEGE_ADMIN_WORKSPACE_HOME_PATH
    : user?.is_admin
      ? ADMIN_WORKSPACE_HOME_PATH
      : TEACHER_WORKSPACE_HOME_PATH

export const resolvePostLoginLandingPath = (resolvedTarget, user) => {
  const normalizedTarget = typeof resolvedTarget === 'string' ? resolvedTarget.trim() : ''
  return normalizedTarget || resolveWorkspaceHomePath(user)
}

export const shouldRedirectAdminPortraitRoute = () => false
