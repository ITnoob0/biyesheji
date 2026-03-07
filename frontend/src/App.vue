<template>
  <div class="app-container">
    <router-view></router-view>
  </div>
</template>

<script setup lang="ts">
// 根组件只作为路由出口，不写具体内容
</script>

<style>
/* 重置全局默认样式，让页面撑满全屏 */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f5f7fa; 
}
#app, .app-container {
  height: 100vh;
  width: 100vw;
}
</style>