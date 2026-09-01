/**
 * Thin API client for the cities CRUD endpoints.
 *
 * GET    /api/cities        -> list of cities
 * POST   /api/cities        -> create
 * PUT    /api/cities/{id}   -> update (partial)
 * DELETE /api/cities/{id}   -> delete
 */
import { endpoints } from './config'

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  // 204 No Content (DELETE) — nothing to parse
  if (res.status === 204) return null

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  /** GET /api/cities -> [{ id, name, parm1, parm2, parm3 }] */
  async fetchCities() {
    return request(endpoints.cities)
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

  /** GET /api/cities/schema -> { table, columns: [...] } — actual DB columns */
  async fetchCitySchema() {
    return request(`${endpoints.cities}/schema`)
  },

  /** DELETE /api/cities/{id} */
  async deleteCity(id) {
    await request(endpoints.city(id), { method: 'DELETE' })
  },
}
