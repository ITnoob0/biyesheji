import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import AchievementEntryView from '../views/AchievementEntryView.vue'
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
  ],
})

router.beforeEach(async to => {
  if (to.name === 'login') {
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
