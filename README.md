# Incentive — Cities (FastAPI + Vue 3 with Docker Compose)

A simple **Cities** CRUD app, 100% driven by the database:

- **Backend** — [FastAPI](https://fastapi.tiangolo.com/) served by Uvicorn (dev) / Gunicorn with Uvicorn workers (prod), with **MySQL** wired in via SQLAlchemy. The `cities` table is created on startup **only if it doesn't exist**; an existing table is never altered.
- **Frontend** — [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/): one page showing the **real `cities` table** — whatever columns and values the database actually contains (e.g. `id`, `name`, `parm1`, `parm2`, `parm3`, …). There is no mock data and no hardcoded columns anywhere: the table schema is read from the DB and the UI renders it dynamically. You can edit any `name`/numeric cell inline, add rows, and delete rows.
- Two Compose files: one for development with hot reload, one for production.

```
.
├── docker-compose.yml          # development
├── docker-compose.prod.yml     # production
├── .env / .env.example         # settings (DB credentials, etc.)
├── backend/
│   ├── Dockerfile              # multi-stage: target `dev` or `prod`
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app factory (+ table creation on startup)
│       ├── database.py         # SQLAlchemy engine/session
│       ├── schemas.py          # Pydantic request schemas (responses = raw DB columns)
│       ├── core/config.py      # settings (env vars) — app name, DB, API_PREFIX, CORS
│       └── api/routes/
│           ├── health.py       # GET /api/health, GET /api/health/db
│           └── cities.py       # cities CRUD (reflects the real table structure)
└── frontend/
    ├── Dockerfile              # multi-stage: `dev` (Vite) / `build` / `prod` (nginx)
    ├── nginx.conf              # SPA + /api reverse proxy
    ├── vite.config.js          # dev server + /api proxy
    ├── .env.development        # main API URL for dev
    ├── .env.production         # main API URL for production build
    └── src/
        ├── App.vue             # dynamic cities table UI
        ├── api.js              # API client (fetchCities / fetchCitySchema / createCity / updateCity / deleteCity)
        └── config.js           # endpoint URLs
```

## Cities API

All routes are mounted under the API prefix (default `/api`).

| Method | Path                | Description                              |
| ------ | ------------------- | ---------------------------------------- |
| GET    | `/api/cities`       | List all cities — every real column, every real value |
| GET    | `/api/cities/schema`| Describe the actual `cities` table (columns, types, PK) |
| POST   | `/api/cities`       | Create a city (`name` required when the table has a `name` column; any other existing columns accepted) |
| GET    | `/api/cities/{id}`  | Get one city                             |
| PUT    | `/api/cities/{id}`  | Update a city — partial update of any subset of the real columns |
| DELETE | `/api/cities/{id}`  | Delete a city                            |

City objects are plain dicts of the table's real columns — e.g. if your table
looks like `id / name / parm1 / parm2 / parm3`:

```json
{ "id": 1, "name": "Tehran", "parm1": 10.5, "parm2": 20, "parm3": 0 }
```

- The schema is introspected from the DB; **create/update reject columns that
  don't really exist** with `400` (the response lists the existing columns).
- `name` is unique where a `name` column exists → duplicate names return `409`.
- Missing city returns `404`; empty/too-long names return `422`.

Interactive docs: `http://localhost:8000/api/docs`

## Database (MySQL)

The backend connects to MySQL via SQLAlchemy + PyMySQL. Settings come from environment variables in the root **`.env`** file (copy `.env.example` → `.env` and fill in; `.env` is git-ignored):

| Variable      | Value             |
| ------------- | ----------------- |
| `DB_HOST`     | `172.21.41.75`    |
| `DB_PORT`     | `3306`            |
| `DB_USER`     | `erfan.mohamadi`  |
| `DB_PASSWORD` | (set in `.env`)   |
| `DB_NAME`     | `incentive`       |

- The database is the **single source of truth**. On startup the backend only
  creates the `cities` table if it doesn't exist (a minimal `id` + `name`
  table); it **never alters an existing table** and never invents columns.
- To see exactly what your `cities` table contains, open
  `GET /api/cities/schema` — it lists the actual columns, types and primary key.
- **No MySQL handy?** Point the backend at SQLite for local development:
  `DATABASE_URL=sqlite:///./backend/dev.db` (takes precedence over `DB_*`).
- If MySQL runs on the Windows host itself (not the LAN IP), set `DB_HOST=host.docker.internal` in `.env`.

## Development

```bash
docker compose up --build
```

| Service  | URL                            |
| -------- | ------------------------------ |
| Frontend | http://localhost:5173          |
| API      | http://localhost:8000          |
| API docs | http://localhost:8000/api/docs |
| DB check | http://localhost:8000/api/health/db |

- Backend code in `backend/` is mounted into the container and Uvicorn auto-reloads on changes.
- Frontend code in `frontend/` is mounted and Vite provides HMR. The Vite dev server proxies `/api/*` to the `backend` container, so the frontend calls relative URLs.
- When running the frontend **without Docker**, point the proxy at the local backend: `VITE_API_PROXY_TARGET=http://localhost:8000 npm run dev` (default target is the Compose service name `backend`).

### Quick local run without Docker

```bash
# backend (SQLite, no MySQL needed)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./dev.db uvicorn app.main:app --reload

# frontend (another terminal)
cd frontend
npm install
VITE_API_PROXY_TARGET=http://localhost:8000 npm run dev
```

Stop with `Ctrl+C`, then `docker compose down` (add `-v` to also clear the `node_modules` volume).

## Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

| Service          | URL                                |
| ---------------- | ---------------------------------- |
| App (nginx)      | http://localhost:8080             |
| API (via nginx)  | http://localhost:8080/api/cities  |
| API docs         | http://localhost:8080/api/docs    |

- The Vue app is compiled to static files (`npm run build`) and served by nginx.
- nginx reverse-proxies `/api/*` to the FastAPI container on the internal Docker network — the backend publishes no host port.
- FastAPI runs under Gunicorn with 4 Uvicorn workers (adjust worker count in `backend/Dockerfile`).

## Configuration

- **App name:** `app_name` in `backend/app/core/config.py` (env `APP_NAME`).
- **API base path:** all routes mount under `api_prefix` (default `/api`; env `API_PREFIX`, e.g. `/api/v1`).
- **Full DB override:** `DATABASE_URL` (e.g. `sqlite:///./dev.db` or any SQLAlchemy URL) beats the `DB_*` variables.
- **Frontend API URL:** `VITE_API_BASE_URL` in `frontend/.env.development` / `frontend/.env.production` — empty = same origin (default Docker setup), or a full URL to call a remote API directly (also allow that origin in `cors_origins`).

## Where to start coding

- Add API routes in `backend/app/api/routes/` and include them in `backend/app/main.py`; use `Depends(get_db)` to query the database.
- There are no hardcoded ORM models for city data — `backend/app/api/routes/cities.py` reflects the real `cities` table and serves its columns as-is.
- Build UI in `frontend/src/`; add endpoint URLs to the `endpoints` object in `frontend/src/config.js`.
