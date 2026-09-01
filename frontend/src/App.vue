<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from './api'

// ── State ──────────────────────────────────────────────────────
const cities = ref([])          // rows as returned by the API
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

// Inline editing: one row at a time, with a local draft
const editingId = ref(null)
const draft = ref({ id: null, name: '', parm1: 0, parm2: 0, parm3: 0 })

// New-city form
const newCity = ref({ name: '', parm1: 0, parm2: 0, parm3: 0 })
const adding = ref(false)

// Delete confirmation
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Sorting
const sortKey = ref('id')
const sortDir = ref(1) // 1 = asc, -1 = desc

// ── Derived ────────────────────────────────────────────────────
const sortedCities = computed(() =>
  [...cities.value].sort((a, b) => {
    const av = a[sortKey.value]
    const bv = b[sortKey.value]
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sortDir.value
    return String(av).localeCompare(String(bv)) * sortDir.value
  }),
)

const editingRow = computed(() => editingId.value !== null)

function isDraftValid() {
  return draft.value.name.trim().length > 0
}

// ── Load ───────────────────────────────────────────────────────
async function loadCities() {
  loading.value = true
  error.value = ''
  try {
    cities.value = await api.fetchCities()
  } catch (e) {
    error.value = `Failed to load cities: ${e.message}`
    // Show what the database table actually contains so schema mismatches
    // are visible instead of a generic error.
    try {
      const schema = await api.fetchCitySchema()
      if (schema.columns.length) {
        error.value += ` — the "cities" table in the DB has columns: ${schema.columns.map((c) => c.name).join(', ')}`
      } else {
        error.value += ' — the "cities" table does not exist (or has no columns) in the database'
      }
    } catch {
      /* could not reach the schema endpoint either */
    }
  } finally {
    loading.value = false
  }
}

// ── Sorting ────────────────────────────────────────────────────
function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = 1
  }
}

function sortArrow(key) {
  if (sortKey.value !== key) return ''
  return sortDir.value === 1 ? ' ↑' : ' ↓'
}

// ── Add a row ──────────────────────────────────────────────────
async function addCity() {
  const payload = {
    name: newCity.value.name.trim(),
    parm1: Number(newCity.value.parm1) || 0,
    parm2: Number(newCity.value.parm2) || 0,
    parm3: Number(newCity.value.parm3) || 0,
  }
  if (!payload.name) return

  adding.value = true
  error.value = ''
  notice.value = ''
  try {
    const created = await api.createCity(payload)
    cities.value.push(created)
    newCity.value = { name: '', parm1: 0, parm2: 0, parm3: 0 }
    notice.value = `City "${created.name}" added.`
  } catch (e) {
    error.value = `Failed to add city: ${e.message}`
  } finally {
    adding.value = false
  }
}

// ── Start / cancel editing a row ───────────────────────────────
function startEdit(row) {
  if (editingId.value !== null) return
  editingId.value = row.id
  draft.value = {
    id: row.id,
    name: row.name,
    parm1: row.parm1,
    parm2: row.parm2,
    parm3: row.parm3,
  }
}

function cancelEdit() {
  editingId.value = null
  draft.value = { id: null, name: '', parm1: 0, parm2: 0, parm3: 0 }
}

// ── Save a single row ──────────────────────────────────────────
async function saveRow() {
  const id = editingId.value
  if (id === null || !isDraftValid()) return

  const original = cities.value.find((c) => c.id === id)
  if (!original) return cancelEdit()

  // Only send fields that actually changed
  const patch = {}
  if (draft.value.name.trim() !== original.name) patch.name = draft.value.name.trim()
  for (const p of ['parm1', 'parm2', 'parm3']) {
    const v = Number(draft.value[p]) || 0
    if (v !== Number(original[p])) patch[p] = v
  }

  if (Object.keys(patch).length === 0) return cancelEdit()

  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const updated = await api.updateCity(id, patch)
    const idx = cities.value.findIndex((c) => c.id === id)
    if (idx !== -1) cities.value[idx] = updated
    notice.value = `City "${updated.name}" saved.`
    cancelEdit()
  } catch (e) {
    error.value = `Failed to save: ${e.message}`
  } finally {
    saving.value = false
  }
}

// ── Delete a row ───────────────────────────────────────────────
function openDelete(row) {
  deleteTarget.value = row
  showDeleteDialog.value = true
}

async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  deleting.value = true
  error.value = ''
  notice.value = ''
  try {
    await api.deleteCity(target.id)
    cities.value = cities.value.filter((c) => c.id !== target.id)
    if (editingId.value === target.id) cancelEdit()
    notice.value = `City "${target.name}" deleted.`
    showDeleteDialog.value = false
    deleteTarget.value = null
  } catch (e) {
    error.value = `Failed to delete: ${e.message}`
    showDeleteDialog.value = false
  } finally {
    deleting.value = false
  }
}

onMounted(loadCities)
</script>

<template>
  <section class="page">
    <header class="topbar">
      <h1>Cities</h1>
      <p class="tagline">City parameters — parm1, parm2, parm3</p>
    </header>

    <p v-if="error" class="banner error">{{ error }}</p>
    <p v-if="notice" class="banner ok">{{ notice }}</p>

    <div class="toolbar">
      <button class="btn small" :disabled="loading" @click="loadCities">
        {{ loading ? 'Loading…' : '⟳ Refresh' }}
      </button>
    </div>

    <!-- ── Table ─────────────────────────────────────────── -->
    <div class="table-wrap">
      <div v-if="loading" class="placeholder">Loading cities…</div>
      <div v-else-if="!cities.length" class="placeholder">
        No cities yet. Use the form below to add one.
      </div>

      <table v-else class="cities">
        <thead>
          <tr>
            <th class="col-id" @click="toggleSort('id')">ID{{ sortArrow('id') }}</th>
            <th class="col-name" @click="toggleSort('name')">Name{{ sortArrow('name') }}</th>
            <th class="col-param" @click="toggleSort('parm1')">parm1{{ sortArrow('parm1') }}</th>
            <th class="col-param" @click="toggleSort('parm2')">parm2{{ sortArrow('parm2') }}</th>
            <th class="col-param" @click="toggleSort('parm3')">parm3{{ sortArrow('parm3') }}</th>
            <th class="col-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sortedCities" :key="row.id" :class="{ editing: row.id === editingId }">
            <td class="col-id">{{ row.id }}</td>

            <td class="col-name">
              <template v-if="row.id === editingId">
                <input
                  v-model="draft.name"
                  class="cell-input"
                  type="text"
                  maxlength="80"
                  placeholder="Name"
                  @keydown.enter="saveRow"
                  @keydown.esc="cancelEdit"
                />
              </template>
              <template v-else>{{ row.name }}</template>
            </td>

            <td v-for="p in ['parm1', 'parm2', 'parm3']" :key="p" class="col-param">
              <template v-if="row.id === editingId">
                <input
                  v-model.number="draft[p]"
                  class="cell-input"
                  type="number"
                  step="any"
                  @keydown.enter="saveRow"
                  @keydown.esc="cancelEdit"
                />
              </template>
              <template v-else>{{ row[p] }}</template>
            </td>

            <td class="col-actions">
              <template v-if="row.id === editingId">
                <button
                  class="btn small primary"
                  :disabled="saving || !isDraftValid()"
                  @click="saveRow"
                >
                  {{ saving ? 'Saving…' : 'Save' }}
                </button>
                <button class="btn small" :disabled="saving" @click="cancelEdit">Cancel</button>
              </template>
              <template v-else>
                <button class="btn small" @click="startEdit(row)">Edit</button>
                <button class="btn small danger" @click="openDelete(row)">Delete</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Add-new row ───────────────────────────────────── -->
    <form class="add-row" @submit.prevent="addCity">
      <input
        v-model="newCity.name"
        type="text"
        placeholder="City name…"
        maxlength="80"
        :disabled="adding"
      />
      <input
        v-model.number="newCity.parm1"
        type="number"
        step="any"
        placeholder="parm1"
        :disabled="adding"
      />
      <input
        v-model.number="newCity.parm2"
        type="number"
        step="any"
        placeholder="parm2"
        :disabled="adding"
      />
      <input
        v-model.number="newCity.parm3"
        type="number"
        step="any"
        placeholder="parm3"
        :disabled="adding"
      />
      <button class="btn primary" type="submit" :disabled="adding || !newCity.name.trim()">
        {{ adding ? 'Adding…' : 'Add city' }}
      </button>
    </form>

    <!-- ── Delete confirmation ───────────────────────────── -->
    <div v-if="showDeleteDialog" class="modal-backdrop" @click.self="showDeleteDialog = false">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
        <h3 id="delete-title">Delete city</h3>
        <p>
          Are you sure you want to delete <strong>{{ deleteTarget?.name }}</strong>?
          This cannot be undone.
        </p>
        <div class="modal-actions">
          <button class="btn" :disabled="deleting" @click="showDeleteDialog = false">Cancel</button>
          <button class="btn danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page {
  width: min(1000px, 96vw);
}

.topbar {
  text-align: center;
  margin-bottom: 1.25rem;
}
.topbar h1 {
  margin: 0;
  font-size: 1.9rem;
  letter-spacing: 0.02em;
  color: #14532d;
}
.tagline {
  color: #64748b;
  margin: 0.25rem 0 0;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  margin: 0 0 0.6rem;
}

.table-wrap {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(22, 101, 52, 0.07);
  overflow-x: auto;
}
.placeholder {
  color: #64748b;
  padding: 2.5rem 0;
  text-align: center;
}

table.cities {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}
.cities th,
.cities td {
  padding: 0.6rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
}
.cities thead th {
  background: #f0fdf4;
  color: #166534;
  font-weight: 700;
  cursor: pointer;
  user-select: none;
}
.cities thead th:hover {
  background: #dcfce7;
}
.cities tbody tr:hover {
  background: #f8fafc;
}
.cities tbody tr.editing {
  background: #f0fdf4;
}
.cities tbody tr:last-child td {
  border-bottom: none;
}

.col-id {
  width: 60px;
  color: #64748b;
}
.col-name {
  font-weight: 600;
  color: #1f2937;
}
.col-param {
  color: #334155;
}
.col-actions {
  text-align: right;
  width: 170px;
}

.cell-input {
  width: 100%;
  min-width: 90px;
  padding: 0.35rem 0.5rem;
  border: 1px solid #86efac;
  border-radius: 6px;
  font: inherit;
  background: #fff;
}
.cell-input:focus {
  outline: 2px solid #86efac;
  border-color: #16a34a;
}

/* ── Buttons ── */
.btn {
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  color: #334155;
}
.btn:hover:not(:disabled) {
  background: #f8fafc;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn.small {
  padding: 0.32rem 0.7rem;
  font-size: 0.85rem;
  margin-left: 0.35rem;
}
.btn.primary {
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
}
.btn.primary:hover:not(:disabled) {
  background: #15803d;
  border-color: #15803d;
}
.btn.danger {
  background: #dc2626;
  border-color: #dc2626;
  color: #fff;
}
.btn.danger:hover:not(:disabled) {
  background: #b91c1c;
  border-color: #b91c1c;
}

/* ── Add-row form ── */
.add-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr auto;
  gap: 0.6rem;
  margin-top: 1.1rem;
  padding: 0.9rem 1rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(22, 101, 52, 0.07);
}
.add-row input {
  width: 100%;
  padding: 0.55rem 0.7rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
  background: #fff;
}
.add-row input:focus {
  outline: 2px solid #86efac;
  border-color: #16a34a;
}
@media (max-width: 720px) {
  .add-row {
    grid-template-columns: 1fr;
  }
}

/* ── Banners ── */
.banner {
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  font-size: 0.9rem;
  margin: 0 0 0.9rem;
}
.banner.error {
  background: #fee2e2;
  color: #991b1b;
}
.banner.ok {
  background: #dcfce7;
  color: #166534;
}

/* ── Modal ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 42, 26, 0.45);
  display: grid;
  place-items: center;
  padding: 1rem;
  z-index: 50;
}
.modal {
  width: min(420px, 96vw);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(22, 101, 52, 0.07);
  padding: 1.4rem;
}
.modal h3 {
  margin: 0 0 0.4rem;
  color: #14532d;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 1.25rem;
}
</style>
