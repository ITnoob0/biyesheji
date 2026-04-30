import type { Component } from 'vue'
import {
  ChatDotRound,
  DataAnalysis,
  Document,
  Histogram,
  MagicStick,
  Odometer,
  Reading,
  Setting,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import type { RouteRecordRaw } from 'vue-router'
import type { SessionUser } from '../utils/sessionAuth'

export interface LayoutModuleChild {
  path: string
  title: string
  icon?: Component | null
  order: number
}

export interface LayoutModuleMenu {
  key: string
  title: string
  icon?: Component | null
  order: number
  homePath: string
  description: string
  children: LayoutModuleChild[]
}

const iconMap: Record<string, Component> = {
  Odometer,
  User,
  UserFilled,
  Document,
  Histogram,
  MagicStick,
  ChatDotRound,
  DataAnalysis,
  Reading,
  Setting,
}

const moduleDescriptions: Record<string, string> = {
  'personal-center': '教师侧统一入口，承接身份状态、公开资料、账户安全与快捷入口。',
  portrait: '以教师科研画像为分析主视图，按总览、维度、趋势和说明分层展开。',
  achievement: '以成果维护为主入口，承接成果列表、录入、导入和统计摘要。',
  graph: '承接学术关系图谱、合作网络、主题热点和图谱说明。',
  recommendation: '承接项目推荐结果、反馈闭环和推荐解释。',
  assistant: '承接模板化问答、常见问题和来源说明。',
  'teacher-management': '管理员统一维护教师账户、状态和批量操作。',
  'academy-dashboard': '管理员查看学院级统计、趋势对比和排行钻取。',
  'project-guide-management': '管理员维护项目指南、规则配置和生命周期。',
}

moduleDescriptions['evaluation-rules'] = '统一查看核心科研能力规则，并由系统管理员维护规则版本与条目。'

const normalizePath = (path: string): string => (path.startsWith('/') ? path : `/${path}`)

const joinPaths = (parentPath: string, childPath?: string): string => {
  const normalizedParent = normalizePath(parentPath)
  if (!childPath) {
    return normalizedParent
  }

  const normalizedChild = childPath.startsWith('/') ? childPath.slice(1) : childPath
  return `${normalizedParent}/${normalizedChild}`
}

const getCurrentRole = (user: SessionUser | null | undefined): 'teacher' | 'admin' | 'college_admin' =>
  user?.role_code === 'college_admin' ? 'college_admin' : user?.is_admin ? 'admin' : 'teacher'

const canDisplayRoute = (route: RouteRecordRaw, user: SessionUser | null | undefined): boolean => {
  const role = getCurrentRole(user)
  if (route.meta?.requiresAdmin && role === 'teacher') {
    return false
  }

  if (route.meta?.requiresSystemAdmin && role !== 'admin') {
    return false
  }

  const menuRoles = route.meta?.menuRoles
  if (menuRoles && !menuRoles.includes(role)) {
    return false
  }

  return !route.meta?.hiddenInMenu
}

export const resolveLayoutIcon = (iconName?: string): Component | null => {
  if (!iconName) {
    return null
  }
  return iconMap[iconName] || null
}

export const buildLayoutModules = (
  routes: RouteRecordRaw[],
  user: SessionUser | null | undefined,
): LayoutModuleMenu[] => {
  return routes
    .filter(route => route.meta?.moduleRoot)
    .filter(route => canDisplayRoute(route, user))
    .map(route => {
      const children = (route.children || [])
        .filter(child => canDisplayRoute(child, user))
        .map(child => ({
          path: joinPaths(route.path, child.path),
          title: String(child.meta?.title || child.name || child.path || route.path),
          icon: resolveLayoutIcon(child.meta?.icon),
          order: Number(child.meta?.order || 999),
        }))
        .sort((left, right) => left.order - right.order || left.title.localeCompare(right.title))

      const moduleKey = String(route.meta?.moduleKey || route.path)

      return {
        key: moduleKey,
        title: String(route.meta?.title || route.name || route.path),
        icon: resolveLayoutIcon(route.meta?.icon),
        order: Number(route.meta?.order || 999),
        homePath: children[0]?.path || normalizePath(route.path),
        description: moduleDescriptions[moduleKey] || '当前模块已切换到分层工作台视图。',
        children,
      }
    })
    .sort((left, right) => left.order - right.order)
}

export const flattenLayoutModules = (modules: LayoutModuleMenu[]): LayoutModuleChild[] =>
  modules.flatMap(module => module.children)

export const findCurrentModule = (
  modules: LayoutModuleMenu[],
  moduleKey: string | undefined,
  currentPath: string,
): LayoutModuleMenu | null => {
  if (moduleKey) {
    const matchedModule = modules.find(item => item.key === moduleKey)
    if (matchedModule) {
      return matchedModule
    }
  }

  return (
    modules.find(module =>
      module.children.some(item => currentPath === item.path || currentPath.startsWith(`${item.path}/`)),
    ) || null
  )
}
