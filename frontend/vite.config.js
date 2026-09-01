import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In development the browser talks to this Vite dev server, which proxies
// /api requests to the FastAPI container (service name "backend").
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // listen on 0.0.0.0 so the port is reachable from the host
    port: 5173,
    strictPort: true,
    allowedHosts: true, // allow access through tunnels / preview proxies
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
