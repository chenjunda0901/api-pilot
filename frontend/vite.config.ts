import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { fileURLToPath } from 'url'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  css: {
    devSourcemap: false,
    // lightningcss 是 Vite 8 默认 CSS 处理器，保留它但用 esbuild 做压缩，
    // 并开启 errorRecovery 避免 :deep() 导致的构建失败。
    transformer: 'lightningcss',
    lightningcss: {
      errorRecovery: true,
      cssModules: false,
      drafts: { nesting: false, customMedia: false },
    },
    minify: 'esbuild',
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 800, // Monaco Editor 超大包容忍阈值
    cssCodeSplit: true,        // 按路由拆分 CSS（减少首屏 CSS 体积）
    target: 'es2022',          // 现代浏览器目标，允许使用原生顶层 await / StructuredClone
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('monaco-editor')) return 'vendor-monaco'
          if (id.includes('echarts')) return 'vendor-echarts'
          if (id.includes('element-plus')) return 'vendor-element-plus'
          if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router') || id.includes('vue-i18n')) {
            return 'vendor-vue'
          }
          return 'vendor-utils'
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 8080,
    strictPort: false,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: true,
    }),
    {
      name: 'port-notify',
      configureServer(server) {
        server.httpServer?.once('listening', () => {
          const addr = server.httpServer?.address()
          if (addr && typeof addr === 'object') {
            const port = addr.port
            if (port !== 8080) {
              console.log('')
              console.log('  ╔════════════════════════════════════════╗')
              console.log(`  ║  端口 8080 已被占用，已切换到端口 ${port}  ║`)
              console.log('  ╚════════════════════════════════════════╝')
              console.log('')
            }
          }
        })
      },
    },
  ],
})