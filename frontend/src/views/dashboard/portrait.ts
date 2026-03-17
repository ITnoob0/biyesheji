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

export type DashboardStatsResponse = {
  statistics?: StatisticItem[]
  radar_data?: Array<{ name: string; value: number }>
  achievement_overview?: AchievementOverview
  recent_achievements?: RecentAchievementRecord[]
  data_meta?: PortraitDataMeta
}

export type RadarResponse = {
  radar_dimensions?: Array<{ name: string; value: number }>
  dimension_sources?: DimensionSource[]
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
