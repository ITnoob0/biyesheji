<template>
  <div v-show="radarData && radarData.length > 0" ref="radarRef" style="width:100%;height:400px;"></div>
  <div v-if="!radarData || radarData.length === 0" class="empty-placeholder">
    <el-empty description="暂无科研画像数据" :image-size="100" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, nextTick } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{ radarData: { name: string; value: number }[] }>();
const radarRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const renderRadar = async () => {
  // 核心修复：如果数据为空，直接跳过渲染，避免 ECharts 内部布局崩溃
  if (!props.radarData || props.radarData.length === 0) {
    return;
  }

  // 等待 DOM 更新
  await nextTick();
  
  if (!radarRef.value) return;

  // 优化：如果实例不存在则初始化，存在则复用
  if (!chart) {
    chart = echarts.init(radarRef.value);
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        // 雷达图的数据结构较特殊，params.value 是一个数组
        return `<b>${params.name}</b>`;
      },
    },
    radar: {
      // 这里的 indicator 必须有值，否则 radarLayout.js 会报错
      indicator: props.radarData.map(d => ({ name: d.name, max: 100 })),
      shape: 'circle',
      radius: '65%',
      splitNumber: 5,
      axisName: {
        color: '#606266',
        fontWeight: 'bold',
      },
      splitArea: {
        areaStyle: {
          color: ['#f4f7fc', '#eef1f6', '#e7ebf1', '#e0e5eb', '#d9dee4']
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.radarData.map(d => d.value),
            name: '当前学者学术画像',
            areaStyle: { color: 'rgba(64, 158, 255, 0.4)' },
            lineStyle: { color: '#409EFF' },
            itemStyle: { color: '#409EFF' },
            symbolSize: 6
          },
        ],
      },
    ],
  };
  chart.setOption(option);
};

// 监听数据变化
watch(() => props.radarData, () => {
  renderRadar();
}, { deep: true });

onMounted(() => {
  renderRadar();
  window.addEventListener('resize', handleResize);
});

const handleResize = () => {
  chart?.resize();
};

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (chart) {
    chart.dispose();
    chart = null;
  }
});
</script>

<style scoped>
.empty-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
  background: #fdfdfd;
  border-radius: 8px;
}
</style>