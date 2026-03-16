import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue' // 1. 导入新创建的登录视图组件

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
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/profile/:id',
      name: 'profile',
      component: DashboardView,
      props: true
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
  
  if (to.name !== 'login' && !token) {
    // 未登录且不是去登录页，重定向到登录页
    next({ name: 'login' })
  } else if (to.name === 'login' && token) {
    // 已登录还想去登录页，直接跳转到首页
    next({ name: 'dashboard' })
  } else {
    // 正常放行
    next()
  }
})

export default router