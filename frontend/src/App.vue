<script setup>
import { ref, onMounted } from 'vue'
import { endpoints } from './config'

const health = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    const res = await fetch(endpoints.health)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    health.value = await res.json()
  } catch (e) {
    error.value = e.message || 'Could not reach the backend'
  }
})
</script>

<template>
  <main class="container">
    <h1>Incentive</h1>
    <p class="subtitle">FastAPI + Vue 3 + Docker starter</p>

    <div v-if="health" class="card">
      <p>
        Backend health:
        <span class="badge ok">{{ health.status }}</span>
      </p>
      <p class="muted">
        {{ health.app }} — running in <strong>{{ health.environment }}</strong>
      </p>
    </div>

    <div v-else-if="error" class="card">
      <p>
        Backend health:
        <span class="badge err">error</span>
      </p>
      <p class="muted">{{ error }}</p>
    </div>

    <div v-else class="card">
      <p>Checking backend…</p>
    </div>
  </main>
</template>

<style scoped>
.container {
  width: min(560px, 92vw);
  text-align: center;
}

h1 {
  font-size: 1.9rem;
  margin-bottom: 0.25rem;
}

.subtitle {
  color: #64748b;
  margin-top: 0;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.5rem;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}

.badge {
  display: inline-block;
  padding: 0.15rem 0.7rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.9rem;
}

.badge.ok {
  background: #dcfce7;
  color: #166534;
}

.badge.err {
  background: #fee2e2;
  color: #991b1b;
}

.muted {
  color: #64748b;
  margin: 0.25rem 0 0;
}
</style>
