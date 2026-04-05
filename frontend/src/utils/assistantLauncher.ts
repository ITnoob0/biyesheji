export const OPEN_FLOATING_ASSISTANT_EVENT = 'workspace-open-floating-assistant'

export interface FloatingAssistantLaunchPayload {
  draft?: string
  contextHint?: string
  autoSend?: boolean
}

export const openFloatingAssistant = (payload: FloatingAssistantLaunchPayload = {}): void => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent<FloatingAssistantLaunchPayload>(OPEN_FLOATING_ASSISTANT_EVENT, { detail: payload }))
}
