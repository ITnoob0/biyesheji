import type { RouteLocationNormalizedLoaded } from 'vue-router'
import type { SessionUser } from './sessionAuth'

export declare const resolveWorkspaceHomePath: (user?: SessionUser | null | undefined) => string
export declare const resolvePostLoginLandingPath: (resolvedTarget: string, user?: SessionUser | null | undefined) => string
export declare const shouldRedirectAdminPortraitRoute: (
  routeLike: Pick<RouteLocationNormalizedLoaded, 'name' | 'params'>,
  user: SessionUser | null | undefined,
) => boolean
