import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue' // 1. 导入新创建的登录视图组件
import AchievementEntryView from '../views/AchievementEntryView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      // 2. 注册登录页面路由
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/profile/:id',
      name: 'profile',
      component: DashboardView,
      props: true
    },
    {
      path: '/entry',
      name: 'AchievementEntry',
      component: AchievementEntryView
    }
  ],
})

/**
 * 3. 添加全局路由守卫
 * 在每次路由跳转前检查 localStorage 中是否存在 token。
 * 如果没有 token 且访问的不是登录页，则强制跳转到登录页。
 */
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  // 访问根路径始终跳到登录页
  if (to.path === '/') {
    next({ name: 'login' })
    return
  }
  if (!token && to.name !== 'login') {
    next({ name: 'login' })
  } else if (token && to.name === 'login') {
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router