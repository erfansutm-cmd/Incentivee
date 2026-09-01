# Incentive — FastAPI + Vue 3 with Docker Compose

Starter project:

- **Backend** — [FastAPI](https://fastapi.tiangolo.com/) served by Uvicorn (dev) / Gunicorn with Uvicorn workers (prod)
- **Frontend** — [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/) dev server (dev) / built static files served by **nginx** (prod)
- Two Compose files: one for development with hot reload, one for production

```
.
├── docker-compose.yml          # development
├── docker-compose.prod.yml     # production
├── .env.example
├── backend/
│   ├── Dockerfile              # multi-stage: target `dev` or `prod`
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app factory
│       ├── schemas.py          # request/response models (City, CityParams, …)
│       ├── core/config.py      # settings (env vars) — app name, API_PREFIX, CORS
│       └── api/routes/
│           ├── health.py
│           └── gatekeeper.py   # GateKeeper city API (mock in-memory store)
└── frontend/
    ├── Dockerfile              # multi-stage: `dev` (Vite) / `build` / `prod` (nginx)
    ├── nginx.conf              # SPA + /api reverse proxy
    ├── vite.config.js          # dev server + /api proxy
    ├── .env.development        # main API URL for dev
    ├── .env.production         # main API URL for production build
    └── src/
        ├── config.js           # reads VITE_API_BASE_URL, exports endpoints
        ├── api.js              # fetch wrapper for the city endpoints
        ├── router/index.js     # vue-router (/gatekeeper, alias /GateKeeper)
        ├── App.vue
        └── views/
            └── GateKeeper.vue  # cities + parm1/2/3 + rename/delete/copy dialogs
```

## Prerequisites

- Docker Engine 24+ and the Docker Compose plugin (`docker compose`)

## Development

```bash
docker compose up --build
```

| Service  | URL                            |
| -------- | ------------------------------ |
| Frontend | http://localhost:5173          |
| API      | http://localhost:8000          |
| API docs | http://localhost:8000/api/docs |

- Backend code in `backend/` is mounted into the container and Uvicorn auto-reloads on changes.
- Frontend code in `frontend/` is mounted and Vite provides hot module replacement (HMR).
- The Vite dev server proxies `/api/*` to the `backend` container, so the frontend calls relative URLs.

Stop with `Ctrl+C`, then `docker compose down`.

## Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

| Service          | URL                                |
| ---------------- | ---------------------------------- |
| App (nginx)      | http://localhost:8080             |
| API (via nginx)  | http://localhost:8080/api/health  |
| API docs         | http://localhost:8080/api/docs    |

- The Vue app is compiled to static files (`npm run build`) and served by nginx.
- nginx reverse-proxies `/api/*` to the FastAPI container on the internal Docker network — the backend publishes no host port.
- FastAPI runs under Gunicorn with 4 Uvicorn workers (adjust worker count in `backend/Dockerfile`).

Stop with:

```bash
docker compose -f docker-compose.prod.yml down
```

## Configuration — the "main URL"

The project name and the API's base URL are both centralized so you can change them later in one place.

**Project / app name:**

- Container and image names live in the two Compose files (`incentive-backend`, `incentive-frontend`).
- The API's own app name (`app_name`) defaults to `"Incentive"` in `backend/app/core/config.py`, overridable with the env var `APP_NAME`.

**API base path (backend side):**

All API routes are mounted under `api_prefix` in `backend/app/core/config.py` (default `/api`). Change it there or with the env var to version/move the whole API:

```bash
API_PREFIX=/api/v1 docker compose up --build
```

The health endpoint then moves to `/api/v1/health`, docs to `/api/v1/docs`, etc.

**API URL the frontend calls:**

Set in `frontend/src/config.js` from the Vite env var `VITE_API_BASE_URL`:

- `VITE_API_BASE_URL=` (empty, default) → **same origin**. Requests go to the Vite dev proxy (dev) or nginx (prod), which forward `/api` to the backend. This is the Docker setup.
- `VITE_API_BASE_URL=https://api.example.com` → the frontend calls that host directly. Set it in `frontend/.env.production` for production builds (Vite bakes env vars in at build time) and add the origin to `cors_origins` in the backend config.

## GateKeeper

Open **http://localhost:5173/GateKeeper** (or `/gatekeeper` — the app uses `vue-router` with history mode; `/` redirects to it).

The UI (`frontend/src/views/GateKeeper.vue`):

- **Select or add cities** — city list on the left, with an "Add a city…" input.
- **Rename a city** — hover a city and click the ✎ icon to edit the name inline (Enter or ✓ to save, Esc or ✕ to cancel).
- **Delete a city** — hover a city and click the 🗑 icon; a confirmation popup asks before deleting.
- **Edit parameters** — each city has `parm1`, `parm2`, `parm3` (placeholders for the real parameters — rename them in `backend/app/schemas.py` and the `PARAMS`/`PARAM_LABELS` arrays in `GateKeeper.vue`).
- **Save** — writes the values with `PUT /api/cities/{id}`; the Save button enables only when there are unsaved changes.
- **Copy from another city** — opens a confirmation modal showing a preview of the source city's values vs the current values; the values are applied only after confirmation, and you still review and Save them.
- Styled with a **green theme** — all colors are CSS variables (`--green-*`) at the top of `GateKeeper.vue`.

### API (mock data for now)

Data is an in-memory list seeded in `backend/app/api/routes/gatekeeper.py`. Restarting the container resets it; swap that store for a real database later — the endpoint shapes don't change.

| Method | Path                 | Purpose                                       | Body                                    |
| ------ | -------------------- | --------------------------------------------- | --------------------------------------- |
| GET    | `/api/cities`        | List all cities + parameters                  | —                                       |
| POST   | `/api/cities`        | Add a city (params default to 0)              | `{"name": "Rome"}`                      |
| PUT    | `/api/cities/{id}`   | Partial update — rename and/or parameters     | `{"name": "Roma"}` and/or `{"parm1":…}` |
| DELETE | `/api/cities/{id}`   | Delete a city                                 | —                                       |

Errors: `404` unknown city, `422` invalid body. Interactive docs: `/api/docs`.

> Note: renaming keeps the city's `id` stable (the id is derived from the original name), so bookmarks and references don't break.

## Where to start coding

- Add API routes in `backend/app/api/routes/` and include them in `backend/app/main.py`.
- Replace the mock store in `backend/app/api/routes/gatekeeper.py` with a database.
- Rename `parm1/parm2/parm3` in `backend/app/schemas.py` and `frontend/src/views/GateKeeper.vue`.
- Add pages in `frontend/src/views/` and register them in `frontend/src/router/index.js`.
- Add new endpoint URLs to the `endpoints` object in `frontend/src/config.js` and call them through `frontend/src/api.js`.
