<template>
  <div v-if="radarData && radarData.length > 0" class="radar-shell">
    <div ref="radarRef" class="radar-canvas"></div>
    <div class="radar-caption">
      <span class="caption-title">{{ teacherName || '当前教师' }}画像维度</span>
      <span class="caption-subtitle">六个维度共同描绘科研能力结构，不同区域越饱满代表画像越完整。</span>
    </div>
  </div>
  <div v-else class="empty-placeholder">
    <el-empty description="暂无科研画像雷达数据" :image-size="100" />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  radarData: { name: string; value: number }[]
  teacherName?: string
}>()

const radarRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const renderRadar = async () => {
  if (!props.radarData || props.radarData.length === 0) {
    chart?.clear()
    return
  }

  await nextTick()
  if (!radarRef.value) return

  if (!chart) {
    chart = echarts.init(radarRef.value)
  }

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const values = props.radarData
          .map((item, index) => `${item.name}: ${params.value[index]}`)
          .join('<br/>')
        return `<b>${props.teacherName || '当前教师'}</b><br/>${values}`
      },
    },
    radar: {
      indicator: props.radarData.map(item => ({ name: item.name, max: 100 })),
      radius: '62%',
      center: ['50%', '50%'],
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#334155',
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
        data: [
          {
            value: props.radarData.map(item => item.value),
            name: props.teacherName || '当前教师',
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: {
              width: 3,
              color: '#2563eb',
            },
            itemStyle: {
              color: '#2563eb',
            },
            areaStyle: {
              color: 'rgba(37, 99, 235, 0.24)',
            },
          },
        ],
      },
    ],
  })
}

const handleResize = () => {
  chart?.resize()
}

watch(
  () => props.radarData,
  () => {
    void renderRadar()
  },
  { deep: true },
)

onMounted(() => {
  void renderRadar()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
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
}

.radar-caption {
  display: grid;
  gap: 6px;
  padding: 0 4px;
}

.caption-title {
  color: #0f172a;
  font-weight: 600;
}

.caption-subtitle {
  color: #64748b;
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
</style>
