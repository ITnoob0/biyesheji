import type { LocationQuery, LocationQueryRaw, RouteLocationRaw } from 'vue-router'
import type { SessionUser } from './sessionAuth'

export type CrossModulePage =
  | 'portrait'
  | 'recommendations'
  | 'achievement-entry'
  | 'assistant'
  | 'academy-dashboard'

export type CrossModuleSource =
  | 'achievement'
  | 'portrait'
  | 'recommendation'
  | 'assistant'
  | 'academy-dashboard'
  | 'graph'

export type CrossModuleSection =
  | 'portrait-dimensions'
  | 'portrait-achievements'
  | 'portrait-explanation'
  | 'portrait-graph'
  | 'recommendation-evidence'
  | 'achievement-records'
  | 'assistant-answer'
  | 'academy-ranking'
  | 'academy-drilldown'

export type AchievementRecordType =
  | 'paper'
  | 'project'
  | 'intellectual_property'
  | 'teaching_achievement'
  | 'academic_service'

export interface CrossModuleLinkQuery {
  source?: CrossModuleSource
  page?: CrossModulePage
  section?: CrossModuleSection
  highlight?: string
  dimension_key?: string
  guide_id?: string
  record_type?: string
  record_id?: string
  question_type?: string
  user_id?: string
  department?: string
  year?: string
  note?: string
}

export interface CrossModuleLinkState {
  source?: CrossModuleSource
  page?: CrossModulePage
  section?: CrossModuleSection
  highlight?: string
  dimensionKey?: string
  guideId?: number
  recordType?: string
  recordId?: number
  questionType?: string
  department?: string
  year?: number
  note?: string
}

export interface AssistantEvidenceLink {
  page: CrossModulePage
  label: string
  section?: CrossModuleSection
  highlight?: string
  dimension_key?: string
  guide_id?: number
  record_type?: string
  record_id?: number
  department?: string
  year?: number | null
  note?: string
}

const asString = (value: unknown): string => {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : ''
  }
  return typeof value === 'string' ? value : ''
}

export const buildCrossModuleQuery = (payload: CrossModuleLinkQuery): LocationQueryRaw => {
  const query: LocationQueryRaw = {}

  Object.entries(payload).forEach(([key, rawValue]) => {
    if (rawValue === undefined || rawValue === null || rawValue === '') {
      return
    }
    query[key] = String(rawValue)
  })

  return query
}

export const parseCrossModuleLink = (query: LocationQuery): CrossModuleLinkState | null => {
  const source = asString(query.source) as CrossModuleSource
  const page = asString(query.page) as CrossModulePage
  const section = asString(query.section) as CrossModuleSection
  const highlight = asString(query.highlight)
  const dimensionKey = asString(query.dimension_key)
  const guideId = Number(asString(query.guide_id))
  const recordType = asString(query.record_type)
  const recordId = Number(asString(query.record_id))
  const questionType = asString(query.question_type)
  const department = asString(query.department)
  const year = Number(asString(query.year))
  const note = asString(query.note)

  if (!source && !page && !section && !highlight && !dimensionKey && !recordType && !recordId && !guideId) {
    return null
  }

  return {
    source: source || undefined,
    page: page || undefined,
    section: section || undefined,
    highlight: highlight || undefined,
    dimensionKey: dimensionKey || undefined,
    guideId: Number.isFinite(guideId) && guideId > 0 ? guideId : undefined,
    recordType: recordType || undefined,
    recordId: Number.isFinite(recordId) && recordId > 0 ? recordId : undefined,
    questionType: questionType || undefined,
    department: department || undefined,
    year: Number.isFinite(year) && year > 0 ? year : undefined,
    note: note || undefined,
  }
}

export const buildScopedTeacherQuery = (
  currentUser: SessionUser | null | undefined,
  targetTeacherId: number | null | undefined,
  extraQuery: LocationQueryRaw = {},
): LocationQueryRaw => {
  if (currentUser?.is_admin && targetTeacherId) {
    return {
      user_id: String(targetTeacherId),
      ...extraQuery,
    }
  }

  return extraQuery
}

export const resolvePortraitRoute = (
  currentUser: SessionUser | null | undefined,
  targetTeacherId: number | null | undefined,
  extraQuery: LocationQueryRaw = {},
): RouteLocationRaw => {
  if (currentUser?.is_admin && targetTeacherId) {
    return {
      name: 'profile',
      params: { id: String(targetTeacherId) },
      query: extraQuery,
    }
  }

  return {
    name: 'dashboard',
    query: extraQuery,
  }
}

export const resolveAssistantEvidenceRoute = (
  link: AssistantEvidenceLink,
  currentUser: SessionUser | null | undefined,
  targetTeacherId: number | null | undefined,
): RouteLocationRaw => {
  const query = buildScopedTeacherQuery(
    currentUser,
    targetTeacherId,
    buildCrossModuleQuery({
      source: 'assistant',
      page: link.page,
      section: link.section,
      highlight: link.highlight,
      dimension_key: link.dimension_key,
      guide_id: link.guide_id ? String(link.guide_id) : undefined,
      record_type: link.record_type,
      record_id: link.record_id ? String(link.record_id) : undefined,
      question_type: link.page === 'assistant' ? 'guide_reason' : undefined,
      department: link.department,
      year: link.year ? String(link.year) : undefined,
      note: link.note,
    }),
  )

  if (link.page === 'portrait') {
    return resolvePortraitRoute(currentUser, targetTeacherId, query)
  }

  if (link.page === 'recommendations') {
    return { name: 'project-recommendations', query }
  }

  if (link.page === 'achievement-entry') {
    return { name: 'AchievementEntry', query }
  }

  if (link.page === 'academy-dashboard') {
    return { name: 'academy-dashboard', query }
  }

  return { name: 'dashboard', query }
}

export const focusEvidenceSection = (sectionId?: string, highlightId?: string): void => {
  if (typeof window === 'undefined') {
    return
  }

  window.setTimeout(() => {
    const primaryTarget = highlightId ? document.getElementById(highlightId) : null
    const fallbackTarget = sectionId ? document.getElementById(sectionId) : null
    const target = primaryTarget || fallbackTarget

    if (!target) {
      return
    }

    target.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }, 120)
}

export const mapAchievementTypeToPortraitDimension = (type?: string): string => {
  if (type === 'project') {
    return 'funding_support'
  }
  if (type === 'intellectual_property') {
    return 'ip_strength'
  }
  if (type === 'teaching_achievement') {
    return 'talent_training'
  }
  if (type === 'academic_service') {
    return 'academic_reputation'
  }
  return 'academic_output'
}

export const mapAchievementTypeToEntryTab = (type?: string): string => {
  if (type === 'project') {
    return 'projects'
  }
  if (type === 'intellectual_property') {
    return 'intellectual-properties'
  }
  if (type === 'teaching_achievement') {
    return 'teaching-achievements'
  }
  if (type === 'academic_service') {
    return 'academic-services'
  }
  return 'papers'
}
