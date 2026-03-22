export interface ApiErrorNotice {
  message: string
  guidance: string
  requestId: string
  requestHint: string
}

export function resolveApiErrorMessage(errorLike: any, fallbackMessage?: string): string

export function resolveApiErrorNextStep(errorLike: any, fallbackGuidance?: string): string

export function resolveApiErrorRequestId(errorLike: any): string

export function buildApiErrorNotice(
  errorLike: any,
  options?: {
    fallbackMessage?: string
    fallbackGuidance?: string
  },
): ApiErrorNotice
