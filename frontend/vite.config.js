import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeuiPlugin from 'frappe-ui/vite'

export default defineConfig({
  plugins: [
    vue(),
    frappeuiPlugin({
      lucideIcons: true,
      frappeProxy: false,    // we manage our own proxy below
      jinjaBootData: false,  // not a Frappe app
      buildConfig: false,    // we set our own outDir
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:8500',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    exclude: ['frappe-ui'],
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
