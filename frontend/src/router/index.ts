import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'
import LoginView from '../views/LoginView.vue'
import TeacherRegisterView from '../views/TeacherRegisterView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import { buildAdminRouteNotice, buildSelfOnlyNotice, buildSystemAdminRouteNotice } from '../utils/authPresentation.js'
import { initializeHttpClient } from '../utils/http'
import { clearSessionAuth, ensureSessionUserContext, getSessionUser, setSessionNotice } from '../utils/sessionAuth'
import { resolveWorkspaceHomePath } from '../utils/workspaceNavigation.js'
import { workspaceChildrenRoutes } from './workspaceRoutes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: () => resolveWorkspaceHomePath(getSessionUser()),
      meta: { requiresAuth: true, hiddenInMenu: true },
      children: workspaceChildrenRoutes,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'teacher-register',
      component: TeacherRegisterView,
      meta: { guestOnly: true },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: ForgotPasswordView,
      meta: { guestOnly: true },
    },
  ],
})

initializeHttpClient(router)

router.beforeEach(async to => {
  if (to.meta.guestOnly) {
    const sessionUser = await ensureSessionUserContext()

    if (sessionUser) {
      return { path: resolveWorkspaceHomePath(sessionUser) }
    }

    clearSessionAuth()
    return true
  }

  const sessionUser = await ensureSessionUserContext()

  if (!sessionUser) {
    clearSessionAuth()
    return {
      name: 'login',
      query: to.fullPath ? { redirect: to.fullPath } : undefined,
      replace: true,
    }
  }

  if (to.meta.requiresAdmin && !sessionUser.is_admin) {
    const adminFeatureLabel =
      to.name === 'teacher-management'
        ? '教师管理入口'
        : to.name === 'project-guide-management'
          ? '项目指南管理入口'
          : to.name === 'academy-dashboard'
            ? '学院级统计看板'
            : '管理员入口'
    setSessionNotice(buildAdminRouteNotice(adminFeatureLabel))
    return {
      name: 'dashboard',
      replace: true,
    }
  }

  if (to.meta.requiresSystemAdmin && sessionUser.role_code !== 'system_admin' && sessionUser.role_code !== 'admin') {
    const systemAdminFeatureLabel =
      to.name === 'teacher-management-accounts'
        ? '添加教师入口'
        : to.name === 'teacher-management-college-admins'
          ? '创建学院管理员入口'
          : to.name === 'project-guide-management'
            ? '项目指南管理入口'
            : to.name === 'academy-dashboard'
              ? '学院级统计看板'
              : '系统管理员入口'
    setSessionNotice(buildSystemAdminRouteNotice(systemAdminFeatureLabel))
    return {
      path: resolveWorkspaceHomePath(sessionUser),
      replace: true,
    }
  }

  if (to.name === 'profile' && !sessionUser.is_admin) {
    const requestedUserId = Number(to.params.id)

    if (Number.isFinite(requestedUserId) && requestedUserId !== sessionUser.id) {
      setSessionNotice(`${buildSelfOnlyNotice('本人的画像与账户信息')}，已自动切回当前账号。`)
      return {
        name: 'profile',
        params: { id: sessionUser.id },
        replace: true,
      }
    }
  }

  return true
})

export default router
