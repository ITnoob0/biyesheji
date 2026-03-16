<template>
  <div class="dashboard-wrapper">
    <el-card class="welcome-header" shadow="never">
      <div class="header-content">
        <div>
          <h2 class="greeting">欢迎回来，{{ teacherInfo.name || '教师' }}！</h2>
          <p class="subtitle">所属学院：{{ teacherInfo.department || '未知' }} | 职称：{{ teacherInfo.title || '未知' }}</p>
        </div>
        <div class="quick-actions">
          <el-button type="primary" icon="DocumentAdd" @click="router.push('/entry')">录入论文</el-button>
          <el-button type="success" icon="Share">查看社交拓扑</el-button>
          <el-button type="warning" icon="Cpu">跨学科推荐</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" class="stat-cards-container">
      <el-col :span="6" v-for="(stat, index) in statistics" :key="index">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-header">
            <span class="stat-title">{{ stat.title }}</span>
            <el-icon :class="stat.iconClass" :size="20">
              <component :is="stat.icon"></component>
            </el-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stat.value }}</span>
            <span v-if="stat.suffix" class="stat-suffix">{{ stat.suffix }}</span>
          </div>
          <div class="stat-footer">
            <span class="trend-text">较去年同期</span>
            <span :class="['trend-value', stat.trend >= 0 ? 'up' : 'down']">
              <el-icon>
                <CaretTop v-if="stat.trend >= 0"></CaretTop>
                <CaretBottom v-else></CaretBottom>
              </el-icon>
              {{ Math.abs(stat.trend) }}%
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-container">
      <el-col :span="10">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>综合能力雷达评估</span>
            </div>
          </template>
          <RadarChart :radarData="radarData"></RadarChart>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>学术社交拓扑图</span>
            </div>
          </template>
          <AcademicGraph :userId="userId"></AcademicGraph>
        </el-card>
      </el-col>
    </el-row>

    <el-row style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header"><span>近十年科研产出趋势</span></div>
          </template>
          <div ref="trendChartRef" class="chart-instance" style="height: 400px; width: 100%;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, markRaw, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { 
  DocumentAdd, Share, Cpu, Document, Star, 
  Trophy, Reading, CaretTop, CaretBottom 
} from '@element-plus/icons-vue'
import AcademicGraph from './AcademicGraph.vue'
import RadarChart from '../components/RadarChart.vue'

const route = useRoute()
const router = useRouter()
const userId = ref(route.params.id || 1)

const statistics = ref([
  { title: '总发文量', value: 0, suffix: '篇', icon: 'Document', iconClass: 'icon-blue', trend: 0 },
  { title: '总被引频次', value: 0, suffix: '次', icon: 'Star', iconClass: 'icon-orange', trend: 0 },
  { title: '综合科研评分', value: 0, suffix: '分', icon: 'Trophy', iconClass: 'icon-red', trend: 0 },
  { title: '主持/参与项目', value: 0, suffix: '项', icon: 'Reading', iconClass: 'icon-green', trend: 0 }
])
const radarData = ref([])
const teacherInfo = ref({ name: '加载中...', department: '...', title: '...' })

const trendChartRef = ref<HTMLElement | null>(null)
let trendChartInstance: echarts.ECharts | null = null

const fetchDashboardData = async () => {
  try {
    const token = localStorage.getItem('token')
    const headers = { Authorization: `Bearer ${token}` }

    const statsRes = await axios.get('/api/achievements/dashboard-stats/', { headers })
    if (statsRes.data.statistics) {
      statistics.value = statsRes.data.statistics
    }

    const radarRes = await axios.get(`/api/achievements/radar/${userId.value}/`, { headers })
    radarData.value = radarRes.data.radar_dimensions

    teacherInfo.value = {
      name: userId.value == 1 ? '系统管理员' : '科研教师',
      department: '计算机学院',
      title: '高级研究员'
    }
  } catch (error) {
    console.error('Data fetch error:', error)
    ElMessage.error('无法获取数据，请检查后端 API 状态')
  }
}

const initTrendChart = () => {
  if (!trendChartRef.value) return
  trendChartInstance = markRaw(echarts.init(trendChartRef.value))
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['发文量 (篇)', '被引频次 (次)'], bottom: '0' },
    xAxis: { type: 'category', data: ['2018', '2019', '2020', '2021', '2022', '2023', '2024'] },
    yAxis: [{ type: 'value' }, { type: 'value', yAxisIndex: 1 }],
    series: [
      { name: '发文量 (篇)', type: 'bar', data: [3, 5, 4, 6, 4, 8, 5] },
      { name: '被引频次 (次)', type: 'line', yAxisIndex: 1, data: [45, 80, 110, 150, 180, 240, 260] }
    ]
  }
  trendChartInstance.setOption(option)
}

const handleResize = () => {
  trendChartInstance?.resize()
}

watch(() => route.params.id, (newId) => {
  userId.value = newId || 1
  fetchDashboardData()
})

onMounted(() => {
  initTrendChart()
  fetchDashboardData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-wrapper { padding: 20px; background-color: #f8f9fa; min-height: 100vh; }
.welcome-header { margin-bottom: 24px; border-radius: 8px; background: white; }
.header-content { display: flex; justify-content: space-between; align-items: center; }
.greeting { margin: 0 0 8px 0; color: #303133; font-size: 22px; }
.subtitle { margin: 0; color: #909399; font-size: 14px; }
.stat-cards-container { margin-bottom: 24px; }
.stat-card { border-radius: 8px; }
.stat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.stat-title { font-size: 14px; color: #606266; }
.stat-value { font-size: 28px; font-weight: bold; }
.icon-blue { color: #409EFF; }
.icon-orange { color: #E6A23C; }
.icon-red { color: #F56C6C; }
.icon-green { color: #67C23A; }
.trend-value.up { color: #F56C6C; }
.trend-value.down { color: #67C23A; }
.chart-instance { height: 350px; width: 100%; }
</style>