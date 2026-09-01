<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from './api'

// ── State ──────────────────────────────────────────────────────
const columns = ref([])        // real DB columns from GET /api/cities/schema
const primaryKey = ref('id')   // real primary-key column name
const rows = ref([])           // rows as returned by the API (all columns)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

// Inline editing: one row at a time, with a local draft
const editingId = ref(null)
const draft = ref({})

// New-row form
const newRow = ref({})
const adding = ref(false)

// Delete confirmation
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Sorting
const sortKey = ref(null)
const sortDir = ref(1) // 1 = asc, -1 = desc

// ── Column helpers ─────────────────────────────────────────────
// Everything comes from the real DB schema — nothing is hardcoded.
const nameColumn = computed(() => columns.value.find((c) => c.name === 'name'))

const numericColumns = computed(() =>
  columns.value.filter(
    (c) => c.name !== primaryKey.value && c.name !== 'name' && isNumericType(c.type),
  ),
)

const displayColumns = computed(() =>
  columns.value.filter((c) => c.name !== primaryKey.value),
)

function isNumericType(type) {
  return /int|float|double|real|decimal|numeric/i.test(String(type ?? ''))
}

function isEditable(col) {
  return col.name === 'name' || isNumericType(col.type)
}

function shortType(type) {
  return String(type ?? '').split('(')[0].toLowerCase()
}

function formatCell(value) {
  if (value === null || value === undefined) return '—'
  return String(value)
}

// ── Derived ────────────────────────────────────────────────────
const sortedRows = computed(() => {
  const key = sortKey.value
  if (!key) return rows.value
  return [...rows.value].sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sortDir.value
    return String(av ?? '').localeCompare(String(bv ?? '')) * sortDir.value
  })
})

function buildEmptyForm() {
  const form = {}
  if (nameColumn.value) form.name = ''
  for (const c of numericColumns.value) form[c.name] = ''
  return form
}

function isNewRowValid() {
  if (nameColumn.value && newRow.value.name.trim().length > 0) return true
  // No name column (or empty name): valid only if some numeric value was typed.
  return numericColumns.value.some((c) => String(newRow.value[c.name]).trim() !== '')
}

function isDraftValid() {
  if (nameColumn.value) return draft.value.name.trim().length > 0
  return true
}

// ── Load ───────────────────────────────────────────────────────
async function loadCities() {
  loading.value = true
  error.value = ''
  notice.value = ''

  // 1) The real table structure, straight from the database.
  let schema = null
  try {
    schema = await api.fetchCitySchema()
  } catch (e) {
    error.value = `Failed to load table schema: ${e.message}`
  }

  // 2) The rows — all columns, all real values.
  try {
    const data = await api.fetchCities()
    rows.value = data

    if (schema && schema.columns && schema.columns.length) {
      columns.value = schema.columns
      primaryKey.value =
        schema.primary_key || columns.value.find((c) => c.is_pk)?.name || 'id'
    } else {
      // Fallback: derive columns from the row keys (everything read-only).
      deriveColumnsFromRows(data)
      if (!error.value) {
        error.value = 'Could not read the table schema — showing raw columns from the rows.'
      }
    }

    if (!sortKey.value || !columns.value.some((c) => c.name === sortKey.value)) {
      sortKey.value = primaryKey.value ?? columns.value[0]?.name ?? null
    }
  } catch (e) {
    if (error.value) error.value += ` Failed to load cities: ${e.message}`
    else error.value = `Failed to load cities: ${e.message}`
  } finally {
    loading.value = false
  }
}

function deriveColumnsFromRows(data) {
  const keys = data.length ? Object.keys(data[0]) : []
  columns.value = keys.map((name) => ({
    name,
    type: 'text',
    nullable: true,
    is_pk: name === 'id',
    default: null,
  }))
  primaryKey.value = columns.value.find((c) => c.is_pk)?.name ?? 'id'
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
async function addRow() {
  if (!isNewRowValid()) return

  const payload = {}
  if (nameColumn.value) {
    const name = newRow.value.name.trim()
    if (name) payload.name = name
  }
  // Only send numeric columns the user actually typed into — columns
  // left blank keep their real DB default instead of a fake 0.
  for (const c of numericColumns.value) {
    const raw = String(newRow.value[c.name]).trim()
    if (raw !== '') payload[c.name] = Number(raw) || 0
  }

  if (Object.keys(payload).length === 0) return

  adding.value = true
  error.value = ''
  notice.value = ''
  try {
    const created = await api.createCity(payload)
    rows.value.push(created)
    newRow.value = buildEmptyForm()
    notice.value = nameColumn.value && created.name ? `"${created.name}" added.` : 'Row added.'
  } catch (e) {
    error.value = `Failed to add row: ${e.message}`
  } finally {
    adding.value = false
  }
}

// ── Start / cancel editing a row ───────────────────────────────
function startEdit(row) {
  if (editingId.value !== null) return
  editingId.value = row[primaryKey.value]
  const d = {}
  if (nameColumn.value) d.name = row.name
  for (const c of numericColumns.value) d[c.name] = row[c.name]
  draft.value = d
}

function cancelEdit() {
  editingId.value = null
  draft.value = {}
}

// ── Save a single row ──────────────────────────────────────────
async function saveRow() {
  const id = editingId.value
  if (id === null || id === undefined || !isDraftValid()) return

  const original = rows.value.find((r) => r[primaryKey.value] === id)
  if (!original) return cancelEdit()

  // Only send fields that actually changed
  const patch = {}
  if (nameColumn.value) {
    const name = draft.value.name.trim()
    if (name !== original.name) patch.name = name
  }
  for (const c of numericColumns.value) {
    const raw = String(draft.value[c.name]).trim()
    const value = raw === '' ? null : Number(raw) || 0
    const current = original[c.name] === null || original[c.name] === undefined ? null : Number(original[c.name])
    if (value !== current) patch[c.name] = value
  }

  if (Object.keys(patch).length === 0) return cancelEdit()

  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const updated = await api.updateCity(id, patch)
    const idx = rows.value.findIndex((r) => r[primaryKey.value] === id)
    if (idx !== -1) rows.value[idx] = updated
    notice.value = nameColumn.value && updated.name ? `"${updated.name}" saved.` : 'Row saved.'
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
  const id = target[primaryKey.value]
  deleting.value = true
  error.value = ''
  notice.value = ''
  try {
    await api.deleteCity(id)
    rows.value = rows.value.filter((r) => r[primaryKey.value] !== id)
    if (editingId.value === id) cancelEdit()
    notice.value = `Row "${target[nameColumn.value?.name ?? primaryKey.value] ?? id}" deleted.`
    showDeleteDialog.value = false
    deleteTarget.value = null
  } catch (e) {
    error.value = `Failed to delete: ${e.message}`
    showDeleteDialog.value = false
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  newRow.value = buildEmptyForm()
  loadCities()
})
</script>

<template>
  <section class="page">
    <header class="topbar">
      <h1>Cities</h1>
      <p class="tagline">
        Live data from the <code>cities</code> table — columns and values are read straight
        from the database{{ columns.length ? ` (${columns.length} columns)` : '' }}.
      </p>
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
      <div v-else-if="!columns.length" class="placeholder">
        Could not load the table — check the database connection.
      </div>
      <div v-else-if="!rows.length" class="placeholder">
        The table has no rows yet. Use the form below to add one.
      </div>

      <table v-else class="cities">
        <thead>
          <tr>
            <th
              v-for="c in displayColumns"
              :key="c.name"
              :class="c.name === 'name' ? 'col-name' : 'col-param'"
              :title="c.type ? `type: ${c.type}` : ''"
              @click="toggleSort(c.name)"
            >
              {{ c.name }}{{ sortArrow(c.name) }}
              <span class="col-type">{{ shortType(c.type) }}</span>
            </th>
            <th class="col-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in sortedRows"
            :key="row[primaryKey]"
            :class="{ editing: row[primaryKey] === editingId }"
          >
            <td
              v-for="c in displayColumns"
              :key="c.name"
              :class="c.name === 'name' ? 'col-name' : 'col-param'"
            >
              <template v-if="row[primaryKey] === editingId && isEditable(c)">
                <input
                  v-if="c.name === 'name'"
                  v-model="draft.name"
                  class="cell-input"
                  type="text"
                  maxlength="80"
                  placeholder="Name"
                  @keydown.enter="saveRow"
                  @keydown.esc="cancelEdit"
                />
                <input
                  v-else
                  v-model="draft[c.name]"
                  class="cell-input"
                  type="number"
                  step="any"
                  @keydown.enter="saveRow"
                  @keydown.esc="cancelEdit"
                />
              </template>
              <template v-else>{{ formatCell(row[c.name]) }}</template>
            </td>

            <td class="col-actions">
              <template v-if="row[primaryKey] === editingId">
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
    <form v-if="columns.length" class="add-row" @submit.prevent="addRow">
      <input
        v-if="nameColumn"
        v-model="newRow.name"
        type="text"
        placeholder="Name…"
        maxlength="80"
        :disabled="adding"
      />
      <input
        v-for="c in numericColumns"
        :key="c.name"
        v-model="newRow[c.name]"
        type="number"
        step="any"
        :placeholder="c.name"
        :disabled="adding"
      />
      <button class="btn primary" type="submit" :disabled="adding || !isNewRowValid()">
        {{ adding ? 'Adding…' : 'Add row' }}
      </button>
    </form>

    <!-- ── Delete confirmation ───────────────────────────── -->
    <div v-if="showDeleteDialog" class="modal-backdrop" @click.self="showDeleteDialog = false">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
        <h3 id="delete-title">Delete row</h3>
        <p>
          Are you sure you want to delete
          <strong>{{ deleteTarget?.[nameColumn?.name ?? primaryKey] }}</strong>?
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
.tagline code {
  background: #f1f5f9;
  border-radius: 4px;
  padding: 0.1rem 0.35rem;
  font-size: 0.85em;
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

.col-type {
  display: block;
  font-size: 0.7rem;
  font-weight: 500;
  color: #94a3b8;
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
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 1.1rem;
  padding: 0.9rem 1rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(22, 101, 52, 0.07);
}
.add-row input {
  flex: 1 1 140px;
  min-width: 110px;
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
.add-row .btn {
  flex: 0 0 auto;
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
