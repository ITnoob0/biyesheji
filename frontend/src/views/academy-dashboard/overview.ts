import type { EChartsOption } from 'echarts'
import type { DepartmentDistributionRecord, ScopeComparisonTrendRecord, YearlyTrendRecord } from '../../types/academy'

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

export const buildAcademyTrendOption = (records: YearlyTrendRecord[], echarts: any): EChartsOption => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['总成果', '论文', '项目'], top: 0 },
  grid: { left: 36, right: 24, bottom: 24, top: 48, containLabel: true },
  xAxis: {
    type: 'category',
    data: records.map(item => `${item.year}`),
    axisLine: { lineStyle: { color: '#94a3b8' } },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
  },
  series: [
    {
      name: '总成果',
      type: 'bar',
      barWidth: 28,
      data: records.map(item => item.achievement_total),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#0f766e' },
          { offset: 1, color: '#34d399' },
        ]),
        borderRadius: [8, 8, 0, 0],
      },
    },
    {
      name: '论文',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: records.map(item => item.paper_count),
      lineStyle: { color: '#2563eb', width: 3 },
      itemStyle: { color: '#2563eb' },
    },
    {
      name: '项目',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: records.map(item => item.project_count),
      lineStyle: { color: '#f59e0b', width: 3 },
      itemStyle: { color: '#f59e0b' },
    },
  ],
})

export const buildDepartmentDistributionOption = (
  records: DepartmentDistributionRecord[],
): EChartsOption => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 0, top: 'center' },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['36%', '50%'],
      avoidLabelOverlap: true,
      label: {
        formatter: '{b}\n{c} 人',
      },
      data: records,
    },
  ],
})

export const buildScopeComparisonOption = (records: ScopeComparisonTrendRecord[], echarts: any): EChartsOption => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当前范围总成果', '全校总成果'], top: 0 },
  grid: { left: 36, right: 24, bottom: 24, top: 48, containLabel: true },
  xAxis: {
    type: 'category',
    data: records.map(item => `${item.year}`),
    axisLine: { lineStyle: { color: '#94a3b8' } },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
  },
  series: [
    {
      name: '当前范围总成果',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: records.map(item => item.scope_achievement_total),
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
      name: '全校总成果',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: records.map(item => item.baseline_achievement_total),
      lineStyle: { color: '#2563eb', width: 3, type: 'dashed' },
      itemStyle: { color: '#2563eb' },
    },
  ],
})
