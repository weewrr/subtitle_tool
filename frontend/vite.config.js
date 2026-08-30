import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts'
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables.scss" as *;`
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
    esbuild: {
      drop: ['console', 'debugger']
    },
    rollupOptions: {
      output: {
        // 函数形式:按需引入后 element-plus 为深路径导入(如 element-plus/es/components/...),
        // 需按模块 ID 归组,避免分散或重复打包
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('@element-plus/icons-vue')) return 'el-icons'
          if (id.includes('element-plus')) return 'element-plus'
          if (/node_modules[\\/](vue|@vue|vue-router|pinia)[\\/]/.test(id)) return 'vue-vendor'
        }
      }
    }
  }
})
