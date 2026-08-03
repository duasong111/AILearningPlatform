import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'
// https://vite.dev/config/
// Docker 环境下通过环境变量指定后端地址, 默认指向本地开发后端
const API_TARGET = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:38000'
const WS_TARGET = process.env.VITE_PROXY_WS_TARGET || 'ws://127.0.0.1:38000'

export default defineConfig({
  plugins: [vue(), vueJsx(), vueDevTools(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // 监听所有网卡（0.0.0.0），让局域网其他设备能访问
    // 启动后控制台会打印 Local: 和 Network: 两个地址
    host: true,
    port: 35173,
    // 端口被占时直接报错，而不是悄悄换一个端口（避免局域网设备访问到的端口对不上）
    strictPort: true,
    // 代理 /api/* 和 /ws/* 到后端 —— 避免 dev 阶段浏览器 CORS / 跨源 WS 拦截
    //   浏览器始终认为请求是同源 (http://localhost:35173 / ws://localhost:35173)
    //   /ws 需要 ws:true 让 vite-http-proxy 在握手时升级 HTTP→WebSocket
    //   真正部署时, 让前端和后端共用同一个 Nginx / 反代即可, 不再需要这个代理
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/ws': {
        target: WS_TARGET,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      onwarn(warning, warn) {
        // 忽略来自 @vueuse/core 的特定警告
        if (warning.code === 'INVALID_ANNOTATION' && warning.loc?.file?.includes('@vueuse/core')) {
          return
        }
        warn(warning)
      },
    },
  },
})
