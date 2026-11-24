import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        // 后端端口可用环境变量覆盖（默认 8080），便于多实例并行开发
        target: `http://localhost:${process.env.BACKEND_PORT || 8080}`,
        changeOrigin: true,
      },
    },
  },
})
