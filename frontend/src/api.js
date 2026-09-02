/**
 * Thin API client for the cities CRUD endpoints.
 *
 * GET    /api/cities        -> list of cities (all real DB columns/values)
 * GET    /api/cities/schema -> real table structure
 * POST   /api/cities        -> create
 * PUT    /api/cities/{id}   -> update (partial)
 * DELETE /api/cities/{id}   -> delete
 *
 * Every call either resolves with data or rejects with a descriptive
 * Error message that the UI can show directly to the user.
 */
import { endpoints } from './config'

const REQUEST_TIMEOUT_MS = 15000

/** Human-friendly messages for bare HTTP statuses (no JSON body). */
const STATUS_TEXT = {
  400: 'Bad request — the server rejected the data sent.',
  404: 'Not found — the city may have been deleted already.',
  409: 'Conflict — a city with that name already exists.',
  422: 'Invalid input — check the values you entered.',
  500: 'Server error — the database may be missing a table or column.',
  502: 'Bad gateway — the backend is not reachable through the proxy.',
  503: 'The database is unreachable. Check that the DB server is running and the connection settings are correct.',
  504: 'The backend timed out while waiting for the database.',
}

async function request(url, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let res
  try {
    res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    })
  } catch (e) {
    const reason = e.name === 'AbortError' ? 'timed out' : `failed: ${e.message}`
    throw new Error(`Cannot reach the server (${url}) — request ${reason}.`)
  } finally {
    clearTimeout(timer)
  }

  // 204 No Content (DELETE) — nothing to parse
  if (res.status === 204) return null

  if (!res.ok) {
    let detail = null
    try {
      const body = await res.json()
      if (body && typeof body.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail ?? STATUS_TEXT[res.status] ?? `Request failed (HTTP ${res.status}).`)
  }

  try {
    return await res.json()
  } catch {
    throw new Error('The server returned an invalid (non-JSON) response.')
  }
}

export const api = {
  /** GET /api/cities -> [{ id, name, ...all real columns }] */
  async fetchCities() {
    return request(endpoints.cities)
  },

  /** GET /api/cities/schema -> { table, primary_key, columns: [...] } */
  async fetchCitySchema() {
    return request(`${endpoints.cities}/schema`)
  },

  /** POST /api/cities -> created city */
  async createCity(payload) {
    return request(endpoints.cities, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /** PUT /api/cities/{id} -> updated city (partial update) */
  async updateCity(id, patch) {
    return request(endpoints.city(id), {
      method: 'PUT',
      body: JSON.stringify(patch),
    })
  },

  /** DELETE /api/cities/{id} */
  async deleteCity(id) {
    await request(endpoints.city(id), { method: 'DELETE' })
  },
}
