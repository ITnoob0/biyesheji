<template>
  <div class="dashboard-wrapper">
    <el-card class="welcome-header" shadow="never">
      <div class="header-content">
        <div>
          <h2 class="greeting">👨‍🏫 欢迎回来，刘老师！</h2>
          <p class="subtitle">您的科研能力数字画像与数据分析引擎已就绪。</p>
        </div>
        <div class="quick-actions">
          <el-button type="primary" icon="DocumentAdd">录入论文</el-button>
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
              <component :is="stat.icon" />
            </el-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stat.value }}</span>
            <span v-if="stat.suffix" class="stat-suffix">{{ stat.suffix }}</span>
          </div>
          <div class="stat-footer">
            <span class="trend-text">较去年同期</span>
            <span :class="['trend-value', stat.trend > 0 ? 'up' : 'down']">
              <el-icon><CaretTop v-if="stat.trend > 0" /><CaretBottom v-else /></el-icon>
              {{ Math.abs(stat.trend) }}%
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-container">
      <el-col :span="14">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📈 科研生命周期轨迹 (近十年)</span>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-instance"></div>
        </el-card>
      </el-col>
      
      <el-col :span="10">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>🎯 综合能力雷达评估</span>
            </div>
          </template>
          <div ref="radarChartRef" class="chart-instance"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, markRaw } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { 
  DocumentAdd, Share, Cpu, 
  Document, Star, Trophy, Reading,
  CaretTop, CaretBottom
} from '@element-plus/icons-vue'

// --- 数据卡片数据 (赋初始默认值防止页面白屏) ---
const statistics = ref([
  { title: '总发文量', value: 0, suffix: '篇', icon: 'Document', iconClass: 'icon-blue', trend: 0 },
  { title: '总被引频次', value: 0, suffix: '次', icon: 'Star', iconClass: 'icon-orange', trend: 0 },
  { title: '综合科研评分', value: 0, suffix: '分', icon: 'Trophy', iconClass: 'icon-red', trend: 0 },
  { title: '主持/参与项目', value: 0, suffix: '项', icon: 'Reading', iconClass: 'icon-green', trend: 0 }
])

// --- ECharts 图表逻辑 ---
const trendChartRef = ref<HTMLElement | null>(null)
const radarChartRef = ref<HTMLElement | null>(null)
let trendChartInstance: echarts.ECharts | null = null
let radarChartInstance: echarts.ECharts | null = null

// --- 获取后端数据 ---
const fetchDashboardData = async () => {
  try {
    // 请根据你的 Django 配置修改实际 URL 前缀，如果配了路由此处可能是 /api/dashboard-stats/
    // 为了防止你没配跨域，这里演示使用完整路径。如果运行端口不是 8000 请对应修改。
    const response = await axios.get('http://127.0.0.1:8000/dashboard-stats/') 
    const data = response.data
    
    statistics.value = data.statistics
    updateRadarChart(data.radar_data)
    
  } catch (error) {
    console.error("获取概览数据失败:", error)
  }
}

// 初始化科研趋势图 (静态演示数据，不请求后端)
const initTrendChart = () => {
  if (!trendChartRef.value) return
  trendChartInstance = markRaw(echarts.init(trendChartRef.value))
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['发文量 (篇)', '被引频次 (次)'], bottom: '0' },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '10%', containLabel: true },
    xAxis: [{ type: 'category', data: ['2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024'], axisPointer: { type: 'shadow' } }],
    yAxis: [
      { type: 'value', name: '发文量', min: 0, max: 10, interval: 2, axisLabel: { formatter: '{value}' } },
      { type: 'value', name: '被引频次', min: 0, max: 300, interval: 60, axisLabel: { formatter: '{value}' } }
    ],
    series: [
      { name: '发文量 (篇)', type: 'bar', itemStyle: { color: '#409EFF' }, data: [2, 3, 3, 5, 4, 6, 4, 8, 5, 2] },
      { name: '被引频次 (次)', type: 'line', yAxisIndex: 1, smooth: true, itemStyle: { color: '#F56C6C' }, data: [15, 30, 45, 80, 110, 150, 180, 240, 260, 176] }
    ]
  }
  trendChartInstance.setOption(option)
}

// 初始化雷达图空壳
const initRadarChart = () => {
  if (!radarChartRef.value) return
  radarChartInstance = markRaw(echarts.init(radarChartRef.value))
  radarChartInstance.showLoading()
}

// 接收后端真实数据并渲染雷达图
const updateRadarChart = (radarData: any[]) => {
  if (!radarChartInstance) return
  radarChartInstance.hideLoading()
  
  const indicator = radarData.map(item => ({ name: item.name, max: 100 }))
  const scores = radarData.map(item => item.value)

  const option = {
    tooltip: {},
    legend: { data: ['当前学者评分'], bottom: '0' },
    radar: {
      center: ['50%', '42%'], 
      radius: '60%',          
      indicator: indicator, 
      shape: 'circle',
      splitNumber: 5,
      axisName: { color: '#606266' },
      splitArea: { areaStyle: { color: ['#f4f7fc', '#eef1f6', '#e7ebf1', '#e0e5eb', '#d9dee4'] } }
    },
    series: [{
      name: '能力评估',
      type: 'radar',
      data: [{
        value: scores,
        name: '当前学者评分',
        areaStyle: { color: 'rgba(64, 158, 255, 0.4)' },
        lineStyle: { color: '#409EFF' },
        itemStyle: { color: '#409EFF' }
      }]
    }]
  }
  radarChartInstance.setOption(option)
}

const handleResize = () => {
  trendChartInstance?.resize()
  radarChartInstance?.resize()
}

onMounted(() => {
  initTrendChart()
  initRadarChart()
  fetchDashboardData() // 发起真实数据请求
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInstance?.dispose()
  radarChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-wrapper {
  padding: 20px;
}
.welcome-header {
  margin-bottom: 24px;
  border-radius: 8px;
  background: linear-gradient(135deg, #ffffff 0%, #f4f7fc 100%);
  border: 1px solid #ebeef5;
}
.header-content { display: flex; justify-content: space-between; align-items: center; }
.greeting { margin: 0 0 8px 0; color: #303133; font-size: 22px; }
.subtitle { margin: 0; color: #909399; font-size: 14px; }
.quick-actions .el-button { margin-left: 12px; }
.stat-cards-container { margin-bottom: 24px; }
.stat-card { border-radius: 8px; transition: all 0.3s; }
.stat-card:hover { transform: translateY(-2px); }
.stat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.stat-title { font-size: 14px; color: #606266; font-weight: 500; }
.icon-blue { color: #409EFF; }
.icon-orange { color: #E6A23C; }
.icon-red { color: #F56C6C; }
.icon-green { color: #67C23A; }
.stat-body { margin-bottom: 16px; }
.stat-value { font-size: 28px; font-weight: bold; color: #303133; }
.stat-suffix { font-size: 14px; color: #909399; margin-left: 4px; }
.stat-footer { font-size: 13px; color: #909399; display: flex; align-items: center; border-top: 1px solid #ebeef5; padding-top: 12px; }
.trend-text { margin-right: 8px; }
.trend-value { display: flex; align-items: center; font-weight: bold; }
.trend-value.up { color: #F56C6C; }
.trend-value.down { color: #67C23A; }
.charts-container { margin-top: 20px; }
.chart-card { border-radius: 8px; }
.card-header { font-weight: bold; color: #303133; }
.chart-instance { height: 350px; width: 100%; }
</style>