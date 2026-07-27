import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 移除 Vite 注入的 crossorigin 属性：Electron file:// 协议下 crossorigin 会触发
// CORS 策略导致 ESM 模块加载失败、界面白屏。本地应用无需 CORS 隔离。
function removeCrossorigin() {
  return {
    name: 'remove-crossorigin',
    enforce: 'post' as const,
    transformIndexHtml(html: string) {
      return html.replace(/\s+crossorigin(="[^"]*")?/g, '')
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  // 生产打包进 Electron 时用相对路径，确保 file:///asar 下资源可加载
  base: './',
  plugins: [vue(), removeCrossorigin()],
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
