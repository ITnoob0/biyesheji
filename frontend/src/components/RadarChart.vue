<template>
  <div ref="radarRef" style="width:100%;height:400px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{ radarData: { name: string; value: number }[] }>();
const radarRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const renderRadar = () => {
  if (!radarRef.value) return;
  if (chart) chart.dispose();
  chart = echarts.init(radarRef.value);
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `<b>${params.name}</b>: ${params.value}`;
      },
    },
    radar: {
      indicator: props.radarData.map(d => ({ name: d.name, max: 100 })),
      shape: 'circle',
      radius: 150,
      splitNumber: 4,
      axisName: {
        color: '#333',
        fontWeight: 'bold',
      },
      splitLine: {
        lineStyle: { color: ['#aaa', '#ddd'] },
      },
      splitArea: {
        areaStyle: { color: ['#f5f7fa', '#fff'], opacity: 0.7 },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.radarData.map(d => d.value),
            name: '教师六维评分',
            areaStyle: { color: 'rgba(84,112,198,0.3)' },
            lineStyle: { color: '#5470C6' },
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color: '#5470C6' },
          },
        ],
      },
    ],
  };
  chart.setOption(option);
};

onMounted(renderRadar);
watch(() => props.radarData, renderRadar);
onBeforeUnmount(() => { if (chart) chart.dispose(); });
</script>

<style scoped>
div {
  width: 100%;
  height: 400px;
}
</style>
