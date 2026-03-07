<template>
  <div class="dashboard-wrapper">
    <el-card class="welcome-card">
      <h1>👨‍🏫 欢迎来到 教师科研能力数字画像与智能辅助系统</h1>
      <p>您的科研数据分析引擎已就绪！</p>
      
      <div style="margin-top: 30px;">
        <el-button type="primary" size="large" icon="DocumentAdd">录入论文</el-button>
        <el-button type="success" size="large" icon="Share">查看学术社交拓扑图</el-button>
        <el-button type="warning" size="large" icon="Cpu">启动跨学科推荐</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.dashboard-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
.welcome-card {
  text-align: center;
  padding: 40px;
  width: 800px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
h1 {
  color: #303133;
}
p {
  color: #606266;
  font-size: 16px;
}
</style>