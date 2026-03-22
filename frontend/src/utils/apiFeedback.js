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

const extractFirstText = detail => {
  if (typeof detail === 'string') {
    return extractSafeText(detail)
  }

  if (Array.isArray(detail)) {
    for (const item of detail) {
      const message = extractFirstText(item)
      if (message) {
        return message
      }
    }
    return ''
  }

  if (detail && typeof detail === 'object') {
    if (detail.error?.message) {
      const errorMessage = extractFirstText(detail.error.message)
      if (errorMessage) {
        return errorMessage
      }
    }

    if (detail.detail) {
      const detailMessage = extractFirstText(detail.detail)
      if (detailMessage) {
        return detailMessage
      }
    }

    if (detail.field_errors && typeof detail.field_errors === 'object') {
      const firstFieldError = Object.values(detail.field_errors)[0]
      const fieldMessage = extractFirstText(firstFieldError)
      if (fieldMessage) {
        return fieldMessage
      }
    }

    const firstValue = Object.values(detail)[0]
    return extractFirstText(firstValue)
  }

  return ''
}

export const resolveApiErrorMessage = (errorLike, fallbackMessage = '操作失败，请稍后重试。') => {
  const message = extractFirstText(errorLike?.response?.data)
  return message || fallbackMessage
}

export const resolveApiErrorNextStep = (errorLike, fallbackGuidance = '请稍后重试。') => {
  const nextStep = extractFirstText(errorLike?.response?.data?.error?.next_step)
  return nextStep || fallbackGuidance
}

export const resolveApiErrorRequestId = errorLike => {
  const requestId =
    extractSafeText(errorLike?.response?.data?.request_id) ||
    extractSafeText(errorLike?.response?.data?.error?.request_id) ||
    extractSafeText(errorLike?.response?.headers?.['x-request-id']) ||
    extractSafeText(errorLike?.response?.headers?.['X-Request-ID'])

  return requestId || ''
}

export const buildApiErrorNotice = (
  errorLike,
  {
    fallbackMessage = '操作失败，请稍后重试。',
    fallbackGuidance = '请稍后重试；若持续失败，请联系管理员。',
  } = {},
) => {
  const message = resolveApiErrorMessage(errorLike, fallbackMessage)
  const guidance = resolveApiErrorNextStep(errorLike, fallbackGuidance)
  const requestId = resolveApiErrorRequestId(errorLike)

  return {
    message,
    guidance,
    requestId,
    requestHint: requestId ? `请求编号：${requestId}` : '',
  }
}
