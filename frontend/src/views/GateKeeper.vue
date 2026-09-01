<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { api } from '../api'

const PARAMS = ['parm1', 'parm2', 'parm3']
const PARAM_LABELS = { parm1: 'parm1', parm2: 'parm2', parm3: 'parm3' }

// ── State ──────────────────────────────────────────────────────
const cities = ref([])
const selectedId = ref(null)
const form = ref({ parm1: 0, parm2: 0, parm3: 0 })
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const newCityName = ref('')
const adding = ref(false)

// Rename
const editingId = ref(null)
const editName = ref('')
const renaming = ref(false)
const renameInput = ref(null)

// Delete
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Copy dialog
const showCopyDialog = ref(false)
const copySourceId = ref('')

// ── Derived ────────────────────────────────────────────────────
const selectedCity = computed(
  () => cities.value.find((c) => c.id === selectedId.value) ?? null,
)

// The form is "dirty" if its values differ from the stored city
const isDirty = computed(() => {
  const c = selectedCity.value
  if (!c) return false
  return PARAMS.some((p) => Number(form.value[p]) !== Number(c[p]))
})

// Cities selectable as copy source = every city except the current one
const copySources = computed(() =>
  cities.value.filter((c) => c.id !== selectedId.value),
)

const copySource = computed(
  () => cities.value.find((c) => c.id === copySourceId.value) ?? null,
)

// ── Data loading / selecting ───────────────────────────────────
async function loadCities(selectId = null) {
  loading.value = true
  error.value = ''
  try {
    cities.value = await api.fetchCities()
    if (selectId && cities.value.some((c) => c.id === selectId)) {
      selectedId.value = selectId
    } else if (cities.value.length) {
      selectedId.value = cities.value[0].id
    } else {
      selectedId.value = null
    }
  } catch (e) {
    error.value = `Failed to load cities: ${e.message}`
  } finally {
    loading.value = false
  }
}

function selectCity(id) {
  if (editingId.value) cancelRename()
  selectedId.value = id
  notice.value = ''
}

// Keep the form in sync when the selected city changes
watch(selectedCity, (city) => {
  if (city) {
    form.value = { parm1: city.parm1, parm2: city.parm2, parm3: city.parm3 }
  } else {
    form.value = { parm1: 0, parm2: 0, parm3: 0 }
  }
})

// Focus the rename input when editing starts
watch(editingId, async (id) => {
  if (id) {
    await nextTick()
    renameInput.value?.focus()
    renameInput.value?.select()
  }
})

// ── Add a city ─────────────────────────────────────────────────
async function addCity() {
  const name = newCityName.value.trim()
  if (!name) return
  adding.value = true
  error.value = ''
  notice.value = ''
  try {
    const created = await api.createCity(name)
    cities.value.push(created)
    selectedId.value = created.id
    newCityName.value = ''
    notice.value = `City "${created.name}" added.`
  } catch (e) {
    error.value = `Failed to add city: ${e.message}`
  } finally {
    adding.value = false
  }
}

// ── Rename a city ──────────────────────────────────────────────
function startRename(city) {
  editingId.value = city.id
  editName.value = city.name
}

function cancelRename() {
  editingId.value = null
  editName.value = ''
}

async function confirmRename() {
  const city = cities.value.find((c) => c.id === editingId.value)
  if (!city) return cancelRename()
  const name = editName.value.trim()
  if (!name || name === city.name) return cancelRename()

  renaming.value = true
  error.value = ''
  notice.value = ''
  try {
    const updated = await api.updateCity(city.id, { name })
    city.name = updated.name // mutate in place -> selection/form untouched
    notice.value = `City renamed to "${updated.name}".`
    editingId.value = null
  } catch (e) {
    error.value = `Failed to rename: ${e.message}`
  } finally {
    renaming.value = false
  }
}

// ── Delete a city ──────────────────────────────────────────────
function openDelete(city) {
  deleteTarget.value = city
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
    notice.value = `City "${target.name}" deleted.`
    showDeleteDialog.value = false
    deleteTarget.value = null
    if (selectedId.value === target.id) {
      selectedId.value = cities.value[0]?.id ?? null
    }
  } catch (e) {
    error.value = `Failed to delete: ${e.message}`
    showDeleteDialog.value = false
  } finally {
    deleting.value = false
  }
}

// ── Save parameters ────────────────────────────────────────────
async function save() {
  if (!selectedCity.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const params = {
      parm1: Number(form.value.parm1) || 0,
      parm2: Number(form.value.parm2) || 0,
      parm3: Number(form.value.parm3) || 0,
    }
    const updated = await api.updateCity(selectedCity.value.id, params)
    Object.assign(selectedCity.value, updated)
    form.value = { parm1: updated.parm1, parm2: updated.parm2, parm3: updated.parm3 }
    notice.value = `Saved parameters for "${updated.name}".`
  } catch (e) {
    error.value = `Failed to save: ${e.message}`
  } finally {
    saving.value = false
  }
}

// ── Copy values from another city ──────────────────────────────
function openCopyDialog() {
  copySourceId.value = copySources.value[0]?.id ?? ''
  showCopyDialog.value = true
}

function confirmCopy() {
  if (!copySource.value) return
  // Apply to the form only — the user still reviews and presses Save.
  form.value = {
    parm1: copySource.value.parm1,
    parm2: copySource.value.parm2,
    parm3: copySource.value.parm3,
  }
  showCopyDialog.value = false
  notice.value = `Values copied from "${copySource.value.name}" — review and Save.`
}

onMounted(() => loadCities())
</script>

<template>
  <section class="gatekeeper">
    <header class="topbar">
      <h1>GateKeeper</h1>
      <p class="tagline">City parameters — parm1, parm2, parm3</p>
    </header>

    <p v-if="error" class="banner error">{{ error }}</p>

    <div class="layout">
      <!-- ── Left: city list ─────────────────────────────── -->
      <aside class="city-panel">
        <div class="panel-head">
          <h2>Cities</h2>
        </div>

        <ul class="city-list">
          <li
            v-for="city in cities"
            :key="city.id"
            :class="['city-item', { active: city.id === selectedId }]"
            @click="selectCity(city.id)"
          >
            <!-- Inline rename -->
            <template v-if="editingId === city.id">
              <input
                ref="renameInput"
                v-model="editName"
                class="rename-input"
                type="text"
                maxlength="80"
                @click.stop
                @keydown.enter="confirmRename"
                @keydown.esc="cancelRename"
              />
              <span class="item-actions always">
                <button
                  class="icon-btn"
                  title="Save name"
                  :disabled="renaming"
                  @click.stop="confirmRename"
                >✓</button>
                <button class="icon-btn" title="Cancel" @click.stop="cancelRename">✕</button>
              </span>
            </template>

            <!-- Normal row -->
            <template v-else>
              <span class="city-name">{{ city.name }}</span>
              <span class="item-actions">
                <button class="icon-btn" title="Rename city" @click.stop="startRename(city)">✎</button>
                <button class="icon-btn danger" title="Delete city" @click.stop="openDelete(city)">🗑</button>
              </span>
            </template>
          </li>
        </ul>

        <form class="add-form" @submit.prevent="addCity">
          <input
            v-model="newCityName"
            type="text"
            placeholder="Add a city…"
            maxlength="80"
            :disabled="adding"
          />
          <button type="submit" class="btn small" :disabled="adding || !newCityName.trim()">
            {{ adding ? 'Adding…' : 'Add' }}
          </button>
        </form>
      </aside>

      <!-- ── Right: parameters ──────────────────────────── -->
      <main class="params-panel">
        <div v-if="loading" class="placeholder">Loading cities…</div>

        <div v-else-if="!selectedCity" class="placeholder">
          No city selected. Add a city to get started.
        </div>

        <div v-else>
          <div class="params-head">
            <h2>{{ selectedCity.name }}</h2>
            <button class="btn secondary" :disabled="!copySources.length" @click="openCopyDialog">
              Copy from another city…
            </button>
          </div>

          <div class="fields">
            <div v-for="p in PARAMS" :key="p" class="field">
              <label :for="p">{{ PARAM_LABELS[p] }}</label>
              <input
                :id="p"
                v-model.number="form[p]"
                type="number"
                step="any"
              />
            </div>
          </div>

          <p v-if="notice" class="banner ok">{{ notice }}</p>

          <div class="actions">
            <button class="btn primary" :disabled="saving || !isDirty" @click="save">
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
            <span v-if="!isDirty" class="muted">All changes saved</span>
            <span v-else class="muted dirty">Unsaved changes</span>
          </div>
        </div>
      </main>
    </div>

    <!-- ── Copy confirmation modal ─────────────────────── -->
    <div v-if="showCopyDialog" class="modal-backdrop" @click.self="showCopyDialog = false">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="copy-title">
        <h3 id="copy-title">Copy parameters from another city</h3>

        <p class="muted">
          This will copy the values below into <strong>{{ selectedCity?.name }}</strong>.
          You can still review them before saving.
        </p>

        <label class="select-label" for="copy-source">Source city</label>
        <select id="copy-source" v-model="copySourceId">
          <option v-for="c in copySources" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>

        <table v-if="copySource" class="preview">
          <tbody>
            <tr v-for="p in PARAMS" :key="p">
              <th>{{ PARAM_LABELS[p] }}</th>
              <td>{{ copySource[p] }}</td>
              <td class="arrow">→</td>
              <td class="muted">{{ form[p] }}</td>
            </tr>
          </tbody>
        </table>
        <p class="muted legend">
          source value → current value of {{ selectedCity?.name }}
        </p>

        <div class="modal-actions">
          <button class="btn" @click="showCopyDialog = false">Cancel</button>
          <button class="btn primary" :disabled="!copySource" @click="confirmCopy">
            Copy values
          </button>
        </div>
      </div>
    </div>

    <!-- ── Delete confirmation modal ───────────────────── -->
    <div v-if="showDeleteDialog" class="modal-backdrop" @click.self="showDeleteDialog = false">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
        <h3 id="delete-title">Delete city</h3>
        <p>
          Are you sure you want to delete
          <strong>{{ deleteTarget?.name }}</strong>?
          Its parameters will be removed. This cannot be undone.
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
.gatekeeper {
  width: min(860px, 94vw);

  /* Green theme — tweak these values to restyle the whole UI */
  --green-600: #16a34a;
  --green-700: #15803d;
  --green-800: #166534;
  --green-100: #dcfce7;
  --green-50: #f0fdf4;
  --green-200: #bbf7d0;
  --green-focus: #86efac;
}

.topbar {
  text-align: center;
  margin-bottom: 1.25rem;
}
.topbar h1 {
  margin: 0;
  font-size: 1.9rem;
  letter-spacing: 0.02em;
  color: var(--green-800);
}
.tagline {
  color: #64748b;
  margin: 0.25rem 0 0;
}

.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 1.25rem;
  align-items: start;
}
@media (max-width: 640px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

.city-panel,
.params-panel,
.modal {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(22, 101, 52, 0.07);
}

.city-panel {
  padding: 1rem;
}
.panel-head h2,
.params-head h2 {
  margin: 0;
  font-size: 1.05rem;
  color: #14532d;
}

.city-list {
  list-style: none;
  margin: 0.75rem 0;
  padding: 0;
  max-height: 340px;
  overflow-y: auto;
}
.city-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  color: #334155;
}
.city-item:hover {
  background: var(--green-50);
}
.city-item.active {
  background: var(--green-600);
  color: #fff;
}
.city-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-actions {
  display: flex;
  gap: 0.2rem;
  opacity: 0;
  transition: opacity 0.15s ease;
  flex-shrink: 0;
}
.item-actions.always {
  opacity: 1;
}
.city-item:hover .item-actions,
.city-item:focus-within .item-actions {
  opacity: 1;
}
.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1;
  padding: 0.25rem 0.4rem;
  border-radius: 6px;
  color: inherit;
}
.icon-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.08);
}
.city-item.active .icon-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.25);
}
.icon-btn.danger:hover:not(:disabled) {
  background: #fee2e2;
  color: #991b1b;
}
.city-item.active .icon-btn.danger:hover:not(:disabled) {
  background: #fee2e2;
  color: #991b1b;
}
.rename-input {
  flex: 1;
  min-width: 0;
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--green-600);
  border-radius: 6px;
  font: inherit;
}

.add-form {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.add-form input {
  flex: 1;
  min-width: 0;
}

.params-panel {
  padding: 1.25rem;
  min-height: 260px;
}
.placeholder {
  color: #64748b;
  padding: 2rem 0;
  text-align: center;
}

.params-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.fields {
  display: grid;
  gap: 0.9rem;
}
.field {
  display: grid;
  grid-template-columns: 110px 1fr;
  align-items: center;
  gap: 0.75rem;
}
.field label {
  font-weight: 600;
  color: #475569;
}

input,
select {
  width: 100%;
  padding: 0.55rem 0.7rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
  background: #fff;
}
input:focus,
select:focus {
  outline: 2px solid var(--green-focus);
  border-color: var(--green-600);
}

.btn {
  padding: 0.55rem 1.1rem;
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
  padding: 0.4rem 0.8rem;
}
.btn.primary {
  background: var(--green-600);
  border-color: var(--green-600);
  color: #fff;
}
.btn.primary:hover:not(:disabled) {
  background: var(--green-700);
  border-color: var(--green-700);
}
.btn.secondary {
  background: var(--green-50);
  border-color: var(--green-200);
  color: var(--green-800);
}
.btn.secondary:hover:not(:disabled) {
  background: var(--green-100);
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

.actions {
  margin-top: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.muted {
  color: #64748b;
  font-size: 0.9rem;
}
.muted.dirty {
  color: #b45309;
  font-weight: 600;
}

.banner {
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  font-size: 0.9rem;
  margin: 0 0 1rem;
}
.banner.error {
  background: #fee2e2;
  color: #991b1b;
}
.banner.ok {
  background: var(--green-100);
  color: var(--green-800);
  margin: 1rem 0 0;
}

/* ── Modals ── */
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
  width: min(440px, 96vw);
  padding: 1.4rem;
}
.modal h3 {
  margin: 0 0 0.4rem;
  color: #14532d;
}
.select-label {
  display: block;
  font-weight: 600;
  font-size: 0.9rem;
  margin: 0.9rem 0 0.35rem;
  color: #475569;
}
.preview {
  width: 100%;
  margin-top: 1rem;
  border-collapse: collapse;
}
.preview th,
.preview td {
  text-align: left;
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}
.preview th {
  color: #475569;
}
.preview .arrow {
  color: #94a3b8;
  width: 24px;
  text-align: center;
}
.legend {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 1.25rem;
}
</style>
