import type { EChartsOption } from 'echarts'
import type { DepartmentDistributionRecord, ScopeComparisonTrendRecord, YearlyTrendRecord } from '../../types/academy'
import { buildBaseChartOption, getChartThemeTokens } from '../../utils/chartTheme'

export type {
  AcademyActiveFilters,
  AcademyDataMeta,
  AcademyFilterOptions,
  AcademyOverviewResponse,
  AcademyStatisticItem,
  CollaborationOverview,
  DepartmentDistributionRecord,
  ScopeComparisonTrendRecord,
  TopActiveTeacherRecord,
  YearlyTrendRecord,
} from '../../types/academy'

export const buildAcademyTrendOption = (records: YearlyTrendRecord[], echarts: any): EChartsOption => {
  const tokens = getChartThemeTokens()
  const hasScoreSeries = records.some(item => typeof item.total_score === 'number')
  const baseOption = buildBaseChartOption()
  const recordMap = new Map(records.map(item => [String(item.year), item]))

  return {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        const points = Array.isArray(params) ? params : [params]
        const year = String(points[0]?.axisValue ?? '')
        const record = recordMap.get(year)
        const rows = points
          .map((item: any) => {
            const value = Number(item.value ?? 0)
            const suffix = item.seriesName.includes('积分') ? ' 分' : item.seriesName.includes('教师') ? ' 人' : ' 项'
            return `${item.marker}${item.seriesName}: ${value}${suffix}`
          })
          .join('<br/>')
        const detail = record
          ? `<br/><span style="color:${tokens.textTertiary}">学术产出 ${record.paper_count} 项 / 科研项目 ${record.project_count} 项 / 奖励转化 ${record.ip_count} 项 / 平台科普 ${record.service_count} 项</span>`
          : ''
        return `<strong>${year} 年</strong><br/>${rows}${detail}`
      },
    },
    legend: {
      data: hasScoreSeries ? ['核心科研积分', '唯一成果数', '活跃教师'] : ['总成果', '论文', '项目'],
      top: 0,
      itemGap: 18,
      textStyle: { color: tokens.textSecondary },
    },
    grid: { left: 42, right: 58, bottom: 36, top: 70, containLabel: true },
    xAxis: {
      type: 'category',
      data: records.map(item => `${item.year}`),
      axisLine: { lineStyle: { color: tokens.borderStrong } },
      axisLabel: { color: tokens.textTertiary },
    },
    yAxis: [
      {
        type: 'value',
        name: hasScoreSeries ? '积分' : '成果',
        minInterval: 1,
        axisLabel: { color: tokens.textTertiary },
        nameTextStyle: { color: tokens.textTertiary },
        splitLine: { lineStyle: { color: tokens.border } },
      },
      {
        type: 'value',
        name: '数量',
        minInterval: 1,
        axisLabel: { color: tokens.textTertiary },
        nameTextStyle: { color: tokens.textTertiary },
        splitLine: { show: false },
      },
    ],
    dataZoom: records.length > 6
      ? [
          { type: 'inside', start: 0, end: 100 },
          { type: 'slider', height: 18, bottom: 4, borderColor: tokens.border, textStyle: { color: tokens.textTertiary } },
        ]
      : [],
    series: [
      {
        name: hasScoreSeries ? '核心科研积分' : '总成果',
        type: 'bar',
        barMaxWidth: 34,
        data: records.map(item => (hasScoreSeries ? item.total_score ?? 0 : item.achievement_total)),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#14b8a6' },
            { offset: 1, color: '#0f766e' },
          ]),
          borderRadius: [8, 8, 0, 0],
        },
        emphasis: { focus: 'series' },
      },
      {
        name: hasScoreSeries ? '唯一成果数' : '论文',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 8,
        data: records.map(item => (hasScoreSeries ? item.achievement_total : item.paper_count)),
        lineStyle: { color: '#2563eb', width: 3 },
        itemStyle: { color: '#2563eb' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.22)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
          ]),
        },
        emphasis: { focus: 'series' },
      },
      {
        name: hasScoreSeries ? '活跃教师' : '项目',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 8,
        data: records.map(item => (hasScoreSeries ? item.active_teacher_count ?? 0 : item.project_count)),
        lineStyle: { color: '#f59e0b', width: 3, type: 'dashed' },
        itemStyle: { color: '#f59e0b' },
        emphasis: { focus: 'series' },
      },
    ],
  }
}

export const buildDepartmentDistributionOption = (
  records: DepartmentDistributionRecord[],
): EChartsOption => {
  const tokens = getChartThemeTokens()

  return {
    ...buildBaseChartOption(),
    tooltip: { ...buildBaseChartOption().tooltip, trigger: 'item' },
    legend: { orient: 'vertical', right: 0, top: 'center', textStyle: { color: tokens.textSecondary } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['36%', '50%'],
        avoidLabelOverlap: true,
        label: {
          formatter: '{b}\n{c}',
          color: tokens.textSecondary,
        },
        data: records,
      },
    ],
  }
}

export const buildScopeComparisonOption = (records: ScopeComparisonTrendRecord[], echarts: any): EChartsOption => {
  const tokens = getChartThemeTokens()
  const hasScoreSeries = records.some(item => typeof item.scope_total_score === 'number' || typeof item.baseline_total_score === 'number')

  return {
    ...buildBaseChartOption(),
    tooltip: { ...buildBaseChartOption().tooltip, trigger: 'axis' },
    legend: {
      data: hasScoreSeries ? ['当前范围积分', '对比范围积分'] : ['当前范围总成果', '全校总成果'],
      top: 0,
      textStyle: { color: tokens.textSecondary },
    },
    grid: { left: 36, right: 24, bottom: 24, top: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: records.map(item => `${item.year}`),
      axisLine: { lineStyle: { color: tokens.borderStrong } },
      axisLabel: { color: tokens.textTertiary },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: tokens.textTertiary },
      splitLine: { lineStyle: { color: tokens.border } },
    },
    series: [
      {
        name: hasScoreSeries ? '当前范围积分' : '当前范围总成果',
        type: 'line',
        smooth: true,
        symbolSize: 8,
        data: records.map(item => (hasScoreSeries ? item.scope_total_score ?? 0 : item.scope_achievement_total)),
        lineStyle: { color: '#0f766e', width: 3 },
        itemStyle: { color: '#0f766e' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(15, 118, 110, 0.28)' },
            { offset: 1, color: 'rgba(15, 118, 110, 0.04)' },
          ]),
        },
      },
      {
        name: hasScoreSeries ? '对比范围积分' : '全校总成果',
        type: 'line',
        smooth: true,
        symbolSize: 8,
        data: records.map(item => (hasScoreSeries ? item.baseline_total_score ?? 0 : item.baseline_achievement_total)),
        lineStyle: { color: '#2563eb', width: 3, type: 'dashed' },
        itemStyle: { color: '#2563eb' },
      },
    ],
  }
}
