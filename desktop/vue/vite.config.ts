import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 兼容桌面与 Web 双构建目标：
// - 桌面（Electron file://）：保留 removeCrossorigin，base 用相对路径。
// - Web（http/https）：removeCrossorigin 去除的 crossorigin 属性在同源下无害；
//   base 相对路径在站点根域名下同样可加载。
function removeCrossorigin() {
  return {
    name: 'remove-crossorigin',
    enforce: 'post' as const,
    transformIndexHtml(html: string) {
      return html.replace(/\s+crossorigin(="[^"]*")?/g, '')
    },
  }
}

export default defineConfig({
  base: './',
  plugins: [vue(), removeCrossorigin()],
  build: {
    // 沙箱会拦截 Vite 默认的 rmSync 清目录，关闭自动清空
    emptyOutDir: false,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5088',
        changeOrigin: true,
      },
    },
  },
  // 生产构建预览（Web 运行）：托管 dist 并代理 /api 到本地后端
  preview: {
    port: 4173,
    host: true, // 监听 0.0.0.0，局域网设备（手机/他人电脑）可通过本机 IP 访问
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5088',
        changeOrigin: true,
      },
    },
  },
})
