import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      // 关键配置：将 /api 开头的请求转向后端
      '/api': {
        target: 'http://127.0.0.1:8000', // 确保这是你 Django 运行的地址
        changeOrigin: true,
        // 如果后端接口没有 /api 前缀，可以取消注释下面这行
        // rewrite: (path) => path.replace(/^\/api/, '') 
      }
    }
  }
})