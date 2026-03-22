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

export function formatPasswordUpdatedAt(value: string | null | undefined): string

export function buildAdminRouteNotice(featureLabel?: string): string

export function buildAdminPortraitSelectionNotice(): string

export function buildSelfOnlyNotice(resourceLabel?: string): string

export function resolvePermissionDeniedMessage(detail: string | null | undefined): string

export function resolveApiErrorMessage(errorLike: any, fallbackMessage?: string): string

export function resolveLoginFailureMessage(errorLike: any): string
