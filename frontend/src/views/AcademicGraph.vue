<template>
  <div class="academic-graph-container">
    <div ref="chartRef" style="width:100%;height:600px;"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { defineProps } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';

const chartRef = ref<HTMLDivElement | null>(null);
const props = defineProps<{ userId: number | string }>();

const nodeColors = {
  CenterTeacher: '#5470C6',
  Paper: '#91CC75',
  Keyword: '#FAC858',
  ExternalScholar: '#EE6666',
};

const fetchGraphData = async (userId: number | string) => {
  const token = localStorage.getItem('token');
  const response = await axios.get(`/api/graph/topology/${userId}/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};

const renderGraph = (data: any) => {
  const option = {
    tooltip: {
      show: true,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `<b>${params.data.name}</b><br/>类型: ${params.data.nodeType}`;
        } else if (params.dataType === 'edge') {
          return `<b>关系:</b> ${params.data.name}`;
        }
        return '';
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: data.nodes.map((node: any) => ({
          ...node,
          itemStyle: {
            color: nodeColors[node.nodeType] || '#888',
          },
          draggable: true,
        })),
        links: data.links,
        categories: [
          { name: '教师', itemStyle: { color: nodeColors.CenterTeacher } },
          { name: '论文', itemStyle: { color: nodeColors.Paper } },
          { name: '外部学者', itemStyle: { color: nodeColors.ExternalScholar } },
          { name: '关键词', itemStyle: { color: nodeColors.Keyword } },
        ],
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
        },
        force: {
          repulsion: 200,
          edgeLength: 120,
        },
      },
    ],
  };
  const chart = echarts.init(chartRef.value!);
  chart.setOption(option);
};

let chart: echarts.ECharts | null = null;
const loadGraph = async () => {
  if (!props.userId) return;
  const data = await fetchGraphData(props.userId);
  if (chart) chart.dispose();
  chart = echarts.init(chartRef.value!);
  renderGraph(data);
};

onMounted(loadGraph);
watch(() => props.userId, loadGraph);

import { onBeforeUnmount } from 'vue';
onBeforeUnmount(() => {
  if (chart) chart.dispose();
});
</script>

<style scoped>
.academic-graph-container {
  width: 100%;
  height: 600px;
}
</style>
