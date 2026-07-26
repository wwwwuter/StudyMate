import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  // 生产打包进 Electron 时用相对路径，确保 file:///asar 下资源可加载
  base: './',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true, // 与 desktop/electron/main.js 中的 5173 保持一致
    proxy: {
      // 开发态：将 /api 转发到 Flask 后端（run.py 默认 127.0.0.1:5000）
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
