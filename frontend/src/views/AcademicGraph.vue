<template>
  <div class="graph-shell">
    <section class="graph-top workspace-surface-card">
      <div class="graph-top__head">
        <div class="graph-top__title-block">
          <p class="graph-top__eyebrow">Academic Topology</p>
          <h2 class="graph-top__title">学术拓扑</h2>
          <p class="graph-top__summary">{{ graphHeadline }}</p>
        </div>
        <div class="graph-top__stats">
          <div class="graph-stat-pill">
            <span>节点</span>
            <strong>{{ graphMeta?.node_count ?? 0 }}</strong>
          </div>
          <div class="graph-stat-pill">
            <span>关系</span>
            <strong>{{ graphMeta?.link_count ?? 0 }}</strong>
          </div>
          <div class="graph-stat-pill">
            <span>当前模式</span>
            <strong>{{ focusPresetLabel }}</strong>
          </div>
        </div>
      </div>
      <div class="graph-top__subline">
        <span class="workspace-muted graph-top__notice">
          
        </span>
      </div>
    </section>

    <section class="graph-toolbar-panel workspace-surface-card">
      <div class="graph-toolbar">
        <el-input
          v-model="searchQuery"
          size="small"
          clearable
          class="toolbar-search"
          placeholder="搜索节点名称或摘要"
          @keyup.enter="focusSearchedNode"
        />
        <el-select v-model="focusPreset" size="small" class="toolbar-select">
          <el-option v-for="item in focusPresetOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button size="small" @click="focusSearchedNode">定位节点</el-button>
        <el-button size="small" @click="resetGraphFilters">重置筛选</el-button>
        <el-button size="small" @click="loadGraph">刷新图谱</el-button>
      </div>
      <div v-if="!loading && !hasError && !isEmpty" class="graph-toolbar graph-toolbar--filters">
        <span class="toolbar-label">节点筛选</span>
        <el-button
          v-for="item in filterItems"
          :key="item.type"
          size="small"
          :type="isTypeVisible(item.type as GraphNodeType) ? 'primary' : 'default'"
          :plain="!isTypeVisible(item.type as GraphNodeType)"
          @click="toggleNodeType(item.type as GraphNodeType)"
        >
          {{ item.shortLabel }}
        </el-button>
      </div>

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
    </section>

    <section class="graph-board">
      <div class="chart-area">
        <div v-loading="loading" ref="chartRef" class="graph-canvas"></div>
        <div v-if="!loading && hasError" class="state-layer">
          <el-result
            icon="warning"
            title="图谱加载失败"
            :sub-title="errorNotice?.guidance || '当前无法读取图谱数据，但不会影响画像页其他模块使用。'"
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
    </section>

    <section v-if="!loading && !hasError && !isEmpty" class="graph-bottom">
      <div class="footer-section">
        <p class="footer-title">图例</p>
        <ul class="legend-list">
          <li v-for="item in legendItems" :key="item.type">
            <span class="dot" :style="{ background: item.color }"></span>
            <span>{{ item.label }}</span>
          </li>
        </ul>
      </div>

      <div class="side-section">
        <p class="side-title">焦点解读 / 当前说明</p>
        <div v-if="selectedNode" class="focus-card">
          <strong>{{ selectedNode.name }}</strong>
          <span class="focus-type">{{ selectedNode.nodeTypeLabel || nodeTypeLabel(selectedNode.nodeType) }}</span>
          <p v-for="line in selectedNode.detailLines || []" :key="line" class="focus-desc">{{ line }}</p>
          <div v-if="selectedNodeCanOpenAchievement" class="tag-row">
            <el-button link type="primary" @click="openSelectedRecordEvidence">查看支撑成果</el-button>
          </div>
        </div>
        <div v-else-if="selectedLink" class="focus-card">
          <strong>{{ selectedLink.relationLabel || selectedLink.name }}</strong>
          <span class="focus-type">边关系</span>
          <p class="focus-desc">{{ selectedLink.description || '当前关系用于描述图谱中的实体连接。' }}</p>
          <p class="focus-desc">连接：{{ selectedLink.source }} → {{ selectedLink.target }}</p>
        </div>
        <div v-else class="focus-card muted-block">点击节点可查看详情，点击边可查看关系说明。</div>

        <div v-if="selectedPathAnalysis" class="focus-card">
          <strong>{{ selectedPathAnalysis.title }}</strong>
          <p class="focus-desc">{{ selectedPathAnalysis.summary }}</p>
          <div class="tag-row">
            <el-tag v-for="item in selectedPathAnalysis.nodeNames" :key="`path-node-${item}`" size="small" effect="plain" type="success">
              {{ item }}
            </el-tag>
          </div>
          <div class="tag-row">
            <el-tag
              v-for="item in selectedPathAnalysis.relationLabels"
              :key="`path-relation-${item}`"
              size="small"
              effect="plain"
              type="info"
            >
              {{ item }}
            </el-tag>
          </div>
        </div>
        <div v-else class="focus-card muted-block">当前路径说明仅在已选中关键词、合作者或成果节点时展示。</div>

        <div class="mini-grid mini-grid--summary">
          <div class="mini-card"><span class="mini-label">论文</span><strong>{{ summary.paperCount }}</strong></div>
          <div class="mini-card"><span class="mini-label">项目</span><strong>{{ summary.projectCount }}</strong></div>
          <div class="mini-card"><span class="mini-label">知识产权</span><strong>{{ summary.ipCount }}</strong></div>
          <div class="mini-card"><span class="mini-label">教学成果</span><strong>{{ summary.teachingCount }}</strong></div>
          <div class="mini-card"><span class="mini-label">学术服务</span><strong>{{ summary.serviceCount }}</strong></div>
          <div class="mini-card"><span class="mini-label">边关系</span><strong>{{ summary.linkCount }}</strong></div>
        </div>

        
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import { buildCrossModuleQuery } from '../utils/crossModuleLinking'
import type { GraphLink, GraphNode, GraphNodeType, GraphTopologyAnalysis, GraphTopologyMeta, GraphTopologyResponse } from '../types/graph'
import { observeElementsResize } from '../utils/resizeObserver'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import { buildGraphSourceSummary } from './graph/sourceState.js'
import { WORKSPACE_THEME_CHANGED_EVENT } from '../utils/workspaceTheme'

type GraphFocusPreset = 'all' | 'collaboration' | 'themes' | 'achievements'

const props = withDefaults(
  defineProps<{
    userId: number | string
    initialFocusPreset?: GraphFocusPreset
  }>(),
  {
    initialFocusPreset: 'all',
  },
)

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
const currentUser = ref<SessionUser | null>(null)
const searchQuery = ref('')
const focusPreset = ref<GraphFocusPreset>(props.initialFocusPreset)

let chartInstance: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const getComputedThemeColor = (token: string, fallback: string) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  return value || fallback
}

const sourceSummary = computed(() => buildGraphSourceSummary(graphMeta.value))
const focusPresetLabelMap: Record<GraphFocusPreset, string> = {
  all: '全部节点',
  collaboration: '合作视角',
  themes: '主题视角',
  achievements: '成果视角',
}
const focusPresetLabel = computed(() => focusPresetLabelMap[focusPreset.value])
const focusPresetOptions = [
  { label: '全部节点', value: 'all' },
  { label: '合作视角', value: 'collaboration' },
  { label: '主题视角', value: 'themes' },
  { label: '成果视角', value: 'achievements' },
]

const nodeMeta: Record<string, { label: string; shortLabel: string; color: string; category: number }> = {
  CenterTeacher: { label: '中心教师：画像主体', shortLabel: '教师', color: '#2563eb', category: 0 },
  Paper: { label: '论文：学术产出', shortLabel: '论文', color: '#14b8a6', category: 1 },
  ExternalScholar: { label: '合作者：合作网络', shortLabel: '合作', color: '#ef4444', category: 2 },
  Keyword: { label: '关键词：研究主题', shortLabel: '关键词', color: '#f59e0b', category: 3 },
  Project: { label: '项目：科研攻关', shortLabel: '项目', color: '#8b5cf6', category: 4 },
  IntellectualProperty: { label: '知识产权：成果转化', shortLabel: '知产', color: '#f97316', category: 5 },
  TeachingAchievement: { label: '教学成果：育人成效', shortLabel: '教学', color: '#06b6d4', category: 6 },
  AcademicService: { label: '学术服务：共同体贡献', shortLabel: '服务', color: '#84cc16', category: 7 },
}

const presetAllowedTypes: Record<GraphFocusPreset, GraphNodeType[] | null> = {
  all: null,
  collaboration: ['CenterTeacher', 'Paper', 'ExternalScholar'],
  themes: ['CenterTeacher', 'Paper', 'Keyword'],
  achievements: ['CenterTeacher', 'Paper', 'Project', 'IntellectualProperty', 'TeachingAchievement', 'AcademicService'],
}

const legendItems = Object.entries(nodeMeta).map(([type, meta]) => ({ type, label: meta.label, shortLabel: meta.shortLabel, color: meta.color }))
const filterItems = legendItems.filter(item => item.type !== 'CenterTeacher')
const isTypeVisible = (type: GraphNodeType) => !hiddenNodeTypes.value.includes(type)

const visibleNodes = computed(() => {
  const allowedTypes = presetAllowedTypes[focusPreset.value]
  return graphNodes.value.filter(node => {
    if (node.nodeType === 'CenterTeacher') return true
    if (!isTypeVisible(node.nodeType)) return false
    return !allowedTypes || allowedTypes.includes(node.nodeType)
  })
})

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
  linkCount: graphLinks.value.length,
}))

const graphHeadline = computed(() => {
  if (selectedNode.value) {
    return `当前焦点位于“${selectedNode.value.name}”，可继续围绕该节点查看关系链和支撑记录。`
  }
  if (selectedLink.value) {
    return `当前正在查看“${selectedLink.value.relationLabel || selectedLink.value.name}”这条边关系。`
  }
  return `当前以${focusPresetLabel.value}浏览图谱，节点 ${graphMeta.value?.node_count ?? 0} 个，关系 ${graphMeta.value?.link_count ?? 0} 条。`
})

const selectedNodeCanOpenAchievement = computed(
  () => Boolean(selectedNode.value?.entityId && selectedNode.value?.recordType && currentUser.value && !currentUser.value.is_admin),
)

const selectedPathAnalysis = computed(() => {
  if (!selectedNode.value || selectedNode.value.nodeType === 'CenterTeacher') return null
  const centerNode = visibleNodes.value.find(node => node.nodeType === 'CenterTeacher')
  if (!centerNode) return null

  const adjacency = new Map<string, Array<{ id: string; relationLabel: string }>>()
  visibleLinks.value.forEach(link => {
    const relationLabel = link.relationLabel || link.name
    adjacency.set(link.source, [...(adjacency.get(link.source) || []), { id: link.target, relationLabel }])
    adjacency.set(link.target, [...(adjacency.get(link.target) || []), { id: link.source, relationLabel }])
  })

  const queue = [centerNode.id]
  const visited = new Set<string>([centerNode.id])
  const parentMap = new Map<string, { parentId: string; relationLabel: string }>()

  while (queue.length) {
    const currentId = queue.shift()
    if (!currentId) continue
    if (currentId === selectedNode.value.id) break
    ;(adjacency.get(currentId) || []).forEach(item => {
      if (visited.has(item.id)) return
      visited.add(item.id)
      parentMap.set(item.id, { parentId: currentId, relationLabel: item.relationLabel })
      queue.push(item.id)
    })
  }

  if (!visited.has(selectedNode.value.id)) return null

  const pathNodeIds: string[] = []
  const relationLabels: string[] = []
  let cursor = selectedNode.value.id
  while (cursor !== centerNode.id) {
    pathNodeIds.unshift(cursor)
    const parent = parentMap.get(cursor)
    if (!parent) return null
    relationLabels.unshift(parent.relationLabel)
    cursor = parent.parentId
  }
  pathNodeIds.unshift(centerNode.id)

  const nodeNames = pathNodeIds
    .map(id => visibleNodes.value.find(node => node.id === id)?.name)
    .filter((name): name is string => Boolean(name))

  let summaryText = `当前节点通过 ${relationLabels.join(' -> ')} 与教师主体相连。`
  if (selectedNode.value.nodeType === 'ExternalScholar') {
    summaryText = '当前合作者节点通过“教师 -> 论文 -> 合作者”关系链进入合作网络，可用于解释合作圈层。'
  } else if (selectedNode.value.nodeType === 'Keyword') {
    summaryText = '当前关键词节点通过“教师 -> 论文 -> 关键词”关系链进入主题分析，可用于解释研究热点来源。'
  } else if (['Paper', 'Project', 'IntellectualProperty', 'TeachingAchievement', 'AcademicService'].includes(selectedNode.value.nodeType)) {
    summaryText = '当前成果节点与教师主体直接相连，可作为图谱中的一级证据节点。'
  }

  return {
    title: `教师到“${selectedNode.value.name}”的关系路径`,
    summary: summaryText,
    nodeNames,
    relationLabels,
    boundaryNote: '当前路径说明仅基于已加载子图的最短关系链，不代表全库检索、复杂路径推理或图挖掘结果。',
  }
})

const nodeTypeLabel = (type: string) => nodeMeta[type]?.label.split('：')[0] || type

const toggleNodeType = (type: GraphNodeType) => {
  hiddenNodeTypes.value = isTypeVisible(type) ? hiddenNodeTypes.value.concat(type) : hiddenNodeTypes.value.filter(item => item !== type)
}

const fetchGraphData = async (userId: number | string): Promise<GraphTopologyResponse> => {
  const sessionUser = await ensureSessionUserContext()
  currentUser.value = sessionUser
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
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)

  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      show: true,
      backgroundColor: getComputedThemeColor('--surface-2', '#ffffff'),
      borderColor: getComputedThemeColor('--border-color', '#e2e8f0'),
      textStyle: { color: getComputedThemeColor('--text-primary', '#0f172a') },
      formatter: (params: { dataType: string; data: GraphNode | GraphLink }) => {
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
              borderColor: getComputedThemeColor('--surface-1', '#ffffff'),
              borderWidth: node.nodeType === 'CenterTeacher' ? 3 : 1,
              shadowBlur: node.nodeType === 'CenterTeacher' ? 24 : 10,
              shadowColor:
                node.nodeType === 'CenterTeacher'
                  ? 'rgba(37,99,235,0.34)'
                  : getComputedThemeColor('--shadow-color', 'rgba(148,163,184,0.18)'),
            },
            label: { show: true, color: getComputedThemeColor('--text-secondary', '#334155') },
          }
        }),
        links: visibleLinks.value.map(link => ({
          ...link,
          lineStyle: { color: getComputedThemeColor('--border-color-soft', 'rgba(148, 163, 184, 0.75)'), width: 2, curveness: 0.12 },
          label: {
            show: true,
            formatter: link.relationLabel || link.name,
            fontSize: 11,
            color: getComputedThemeColor('--text-tertiary', '#64748b'),
            backgroundColor: getComputedThemeColor('--surface-1', 'rgba(255,255,255,0.82)'),
            padding: [2, 6],
            borderRadius: 8,
          },
        })),
        force: { repulsion: 560, edgeLength: [70, 160], gravity: 0.06 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 3, color: getComputedThemeColor('--text-secondary', '#334155') } },
      },
    ],
  })

  bindChartEvents()
}

const syncSelectionWithVisibleGraph = () => {
  if (selectedNode.value && !visibleNodes.value.some(node => node.id === selectedNode.value?.id)) {
    selectedNode.value = visibleNodes.value.find(node => node.nodeType === 'CenterTeacher') ?? visibleNodes.value[0] ?? null
  }
  if (
    selectedLink.value &&
    !visibleLinks.value.some(
      link => link.source === selectedLink.value?.source && link.target === selectedLink.value?.target && link.name === selectedLink.value?.name,
    )
  ) {
    selectedLink.value = null
  }
}

const focusSearchedNode = async () => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) {
    ElMessage.info('请输入节点名称或摘要关键词。')
    return
  }
  const matchedNode = visibleNodes.value.find(node => [node.name, ...(node.detailLines || [])].some(item => item.toLowerCase().includes(keyword)))
  if (!matchedNode) {
    ElMessage.info('当前筛选结果中未找到匹配节点。')
    return
  }
  selectedNode.value = matchedNode
  selectedLink.value = null
  await renderGraph()
}

const resetGraphFilters = async () => {
  searchQuery.value = ''
  focusPreset.value = 'all'
  hiddenNodeTypes.value = []
  selectedNode.value = graphNodes.value.find(node => node.nodeType === 'CenterTeacher') ?? graphNodes.value[0] ?? null
  selectedLink.value = null
  if (!isEmpty.value && !hasError.value) await renderGraph()
}

const openSelectedRecordEvidence = async () => {
  if (!selectedNodeCanOpenAchievement.value || !selectedNode.value?.recordType || !selectedNode.value.entityId) return
  await router.push({
    name: 'AchievementEntry',
    query: buildCrossModuleQuery({
      source: 'graph',
      page: 'achievement-entry',
      section: 'achievement-records',
      record_type: selectedNode.value.recordType,
      record_id: String(selectedNode.value.entityId),
      note: '当前从学术图谱节点回跳到对应成果记录，可在成果页继续核验。',
    }),
  })
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
    focusPreset.value = 'all'

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

const handleResize = () => chartInstance?.resize()

const ensureResizeObserver = () => {
  if (resizeObserver || !chartRef.value) return
  resizeObserver = observeElementsResize([chartRef.value], handleResize)
}

watch(() => props.userId, () => void loadGraph())
watch(
  () => props.initialFocusPreset,
  value => {
    focusPreset.value = value || 'all'
  },
)

watch([hiddenNodeTypes, focusPreset], async () => {
  if (!graphNodes.value.length || isEmpty.value || hasError.value) return
  syncSelectionWithVisibleGraph()
  await renderGraph()
})

watch(
  () => currentUser.value && document.documentElement.getAttribute('data-workspace-theme'),
  async () => {
    if (!graphNodes.value.length || isEmpty.value || hasError.value) return
    await renderGraph()
  },
)

onMounted(() => {
  void loadGraph()
  ensureResizeObserver()
  window.addEventListener(WORKSPACE_THEME_CHANGED_EVENT, renderGraph)
})

onBeforeUnmount(() => {
  window.removeEventListener(WORKSPACE_THEME_CHANGED_EVENT, renderGraph)
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.graph-shell {
  display: grid;
  gap: 16px;
}

.graph-top,
.graph-toolbar-panel,
.graph-board,
.footer-section,
.side-section {
  border-radius: 22px;
  background: var(--card-bg);
  border: 1px solid var(--border-color-soft);
  box-shadow: var(--workspace-shadow);
}

.graph-top,
.graph-toolbar-panel,
.graph-board {
  padding: 16px 18px;
}

.graph-top__head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.graph-top__eyebrow {
  margin: 0 0 6px;
  color: var(--text-tertiary);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.graph-top__title {
  margin: 0;
  color: var(--text-primary);
  font-size: 30px;
}

.graph-top__summary {
  margin: 10px 0 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.graph-top__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 10px;
  min-width: min(420px, 100%);
}

.graph-stat-pill {
  padding: 12px 14px;
  border-radius: 16px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.graph-stat-pill span {
  display: block;
  margin-bottom: 6px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.graph-stat-pill strong {
  color: var(--text-primary);
  font-size: 18px;
}

.graph-top__subline {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 14px;
}

.graph-top__notice {
  line-height: 1.6;
}

.graph-toolbar-panel {
  display: grid;
  gap: 10px;
}

.graph-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.graph-toolbar--filters {
  justify-content: flex-start;
  align-items: center;
}

.toolbar-label {
  color: var(--text-tertiary);
  font-size: 13px;
  margin-right: 4px;
}

.toolbar-search {
  width: 240px;
}

.toolbar-select {
  width: 150px;
}

.graph-board {
  position: relative;
  min-height: 720px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--brand-primary) 5%, var(--surface-1)) 0%, var(--surface-2) 100%);
}

.chart-area {
  position: relative;
}

.graph-canvas {
  width: 100%;
  height: 620px;
}

.state-layer {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: color-mix(in srgb, var(--surface-1) 92%, transparent);
}

.graph-bottom {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 16px;
}

.footer-section,
.side-section {
  padding: 18px;
  background: var(--panel-bg);
}

.footer-title,
.side-title {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-weight: 600;
}

.legend-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.legend-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.mini-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.mini-grid--summary {
  margin-top: 6px;
}

.mini-card,
.focus-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: var(--surface-1);
  border: 1px solid var(--border-color-soft);
}

.focus-card {
  display: grid;
  gap: 8px;
}

.mini-label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.mini-card strong {
  color: var(--text-primary);
  font-size: 18px;
}

.focus-type {
  display: inline-flex;
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--surface-3);
  color: var(--text-secondary);
  font-size: 12px;
}

.focus-desc,
.muted-block {
  margin: 0;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 1180px) {
  .graph-top__head,
  .graph-bottom {
    display: grid;
    grid-template-columns: 1fr;
  }

  .graph-top__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    min-width: 0;
  }
}

@media (max-width: 768px) {
  .graph-top__stats,
  .mini-grid {
    grid-template-columns: 1fr;
  }

  .graph-board {
    padding: 12px;
  }

  .graph-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-search,
  .toolbar-select {
    width: 100%;
  }
}
</style>
