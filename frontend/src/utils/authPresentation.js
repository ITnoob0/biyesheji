const DEFAULT_PERMISSION_MESSAGE = '当前身份没有权限执行此操作。'
const DEFAULT_LOGIN_FAILURE_MESSAGE = '登录失败，请检查工号/账号和密码。'
const HTML_DEBUG_PAYLOAD_PATTERN = /<\/?[a-z][\s\S]*>|<!DOCTYPE|Traceback/i

const extractSafeText = detail => {
  if (typeof detail !== 'string') {
    return ''
  }

  const normalized = detail.trim()
  if (!normalized) {
    return ''
  }

  if (HTML_DEBUG_PAYLOAD_PATTERN.test(normalized)) {
    return ''
  }

  return normalized
}

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

export const resolveApiErrorMessage = (errorLike, fallbackMessage = '操作失败，请稍后重试。') => {
  const detail = errorLike?.response?.data

  const safeText = extractSafeText(detail)
  if (safeText) {
    return safeText
  }

  if (detail?.detail) {
    const safeDetail = extractSafeText(String(detail.detail))
    if (safeDetail) {
      return safeDetail
    }
  }

  if (detail && typeof detail === 'object') {
    const firstValue = Object.values(detail)[0]
    if (Array.isArray(firstValue) && firstValue.length) {
      const safeArrayValue = extractSafeText(String(firstValue[0]))
      if (safeArrayValue) {
        return safeArrayValue
      }
    }
    const safeFirstValue = extractSafeText(firstValue)
    if (safeFirstValue) {
      return safeFirstValue
    }
  }

  return fallbackMessage
}

export const resolveLoginFailureMessage = errorLike => {
  const detail = resolveApiErrorMessage(errorLike, DEFAULT_LOGIN_FAILURE_MESSAGE)
  return detail || DEFAULT_LOGIN_FAILURE_MESSAGE
}
