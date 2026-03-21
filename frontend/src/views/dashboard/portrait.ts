import type { EChartsOption } from 'echarts'

export type StatisticItem = {
  title: string
  value: number
  suffix?: string
  icon: string
  iconClass: string
  trend?: number | null
  helper?: string
}

export type TeacherDetail = {
  id: number
  username: string
  name: string
  real_name: string
  department: string
  title: string
  discipline: string
  research_interests: string
  research_direction: string[]
  bio: string
  h_index: number
  hIndex: number
  is_admin: boolean
}

export type PaperRecord = {
  id: number
  title: string
  date_acquired: string
  paper_type_display: string
  journal_name: string
  citation_count: number
  keywords: string[]
  coauthor_details: Array<{ id: number; name: string }>
}

export type RecentAchievementRecord = {
  id: number
  type: string
  type_label: string
  title: string
  date_acquired: string
  detail: string
  highlight: string
}

export type AchievementOverview = {
  paper_count: number
  project_count: number
  intellectual_property_count: number
  teaching_achievement_count: number
  academic_service_count: number
  total_citations: number
  total_achievements: number
}

export type PortraitDataMeta = {
  updated_at?: string | null
  source_note?: string
  acceptance_scope?: string
}

export type DimensionSource = {
  name: string
  description: string
}

export type DimensionInsight = {
  key: string
  name: string
  value: number
  weight: number
  level: string
  formula_note: string
  source_description: string
  evidence: string[]
}

export type DimensionTrendPoint = {
  year: number
  academic_output: number
  funding_support: number
  ip_strength: number
  talent_training: number
  academic_reputation: number
  interdisciplinary: number
  total_score: number
}

export type RecentStructurePoint = {
  year: number
  papers: number
  projects: number
  intellectual_properties: number
  teaching_achievements: number
  academic_services: number
  total: number
}

export type PortraitExplanation = {
  overview: string
  formation_steps: string[]
  transparency_note: string
  trend_note: string
  snapshot_boundary_note: string
}

export type DashboardStatsResponse = {
  statistics?: StatisticItem[]
  radar_data?: Array<{ name: string; value: number }>
  dimension_insights?: DimensionInsight[]
  achievement_overview?: AchievementOverview
  recent_achievements?: RecentAchievementRecord[]
  dimension_trend?: DimensionTrendPoint[]
  recent_structure?: RecentStructurePoint[]
  portrait_explanation?: PortraitExplanation
  data_meta?: PortraitDataMeta
}

export type RadarResponse = {
  radar_dimensions?: Array<{ name: string; value: number }>
  dimension_sources?: DimensionSource[]
  dimension_insights?: DimensionInsight[]
  data_meta?: PortraitDataMeta
}

export const buildProfileHighlights = (teacherInfo: TeacherDetail): string[] => {
  const fromDirection = teacherInfo.research_direction || []
  const fromInterests = (teacherInfo.research_interests || '')
    .split(/[，、,]/)
    .map(item => item.trim())
    .filter(Boolean)

  return Array.from(new Set([...fromDirection, ...fromInterests])).slice(0, 8)
}

export const buildTopKeywords = (papers: PaperRecord[]): string[] => {
  const counts = new Map<string, number>()

  papers.forEach(paper => {
    paper.keywords.forEach(keyword => {
      counts.set(keyword, (counts.get(keyword) || 0) + 1)
    })
  })

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([keyword]) => keyword)
}

export const buildTopCollaborators = (papers: PaperRecord[]): string[] => {
  const counts = new Map<string, number>()

  papers.forEach(paper => {
    paper.coauthor_details.forEach(person => {
      counts.set(person.name, (counts.get(person.name) || 0) + 1)
    })
  })

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name]) => name)
}

export const buildPaperTypeSummary = (papers: PaperRecord[]): string => {
  const journalCount = papers.filter(paper => paper.paper_type_display.includes('期刊')).length
  const conferenceCount = papers.filter(paper => paper.paper_type_display.includes('会议')).length
  return `期刊 ${journalCount} / 会议 ${conferenceCount}`
}

export const buildLatestActiveYear = (papers: PaperRecord[]): string => {
  const years = papers.map(paper => Number(paper.date_acquired.slice(0, 4))).filter(Boolean)
  return years.length ? `${Math.max(...years)} 年` : '暂无数据'
}

export const buildPortraitUpdatedLabel = (dataMeta: PortraitDataMeta | null): string => {
  if (!dataMeta?.updated_at) {
    return '尚无成果入库记录'
  }

  return new Date(dataMeta.updated_at).toLocaleString('zh-CN', {
    hour12: false,
  })
}

export const buildRecentAchievementEmptyText = (records: RecentAchievementRecord[]): string =>
  records.length ? '' : '暂无成果记录，可先前往成果录入页补充数据。'

const DIMENSION_SERIES = [
  { key: 'academic_output', label: '学术产出', color: '#2563eb' },
  { key: 'funding_support', label: '项目攻关', color: '#0f766e' },
  { key: 'ip_strength', label: '知识产权', color: '#f59e0b' },
  { key: 'talent_training', label: '人才培养', color: '#8b5cf6' },
  { key: 'academic_reputation', label: '学术活跃', color: '#ef4444' },
  { key: 'interdisciplinary', label: '跨学科', color: '#14b8a6' },
] as const

export const buildDimensionTrendOption = (trend: DimensionTrendPoint[], echarts: any): EChartsOption => {
  const years = trend.map(item => item.year)

  return {
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      data: DIMENSION_SERIES.map(item => item.label),
    },
    grid: { left: 28, right: 24, bottom: 24, top: 54, containLabel: true },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: {
      type: 'value',
      max: 100,
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.24)' } },
    },
    series: DIMENSION_SERIES.map(item => ({
      name: item.label,
      type: 'line',
      smooth: true,
      data: trend.map(point => point[item.key]),
      symbolSize: 7,
      lineStyle: { color: item.color, width: 3 },
      itemStyle: { color: item.color },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: `${item.color}33` },
          { offset: 1, color: `${item.color}08` },
        ]),
      },
    })),
  }
}

export const buildAchievementStructureOption = (records: RecentStructurePoint[], echarts: any): EChartsOption => {
  const years = records.map(item => item.year)
  const seriesConfig = [
    { key: 'papers', label: '论文', color: '#2563eb' },
    { key: 'projects', label: '项目', color: '#10b981' },
    { key: 'intellectual_properties', label: '知识产权', color: '#f59e0b' },
    { key: 'teaching_achievements', label: '教学成果', color: '#8b5cf6' },
    { key: 'academic_services', label: '学术服务', color: '#ef4444' },
  ] as const

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 28, right: 24, bottom: 24, top: 54, containLabel: true },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.24)' } },
    },
    series: seriesConfig.map(item => ({
      name: item.label,
      type: 'bar',
      stack: 'total',
      emphasis: { focus: 'series' },
      data: records.map(record => record[item.key]),
      itemStyle: { color: item.color, borderRadius: [6, 6, 0, 0] },
    })),
  }
}

export const buildTrendOption = (papers: PaperRecord[], echarts: any): EChartsOption => {
  const yearMap = new Map<number, { publications: number; citations: number }>()

  papers.forEach(paper => {
    const year = Number(paper.date_acquired.slice(0, 4))
    if (!year) return

    const current = yearMap.get(year) || { publications: 0, citations: 0 }
    current.publications += 1
    current.citations += paper.citation_count || 0
    yearMap.set(year, current)
  })

  const years = [...yearMap.keys()].sort((a, b) => a - b)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['发文量', '引用次数'], top: 0 },
    grid: { left: 36, right: 36, bottom: 24, top: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: [
      {
        type: 'value',
        name: '发文量',
        minInterval: 1,
      },
      {
        type: 'value',
        name: '引用次数',
      },
    ],
    series: [
      {
        name: '发文量',
        type: 'bar',
        barWidth: 28,
        data: years.map(year => yearMap.get(year)?.publications || 0),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#2563eb' },
            { offset: 1, color: '#60a5fa' },
          ]),
          borderRadius: [8, 8, 0, 0],
        },
      },
      {
        name: '引用次数',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: years.map(year => yearMap.get(year)?.citations || 0),
        symbolSize: 8,
        lineStyle: { color: '#f59e0b', width: 3 },
        itemStyle: { color: '#f59e0b' },
        areaStyle: {
          color: 'rgba(245, 158, 11, 0.12)',
        },
      },
    ],
  }
}
