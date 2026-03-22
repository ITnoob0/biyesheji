import { resolveApiErrorMessage } from './apiFeedback.js'

const DEFAULT_PERMISSION_MESSAGE = '当前身份没有权限执行此操作。'
const DEFAULT_LOGIN_FAILURE_MESSAGE = '登录失败，请检查工号/账号和密码。'
const DEFAULT_ADMIN_ROUTE_NOTICE = '当前账号为教师身份，不能访问管理员入口。'
const DEFAULT_ADMIN_PORTRAIT_NOTICE = '管理员登录后默认进入教师管理，请先选择教师后再查看画像。'

export const resolveRoleLabel = user => {
  if (user?.role_label && String(user.role_label).trim()) {
    return String(user.role_label).trim()
  }
  return user?.is_admin ? '系统管理员' : '教师账户'
}

export const buildPasswordSecurityNotice = user => {
  if (user?.security_notice && String(user.security_notice).trim()) {
    return String(user.security_notice).trim()
  }
  if (user?.is_active === false) {
    return '当前账户已停用，请联系管理员恢复后再继续使用。'
  }
  if (user?.password_reset_required) {
    return '当前密码为管理员初始化或重置后的临时密码，请登录后尽快修改。'
  }
  return '请妥善保管工号与密码，建议使用高强度密码并定期更新。'
}

export const formatPasswordUpdatedAt = value => {
  if (!value) return '尚未记录'
  const nextDate = new Date(value)
  if (Number.isNaN(nextDate.getTime())) {
    return '尚未记录'
  }
  return nextDate.toLocaleString('zh-CN', { hour12: false })
}

export const resolvePermissionDeniedMessage = detail => {
  const message = typeof detail === 'string' ? detail.trim() : ''
  return message || DEFAULT_PERMISSION_MESSAGE
}

export const buildAdminRouteNotice = (featureLabel = '管理员入口') => {
  const normalized = typeof featureLabel === 'string' ? featureLabel.trim() : ''
  if (!normalized || normalized === '管理员入口') {
    return DEFAULT_ADMIN_ROUTE_NOTICE
  }
  return `当前账号为教师身份，不能访问${normalized}。`
}

export const buildSelfOnlyNotice = (resourceLabel = '本人的画像与账户信息') => {
  const normalized = typeof resourceLabel === 'string' ? resourceLabel.trim() : ''
  return `教师账号只能查看${normalized || '本人的数据'}`
}

export const buildAdminPortraitSelectionNotice = () => DEFAULT_ADMIN_PORTRAIT_NOTICE

export { resolveApiErrorMessage }

export const resolveLoginFailureMessage = errorLike => {
  const detail = resolveApiErrorMessage(errorLike, DEFAULT_LOGIN_FAILURE_MESSAGE)
  return detail || DEFAULT_LOGIN_FAILURE_MESSAGE
}
