import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    icon?: string
    order?: number
    section?: string
    moduleKey?: string
    moduleRoot?: boolean
    hiddenInMenu?: boolean
    activeMenu?: string
    requiresAuth?: boolean
    requiresAdmin?: boolean
    guestOnly?: boolean
    menuRoles?: Array<'teacher' | 'admin' | 'college_admin'>
  }
}
