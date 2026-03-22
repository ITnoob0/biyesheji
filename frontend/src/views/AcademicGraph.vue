<template>
  <div class="graph-shell">
    <div class="graph-board">
      <div class="graph-toolbar">
        <el-button size="small" @click="loadGraph">刷新图谱</el-button>
      </div>

      <el-alert
        v-if="!loading && graphMeta?.fallback_used"
        type="warning"
        show-icon
        :closable="false"
        class="fallback-alert"
      >
        <template #title>{{ sourceSummary.title }} · {{ sourceSummary.badge }}</template>
        <template #default>
          <p>{{ sourceSummary.notice }}</p>
          <p>{{ sourceSummary.fallbackTip }}</p>
        </template>
      </el-alert>

      <el-alert
        v-if="!loading && errorNotice"
        type="error"
        show-icon
        :closable="false"
        class="fallback-alert"
        :title="errorNotice.message"
      >
        <template #default>
          <p>{{ errorNotice.guidance }}</p>
          <p v-if="errorNotice.requestHint">{{ errorNotice.requestHint }}</p>
        </template>
      </el-alert>

      <div class="chart-area">
        <div v-loading="loading" ref="chartRef" class="graph-canvas"></div>

        <div v-if="!loading && hasError" class="state-layer">
          <el-result
            icon="warning"
            title="图谱加载失败"
            :sub-title="errorNotice?.guidance || '未能读取当前教师图谱数据，但不会影响画像页其他模块。'"
          >
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
        <p class="side-title">数据来源</p>
        <div class="focus-card">
          <strong>{{ sourceSummary.title }}</strong>
          <span class="focus-type">{{ sourceSummary.source }}</span>
          <p class="focus-desc">{{ sourceSummary.notice }}</p>
          <p class="focus-desc">{{ sourceSummary.calculationNote }}</p>
          <p class="focus-desc">{{ sourceSummary.fallbackTip }}</p>
          <p class="focus-desc">节点 {{ graphMeta?.node_count ?? 0 }} 个 · 关系 {{ graphMeta?.link_count ?? 0 }} 条</p>
        </div>
      </div>

      <div class="side-section">
        <p class="side-title">图分析亮点</p>
        <div class="meta-grid">
          <div v-for="item in graphAnalysis?.highlight_cards || []" :key="item.title" class="mini-card">
            <span class="mini-label">{{ item.title }}</span>
            <strong>{{ item.value }}</strong>
            <p class="focus-desc">{{ item.detail }}</p>
          </div>
        </div>
        <p class="focus-desc analysis-note">{{ graphAnalysis?.scope_note || '当前为轻量图分析展示。' }}</p>
        <p class="focus-desc">{{ graphAnalysis?.analysis_method_note || '当前图分析基于现有关系数据与轻量统计口径生成。' }}</p>
      </div>

      <div class="side-section">
        <p class="side-title">合作与主题热点</p>
        <div class="focus-card">
          <strong>合作最活跃学者</strong>
          <div class="tag-row">
            <el-tag v-for="item in graphAnalysis?.top_collaborators || []" :key="item.name" effect="plain" type="danger">
              {{ item.name }} · {{ item.count }}
            </el-tag>
            <span v-if="!(graphAnalysis?.top_collaborators || []).length" class="focus-desc">暂无合作热点数据。</span>
          </div>
        </div>
        <div class="focus-card">
          <strong>高频研究主题</strong>
          <div class="tag-row">
            <el-tag v-for="item in graphAnalysis?.top_keywords || []" :key="item.name" effect="plain" type="warning">
              {{ item.name }} · {{ item.count }}
            </el-tag>
            <span v-if="!(graphAnalysis?.top_keywords || []).length" class="focus-desc">暂无主题热点数据。</span>
          </div>
        </div>
      </div>

      <div class="side-section">
        <p class="side-title">合作网络概览</p>
        <div class="mini-grid">
          <div class="mini-card">
            <span class="mini-label">合作作者</span>
            <strong>{{ graphAnalysis?.collaboration_overview?.collaborator_total ?? 0 }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">合作边</span>
            <strong>{{ graphAnalysis?.collaboration_overview?.collaboration_links ?? 0 }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">篇均合作者</span>
            <strong>{{ graphAnalysis?.collaboration_overview?.average_collaborators_per_paper ?? 0 }}</strong>
          </div>
          <div class="mini-card">
            <span class="mini-label">最强合作</span>
            <strong>{{ graphAnalysis?.collaboration_overview?.strongest_collaborator?.name || '暂无' }}</strong>
          </div>
        </div>
      </div>

      <div class="side-section">
        <p class="side-title">合作者类型分析</p>
        <div class="focus-card">
          <strong>内外部合作分布</strong>
          <p class="focus-desc">
            校内 {{ graphAnalysis?.collaborator_type_breakdown?.internal_count ?? 0 }} 位
            · 校外 {{ graphAnalysis?.collaborator_type_breakdown?.external_count ?? 0 }} 位
          </p>
          <p class="focus-desc">
            校内占比 {{ graphAnalysis?.collaborator_type_breakdown?.internal_ratio ?? 0 }}%
            · 校外占比 {{ graphAnalysis?.collaborator_type_breakdown?.external_ratio ?? 0 }}%
          </p>
          <p class="focus-desc">{{ graphAnalysis?.collaborator_type_breakdown?.description || '当前暂无可用的合作者类型分析数据。' }}</p>
        </div>
      </div>

      <div class="side-section">
        <p class="side-title">研究主题热点分析</p>
        <div class="focus-card">
          <strong>{{ graphAnalysis?.theme_hotspots?.focus_label || '暂无' }}</strong>
          <p class="focus-desc">Top3 关键词集中度 {{ graphAnalysis?.theme_hotspots?.focus_ratio ?? 0 }}%</p>
          <p class="focus-desc">{{ graphAnalysis?.theme_hotspots?.description || '当前暂无可用的研究主题热点分析数据。' }}</p>
        </div>
        <div class="yearly-focus-list">
          <div
            v-for="item in graphAnalysis?.theme_hotspots?.yearly_focus || []"
            :key="item.year"
            class="focus-card yearly-focus-card"
          >
            <strong>{{ item.year }} 年</strong>
            <div class="tag-row">
              <el-tag v-for="keyword in item.keywords" :key="`${item.year}-${keyword.name}`" size="small" effect="plain" type="success">
                {{ keyword.name }} · {{ keyword.count }}
              </el-tag>
              <span v-if="!item.keywords.length" class="focus-desc">当年暂无可识别主题热点。</span>
            </div>
          </div>
        </div>
      </div>

      <div class="side-section">
        <p class="side-title">图谱侧栏说明</p>
        <div class="focus-card">
          <strong>当前计算口径</strong>
          <p class="focus-desc">合作网络概览基于教师论文与合作作者关系统计。</p>
          <p class="focus-desc">合作者类型按是否标记为内部教师账号进行区分。</p>
          <p class="focus-desc">研究主题热点基于论文关键词出现频次，不包含路径分析、合作圈层分析或主题聚类。</p>
        </div>
      </div>

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
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import { buildGraphSourceSummary } from './graph/sourceState.js'
import type { GraphLink, GraphNode, GraphNodeType, GraphTopologyAnalysis, GraphTopologyMeta, GraphTopologyResponse } from '../types/graph'
import { ensureSessionUserContext } from '../utils/sessionAuth'

const props = defineProps<{ userId: number | string }>()

const chartRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const isEmpty = ref(false)
const hasError = ref(false)
const router = useRouter()

const graphNodes = ref<GraphNode[]>([])
const graphLinks = ref<GraphLink[]>([])
const graphMeta = ref<GraphTopologyMeta | null>(null)
const graphAnalysis = ref<GraphTopologyAnalysis | null>(null)
const selectedNode = ref<GraphNode | null>(null)
const selectedLink = ref<GraphLink | null>(null)
const hiddenNodeTypes = ref<GraphNodeType[]>([])
const errorNotice = ref<{ message: string; guidance: string; requestHint: string } | null>(null)

let chartInstance: echarts.ECharts | null = null

const sourceSummary = computed(() => buildGraphSourceSummary(graphMeta.value))

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

const fetchGraphData = async (userId: number | string): Promise<GraphTopologyResponse> => {
  const sessionUser = await ensureSessionUserContext()
  if (!sessionUser) {
    router.replace({ name: 'login' })
    return { nodes: [], links: [], meta: {} }
  }

  const response = await axios.get<GraphTopologyResponse>(`/api/graph/topology/${userId}/`)
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
  errorNotice.value = null

  try {
    const data = await fetchGraphData(props.userId)
    graphNodes.value = data.nodes || []
    graphLinks.value = data.links || []
    graphMeta.value = data.meta || null
    graphAnalysis.value = data.analysis || null
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
    graphMeta.value = null
    graphAnalysis.value = null
    selectedNode.value = null
    selectedLink.value = null
    chartInstance?.clear()
    errorNotice.value = buildApiErrorNotice(error, {
      fallbackMessage: '学术拓扑图加载失败，画像页其他区域仍可继续使用。',
      fallbackGuidance: '你可以稍后重试；若 Neo4j 不可用，系统会继续保留 MySQL 回退链路。',
    })
    ElMessage.warning(errorNotice.value.message)
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

.fallback-alert {
  margin-bottom: 12px;
  border-radius: 16px;
}

.fallback-alert :deep(p) {
  margin: 0;
  line-height: 1.7;
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

.meta-grid,
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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

.analysis-note {
  margin-top: 10px;
}

.yearly-focus-list {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

.yearly-focus-card {
  gap: 10px;
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
