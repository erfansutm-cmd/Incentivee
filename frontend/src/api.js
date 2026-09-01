/**
 * Thin API helper for GateKeeper.
 *
 * Talks to the (currently mock) backend. When the backend gains a
 * real database these calls stay exactly the same.
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
    const data = await request(endpoints.cities)
    return data.cities
  },

  /** POST /api/cities -> created city */
  async createCity(name) {
    return request(endpoints.cities, {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
  },

  /**
   * PUT /api/cities/{id} -> updated city.
   * Partial update: pass { name } to rename, { parm1, parm2, parm3 }
   * to save parameters, or both together.
   */
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
