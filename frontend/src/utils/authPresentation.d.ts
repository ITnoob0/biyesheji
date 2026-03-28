export function resolveRoleLabel(user: { is_admin?: boolean; role_label?: string | null } | null | undefined): string

export function buildPasswordSecurityNotice(
  user:
    | {
        is_active?: boolean
        password_reset_required?: boolean
        security_notice?: string | null
      }
    | null
    | undefined,
): string

export function buildAccountLifecycleHint(
  user:
    | {
        is_active?: boolean
        password_reset_required?: boolean
        next_action_hint?: string | null
      }
    | null
    | undefined,
): string

export function resolveContactVisibilityLabel(value: string | null | undefined): string

export function buildPublicContactSummary(
  user:
    | {
        contact_visibility?: string | null
        public_contact_channels?: Array<{ label?: string | null; value?: string | null }>
      }
    | null
    | undefined,
): string

export function formatPasswordUpdatedAt(value: string | null | undefined): string

export function buildAdminRouteNotice(featureLabel?: string): string

export function buildAdminPortraitSelectionNotice(): string

export function buildSessionRecoveryNotice(reason?: string, hasRedirectTarget?: boolean): string

export function buildSelfOnlyNotice(resourceLabel?: string): string

export function resolvePermissionDeniedMessage(detail: string | null | undefined): string

export function resolveApiErrorMessage(errorLike: any, fallbackMessage?: string): string

export function resolveLoginFailureMessage(errorLike: any): string
