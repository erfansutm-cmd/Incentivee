import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In development the browser talks to this Vite dev server, which proxies
// /api requests to the FastAPI backend. The default target is the Docker
// Compose service name "backend"; override it locally with
// VITE_API_PROXY_TARGET=http://localhost:8000 when running without Docker.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://backend:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // listen on 0.0.0.0 so the port is reachable from the host
    port: 5173,
    strictPort: true,
    allowedHosts: true, // allow access through tunnels / preview proxies
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
