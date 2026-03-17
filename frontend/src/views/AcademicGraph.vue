<template>
  <div class="graph-shell">
    <div class="graph-board">
      <div class="graph-toolbar">
        <el-button size="small" @click="loadGraph">刷新图谱</el-button>
      </div>

      <div class="chart-area">
        <div v-loading="loading" ref="chartRef" class="graph-canvas"></div>

        <div v-if="!loading && hasError" class="state-layer">
          <el-result icon="warning" title="图谱加载失败" sub-title="未能读取当前教师图谱数据，但不会影响画像页其他模块。">
            <template #extra>
              <el-button type="primary" @click="loadGraph">重试</el-button>
            </template>
          </el-result>
        </div>

        <div v-else-if="!loading && isEmpty" class="state-layer">
          <el-empty description="当前教师暂无可展示的学术图谱数据，可先录入论文、项目、知识产权、教学成果或学术服务。" />
        </div>
      </div>

      <div v-if="!loading && !hasError && !isEmpty" class="graph-footer">
        <div class="footer-section">
          <p class="footer-title">隐藏/显示节点</p>
          <div class="filter-row">
            <el-button
              v-for="item in filterItems"
              :key="item.type"
              class="filter-button"
              size="small"
              :type="isTypeVisible(item.type) ? 'primary' : 'default'"
              :plain="!isTypeVisible(item.type)"
              @click="toggleNodeType(item.type)"
            >
              {{ item.shortLabel }}
            </el-button>
          </div>
        </div>

        <div class="footer-section">
          <p class="footer-title">图谱图例</p>
          <ul class="legend-list legend-grid">
            <li v-for="item in legendItems" :key="item.type">
              <span class="dot" :style="{ background: item.color }"></span>
              <span>{{ item.label }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <aside class="graph-side">
      <div class="side-section">
        <p class="side-title">关系速览</p>
        <div class="mini-grid">
          <div class="mini-card">
            <span class="mini-label">论文</span>
            <strong>{{ summary.paperCount }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">项目</span>
            <strong>{{ summary.projectCount }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">知识产权</span>
            <strong>{{ summary.ipCount }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">教学成果</span>
            <strong>{{ summary.teachingCount }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">学术服务</span>
            <strong>{{ summary.serviceCount }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">边关系</span>
            <strong>{{ summary.linkCount }}</strong>
          </div>
        </div>
      </div>

      <div class="side-section">
        <p class="side-title">当前焦点</p>
        <div v-if="selectedNode" class="focus-card">
          <strong>{{ selectedNode.name }}</strong>
          <span class="focus-type">{{ selectedNode.nodeTypeLabel || nodeTypeLabel(selectedNode.nodeType) }}</span>
          <p v-for="line in selectedNode.detailLines || []" :key="line" class="focus-desc">{{ line }}</p>
        </div>
        <div v-else-if="selectedLink" class="focus-card">
          <strong>{{ selectedLink.relationLabel || selectedLink.name }}</strong>
          <span class="focus-type">边关系</span>
          <p class="focus-desc">{{ selectedLink.description || '当前关系用于描述图谱中的实体连接。' }}</p>
          <p class="focus-desc">连接：{{ selectedLink.source }} → {{ selectedLink.target }}</p>
        </div>
        <div v-else class="focus-card muted-block">点击节点可查看成果详情，点击边可查看关系说明。</div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { ensureSessionUserContext } from '../utils/sessionAuth'

type GraphNodeType =
  | 'CenterTeacher'
  | 'Paper'
  | 'Keyword'
  | 'ExternalScholar'
  | 'Project'
  | 'IntellectualProperty'
  | 'TeachingAchievement'
  | 'AcademicService'
  | string

type GraphNode = {
  id: string
  name: string
  category: number
  symbolSize: number
  nodeType: GraphNodeType
  nodeTypeLabel?: string
  detailLines?: string[]
}

type GraphLink = {
  source: string
  target: string
  name: string
  relationLabel?: string
  description?: string
}

const props = defineProps<{ userId: number | string }>()

const chartRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const isEmpty = ref(false)
const hasError = ref(false)
const router = useRouter()

const graphNodes = ref<GraphNode[]>([])
const graphLinks = ref<GraphLink[]>([])
const selectedNode = ref<GraphNode | null>(null)
const selectedLink = ref<GraphLink | null>(null)
const hiddenNodeTypes = ref<GraphNodeType[]>([])

let chartInstance: echarts.ECharts | null = null

const nodeMeta: Record<string, { label: string; shortLabel: string; color: string; category: number }> = {
  CenterTeacher: { label: '中心教师：画像主体', shortLabel: '教师', color: '#2563eb', category: 0 },
  Paper: { label: '论文：学术产出', shortLabel: '论文', color: '#14b8a6', category: 1 },
  ExternalScholar: { label: '合作学者：合作网络', shortLabel: '合作', color: '#ef4444', category: 2 },
  Keyword: { label: '关键词：研究主题', shortLabel: '关键词', color: '#f59e0b', category: 3 },
  Project: { label: '项目：科研攻关', shortLabel: '项目', color: '#8b5cf6', category: 4 },
  IntellectualProperty: { label: '知识产权：成果转化', shortLabel: '知产', color: '#f97316', category: 5 },
  TeachingAchievement: { label: '教学成果：育人成效', shortLabel: '教学', color: '#06b6d4', category: 6 },
  AcademicService: { label: '学术服务：共同体贡献', shortLabel: '服务', color: '#84cc16', category: 7 },
}

const legendItems = Object.entries(nodeMeta).map(([type, meta]) => ({
  type,
  label: meta.label,
  shortLabel: meta.shortLabel,
  color: meta.color,
}))

const filterItems = legendItems.filter(item => item.type !== 'CenterTeacher')

const isTypeVisible = (type: GraphNodeType) => !hiddenNodeTypes.value.includes(type)

const visibleNodes = computed(() =>
  graphNodes.value.filter(node => node.nodeType === 'CenterTeacher' || isTypeVisible(node.nodeType)),
)

const visibleLinks = computed(() => {
  const visibleIds = new Set(visibleNodes.value.map(node => node.id))
  return graphLinks.value.filter(link => visibleIds.has(link.source) && visibleIds.has(link.target))
})

const summary = computed(() => ({
  paperCount: graphNodes.value.filter(node => node.nodeType === 'Paper').length,
  projectCount: graphNodes.value.filter(node => node.nodeType === 'Project').length,
  ipCount: graphNodes.value.filter(node => node.nodeType === 'IntellectualProperty').length,
  teachingCount: graphNodes.value.filter(node => node.nodeType === 'TeachingAchievement').length,
  serviceCount: graphNodes.value.filter(node => node.nodeType === 'AcademicService').length,
  scholarCount: graphNodes.value.filter(node => node.nodeType === 'ExternalScholar').length,
  keywordCount: graphNodes.value.filter(node => node.nodeType === 'Keyword').length,
  linkCount: graphLinks.value.length,
}))

const nodeTypeLabel = (type: string) => nodeMeta[type]?.label.split('：')[0] || type

const toggleNodeType = (type: GraphNodeType) => {
  hiddenNodeTypes.value = isTypeVisible(type)
    ? hiddenNodeTypes.value.concat(type)
    : hiddenNodeTypes.value.filter(item => item !== type)
}

const fetchGraphData = async (userId: number | string) => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return { nodes: [], links: [], meta: {} }
  }

  const response = await axios.get(`/api/graph/topology/${userId}/`)
  return response.data
}

const bindChartEvents = () => {
  if (!chartInstance) return

  chartInstance.off('click')
  chartInstance.on('click', params => {
    if (params.dataType === 'node') {
      selectedNode.value = params.data as GraphNode
      selectedLink.value = null
      return
    }

    if (params.dataType === 'edge') {
      selectedLink.value = params.data as GraphLink
      selectedNode.value = null
    }
  })
}

const renderGraph = async () => {
  await nextTick()
  if (!chartRef.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption({
    tooltip: {
      show: true,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const node = params.data as GraphNode
          const extra = (node.detailLines || []).slice(0, 2).join('<br/>')
          return `<b>${node.name}</b><br/>${node.nodeTypeLabel || nodeTypeLabel(node.nodeType)}${extra ? `<br/>${extra}` : ''}`
        }

        const link = params.data as GraphLink
        return `<b>${link.relationLabel || link.name}</b><br/>${link.description || '当前关系用于描述图谱中的实体连接。'}`
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: visibleNodes.value.map(node => {
          const meta = nodeMeta[node.nodeType] || { color: '#94a3b8', category: 8 }
          return {
            ...node,
            category: meta.category,
            symbolSize: node.nodeType === 'CenterTeacher' ? 58 : node.symbolSize,
            itemStyle: {
              color: meta.color,
              borderColor: '#ffffff',
              borderWidth: node.nodeType === 'CenterTeacher' ? 3 : 1,
              shadowBlur: node.nodeType === 'CenterTeacher' ? 24 : 10,
              shadowColor: node.nodeType === 'CenterTeacher' ? 'rgba(37,99,235,0.34)' : 'rgba(148,163,184,0.18)',
            },
            label: {
              show: true,
              color: '#334155',
            },
          }
        }),
        links: visibleLinks.value.map(link => ({
          ...link,
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.75)',
            width: 2,
            curveness: 0.12,
          },
          label: {
            show: true,
            formatter: link.relationLabel || link.name,
            fontSize: 11,
            color: '#64748b',
            backgroundColor: 'rgba(255,255,255,0.82)',
            padding: [2, 6],
            borderRadius: 8,
          },
        })),
        force: {
          repulsion: 560,
          edgeLength: [70, 160],
          gravity: 0.06,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 3,
            color: '#334155',
          },
        },
      },
    ],
  })

  bindChartEvents()
}

const loadGraph = async () => {
  if (!props.userId) return

  loading.value = true
  isEmpty.value = false
  hasError.value = false

  try {
    const data = await fetchGraphData(props.userId)
    graphNodes.value = data.nodes || []
    graphLinks.value = data.links || []
    hiddenNodeTypes.value = []

    if (!graphNodes.value.length) {
      isEmpty.value = true
      selectedNode.value = null
      selectedLink.value = null
      chartInstance?.clear()
    } else {
      selectedNode.value = graphNodes.value.find(node => node.nodeType === 'CenterTeacher') ?? graphNodes.value[0] ?? null
      selectedLink.value = null
      await renderGraph()
    }
  } catch (error) {
    console.error(error)
    hasError.value = true
    graphNodes.value = []
    graphLinks.value = []
    selectedNode.value = null
    selectedLink.value = null
    chartInstance?.clear()
    ElMessage.error('学术拓扑图加载失败，画像页其他区域仍可继续使用。')
  } finally {
    loading.value = false
  }
}

const handleResize = () => {
  chartInstance?.resize()
}

watch(
  () => props.userId,
  () => {
    void loadGraph()
  },
)

watch(hiddenNodeTypes, async () => {
  if (!graphNodes.value.length || isEmpty.value || hasError.value) return

  if (selectedNode.value && !visibleNodes.value.some(node => node.id === selectedNode.value?.id)) {
    selectedNode.value = visibleNodes.value.find(node => node.nodeType === 'CenterTeacher') ?? visibleNodes.value[0] ?? null
  }

  if (
    selectedLink.value &&
    !visibleLinks.value.some(
      link =>
        link.source === selectedLink.value?.source &&
        link.target === selectedLink.value?.target &&
        link.name === selectedLink.value?.name,
    )
  ) {
    selectedLink.value = null
  }

  await renderGraph()
})

onMounted(() => {
  void loadGraph()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.graph-shell {
  display: grid;
  grid-template-columns: 1.15fr 0.65fr;
  gap: 18px;
  min-height: 620px;
}

.graph-board {
  position: relative;
  min-height: 620px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 22%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  padding: 14px;
}

.graph-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

.chart-area {
  position: relative;
}

.graph-canvas {
  width: 100%;
  height: 560px;
}

.state-layer {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
}

.graph-footer {
  display: grid;
  gap: 14px;
  margin-top: 14px;
}

.footer-section {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f8fafc;
}

.footer-title {
  margin: 0 0 12px;
  color: #0f172a;
  font-weight: 600;
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, max-content));
  gap: 10px 12px;
  align-items: start;
}

.filter-button {
  min-width: 96px;
  margin: 0;
}

.graph-side {
  display: grid;
  gap: 14px;
}

.side-section {
  padding: 18px;
  border-radius: 20px;
  background: #f8fafc;
}

.side-title {
  margin: 0 0 12px;
  color: #0f172a;
  font-weight: 600;
}

.mini-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.mini-card {
  padding: 14px 12px;
  border-radius: 16px;
  background: #fff;
}

.mini-label {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
}

.mini-card strong {
  color: #0f172a;
  font-size: 18px;
}

.focus-card {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #fff;
}

.focus-type {
  display: inline-flex;
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  font-size: 12px;
}

.focus-desc,
.muted-block {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.legend-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.legend-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.legend-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #334155;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

@media (max-width: 1180px) {
  .graph-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .graph-board {
    padding: 12px;
  }

  .graph-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .legend-grid,
  .mini-grid {
    grid-template-columns: 1fr;
  }
}
</style>
