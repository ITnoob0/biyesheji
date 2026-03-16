<template>
  <div class="academic-graph-container">
    <div v-loading="loading" ref="chartRef" style="width:100%;height:600px;"></div>
    <div v-if="!loading && isEmpty" class="empty-hint">
      <el-empty description="该教师暂无学术社交数据，请先录入论文" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext } from '../utils/sessionAuth'

const props = defineProps<{ userId: number | string }>()
const chartRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const isEmpty = ref(false)
const router = useRouter()

let chartInstance: echarts.ECharts | null = null

const nodeColors: Record<string, string> = {
  CenterTeacher: '#5470C6',
  Paper: '#91CC75',
  Keyword: '#FAC858',
  ExternalScholar: '#EE6666',
}

const fetchGraphData = async (userId: number | string) => {
  const sessionUser = await ensureSessionUserContext()

  if (!sessionUser) {
    router.replace({ name: 'login' })
    return { nodes: [], links: [] }
  }

  try {
    const response = await axios.get(`/api/graph/topology/${userId}/`)
    return response.data
  } catch (err) {
    ElMessage.error('获取拓扑图数据失败')
    return { nodes: [], links: [] }
  }
}

const renderGraph = (data: any) => {
  if (!chartRef.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const option = {
    tooltip: {
      show: true,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `<b>${params.data.name}</b><br/>类型: ${params.data.nodeType}`
        }
        return `关系: ${params.data.name}`
      },
    },
    legend: [
      {
        data: ['教师', '论文', '外部学者', '关键词'],
        orient: 'vertical',
        left: 'left',
      },
    ],
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: data.nodes.map((node: any) => ({
          ...node,
          itemStyle: { color: nodeColors[node.nodeType] || '#888' },
          label: { show: node.symbolSize > 20 },
        })),
        links: data.links,
        categories: [
          { name: '教师' },
          { name: '论文' },
          { name: '外部学者' },
          { name: '关键词' },
        ],
        roam: true,
        draggable: true,
        label: { position: 'right', show: true },
        force: {
          repulsion: 400,
          edgeLength: 150,
          gravity: 0.1,
        },
        lineStyle: { color: '#bbb', width: 1.5, curveness: 0.1 },
      },
    ],
  }

  chartInstance.setOption(option)
}

const loadGraph = async () => {
  if (!props.userId) return

  loading.value = true
  isEmpty.value = false

  const data = await fetchGraphData(props.userId)

  if (!data.nodes || data.nodes.length === 0) {
    isEmpty.value = true
    chartInstance?.clear()
  } else {
    await nextTick()
    renderGraph(data)
  }

  loading.value = false
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  void loadGraph()
  window.addEventListener('resize', handleResize)
})

watch(
  () => props.userId,
  () => {
    void loadGraph()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.academic-graph-container {
  position: relative;
  width: 100%;
  height: 600px;
  background: #fff;
  border-radius: 8px;
}

.empty-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
</style>
