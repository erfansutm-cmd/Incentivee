/**
 * Front-end configuration.
 *
 * The main API URL is read from the Vite env var VITE_API_BASE_URL
 * (see frontend/.env.development and frontend/.env.production).
 *
 * - Empty string  -> same origin (default; works behind the Vite dev
 *                    proxy and behind nginx in production).
 * - A full URL    -> the API is called directly on that host.
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

/** Well-known endpoints. */
export const endpoints = {
  health: `${API_BASE_URL}/api/health`,
  cities: `${API_BASE_URL}/api/cities`,
  city: (id) => `${API_BASE_URL}/api/cities/${id}`,
}
