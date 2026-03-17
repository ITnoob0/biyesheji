import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import AchievementEntryView from '../views/AchievementEntryView.vue'
import TeacherManagementView from '../views/TeacherManagementView.vue'
import TeacherProfileEditorView from '../views/TeacherProfileEditorView.vue'
import TeacherRegisterView from '../views/TeacherRegisterView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ProjectGuideManagementView from '../views/ProjectGuideManagementView.vue'
import ProjectRecommendationView from '../views/ProjectRecommendationView.vue'
import AcademyDashboardView from '../views/AcademyDashboardView.vue'
import { clearSessionAuth, ensureSessionUserContext } from '../utils/sessionAuth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: { name: 'dashboard' },
      meta: { requiresAuth: true },
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
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile/:id',
      name: 'profile',
      component: DashboardView,
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/entry',
      name: 'AchievementEntry',
      component: AchievementEntryView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile-editor',
      name: 'teacher-profile-editor',
      component: TeacherProfileEditorView,
      meta: { requiresAuth: true },
    },
    {
      path: '/teachers',
      name: 'teacher-management',
      component: TeacherManagementView,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/project-guides',
      name: 'project-guide-management',
      component: ProjectGuideManagementView,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/project-recommendations',
      name: 'project-recommendations',
      component: ProjectRecommendationView,
      meta: { requiresAuth: true },
    },
    {
      path: '/academy-dashboard',
      name: 'academy-dashboard',
      component: AcademyDashboardView,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
})

router.beforeEach(async to => {
  if (to.meta.guestOnly) {
    const sessionUser = await ensureSessionUserContext()

    if (sessionUser) {
      return { name: 'dashboard' }
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
    return {
      name: 'dashboard',
      replace: true,
    }
  }

  if (to.name === 'profile' && !sessionUser.is_admin) {
    const requestedUserId = Number(to.params.id)

    if (Number.isFinite(requestedUserId) && requestedUserId !== sessionUser.id) {
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
