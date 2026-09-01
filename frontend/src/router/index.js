import { createRouter, createWebHistory } from 'vue-router'
import GateKeeper from '../views/GateKeeper.vue'

const router = createRouter({
  // createWebHistory needs the SPA fallback to index.html — this is
  // already configured in nginx.conf (try_files) for production, and
  // Vite's dev server handles it automatically.
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/gatekeeper' },
    // Exact casing requested for the URL
    { path: '/GateKeeper', redirect: '/gatekeeper' },
    { path: '/gatekeeper', name: 'gatekeeper', component: GateKeeper },
    { path: '/:pathMatch(.*)*', redirect: '/gatekeeper' },
  ],
})

export default router
