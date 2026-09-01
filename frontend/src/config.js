/**
 * Front-end configuration.
 *
 * The main API URL is read from the Vite env var VITE_API_BASE_URL
 * (see frontend/.env.development and frontend/.env.production).
 *
 * - Empty string  -> same origin (default; works behind the Vite dev
 *                    proxy and behind nginx in production).
 * - A full URL    -> the API is called directly on that host, e.g.
 *                    VITE_API_BASE_URL=https://api.example.com
 *                    (remember to allow that origin in the backend
 *                     CORS settings).
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

/** Well-known endpoints (add your own here as the app grows). */
export const endpoints = {
  health: `${API_BASE_URL}/api/health`,
  cities: `${API_BASE_URL}/api/cities`,
  city: (id) => `${API_BASE_URL}/api/cities/${id}`,
}
