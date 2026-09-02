import { createApp, h } from 'vue'
import { createRouter, createWebHistory, RouterView } from 'vue-router'
import App from './App.vue'
import './style.css'

// The cities app lives at the sub-URL /cities (not the site base).
// Everything else is redirected there.
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/cities' },
    { path: '/cities', component: App },
    { path: '/:pathMatch(.*)*', redirect: '/cities' },
  ],
})

createApp({ render: () => h(RouterView) }).use(router).mount('#app')
