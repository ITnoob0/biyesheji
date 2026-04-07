<template>
  <div v-if="indicators.length > 0" class="radar-shell">
    <div ref="radarRef" class="radar-canvas"></div>
    <div class="radar-caption">
      <span class="caption-title">{{ teacherName || '当前教师' }}画像维度</span>
      <span class="caption-subtitle">多维雷达图支持同侪基准叠加，快速识别当前教师与基准的优势差值。</span>
    </div>
  </div>
  <div v-else class="empty-placeholder">
    <el-empty description="暂无科研画像雷达数据" :image-size="100" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { observeElementsResize } from '../utils/resizeObserver'

type RadarDimension = { name: string; value: number }
type RadarSeries = {
  name: string
  value: number[]
  series_role?: 'teacher' | 'benchmark' | string
}

const props = defineProps<{
  radarData: RadarDimension[]
  seriesData?: RadarSeries[]
  teacherName?: string
}>()

const radarRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const indicators = computed(() => props.radarData || [])

const resolvedSeriesData = computed<RadarSeries[]>(() => {
  if (props.seriesData && props.seriesData.length > 0) {
    return props.seriesData
  }
  return [
    {
      name: props.teacherName || '当前教师',
      value: indicators.value.map(item => Number(item.value || 0)),
      series_role: 'teacher',
    },
  ]
})

const handleResize = () => {
  chart?.resize()
}

const ensureResizeObserver = () => {
  if (resizeObserver || !radarRef.value) {
    return
  }
  resizeObserver = observeElementsResize([radarRef.value], handleResize)
}

const renderRadar = async () => {
  if (indicators.value.length === 0) {
    chart?.clear()
    return
  }

  await nextTick()
  if (!radarRef.value) return

  if (!chart) {
    chart = echarts.init(radarRef.value)
  }
  ensureResizeObserver()

  const normalizedSeries = resolvedSeriesData.value.map(item => {
    const normalized = indicators.value.map((_, index) => Number(item.value?.[index] || 0))
    return {
      ...item,
      value: normalized,
    }
  })
  const teacherSeries =
    normalizedSeries.find(item => item.series_role === 'teacher') || normalizedSeries[0] || null
  const benchmarkSeries =
    normalizedSeries.find(item => item.series_role === 'benchmark') || normalizedSeries[1] || null

  chart.setOption({
    tooltip: {
      trigger: 'item',
      confine: true,
      className: 'portrait-radar-tooltip',
      formatter: () => {
        if (!teacherSeries) {
          return '<b>暂无数据</b>'
        }

        const benchmarkLabel = benchmarkSeries?.name || '本院平均'
        const lines = indicators.value.map((item, index) => {
          const teacherValue = Number(teacherSeries.value[index] || 0)
          const benchmarkValue = Number(benchmarkSeries?.value?.[index] || 0)
          const delta = teacherValue - benchmarkValue
          const trendLabel = delta >= 0 ? '领先' : '落后'
          const deltaLabel = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`
          return [
            `${item.name}：${teacherValue.toFixed(1)}分`,
            `${benchmarkLabel}：${benchmarkValue.toFixed(1)}分`,
            `对比差值：${deltaLabel}分（${trendLabel}）`,
          ].join('<br/>')
        })

        return `<b>${teacherSeries.name}</b><br/>${lines.join('<br/><br/>')}`
      },
    },
    radar: {
      indicator: indicators.value.map(item => ({ name: item.name, max: 100 })),
      radius: '62%',
      center: ['50%', '50%'],
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#5b6880',
        fontSize: 13,
        fontWeight: 600,
      },
      splitArea: {
        areaStyle: {
          color: ['#f8fafc', '#f1f5f9', '#e2e8f0', '#dbeafe', '#dbeafe'],
        },
      },
      splitLine: {
        lineStyle: { color: 'rgba(148, 163, 184, 0.38)' },
      },
      axisLine: {
        lineStyle: { color: 'rgba(148, 163, 184, 0.45)' },
      },
    },
    series: [
      {
        type: 'radar',
        data: normalizedSeries.map(item => {
          const isBenchmark = item.series_role === 'benchmark'
          return {
            value: item.value,
            name: item.name,
            symbol: isBenchmark ? 'none' : 'circle',
            symbolSize: isBenchmark ? 0 : 6,
            lineStyle: {
              width: isBenchmark ? 2 : 3,
              type: isBenchmark ? 'dashed' : 'solid',
              color: isBenchmark ? '#8b95a7' : '#2563eb',
            },
            itemStyle: {
              color: isBenchmark ? '#8b95a7' : '#2563eb',
            },
            areaStyle: {
              color: isBenchmark ? 'rgba(128, 128, 128, 0.2)' : 'rgba(37, 99, 235, 0.24)',
            },
          }
        }),
      },
    ],
  })
}

watch(
  () => [props.radarData, props.seriesData],
  () => {
    void renderRadar()
  },
  { deep: true },
)

onMounted(() => {
  void renderRadar()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.radar-shell {
  display: grid;
  gap: 12px;
}

.radar-canvas {
  width: 100%;
  height: 380px;
  view-transition-name: portrait-radar-canvas;
}

.radar-caption {
  display: grid;
  gap: 6px;
  padding: 0 4px;
}

.caption-title {
  color: var(--text-primary);
  font-weight: 600;
}

.caption-subtitle {
  color: var(--text-tertiary);
  line-height: 1.6;
}

.empty-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
  background: #fdfdfd;
  border-radius: 8px;
}

:global(::view-transition-old(portrait-radar-canvas)),
:global(::view-transition-new(portrait-radar-canvas)) {
  animation-duration: 280ms;
  animation-timing-function: ease;
}
</style>
