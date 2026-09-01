# Incentive — FastAPI + Vue 3 with Docker Compose

Empty starter project:

- **Backend** — [FastAPI](https://fastapi.tiangolo.com/) served by Uvicorn (dev) / Gunicorn with Uvicorn workers (prod), with **MySQL** wired in via SQLAlchemy.
- **Frontend** — [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/) dev server (dev) / built static files served by **nginx** (prod)
- Two Compose files: one for development with hot reload, one for production

```
.
├── docker-compose.yml          # development
├── docker-compose.prod.yml     # production
├── .env / .env.example         # settings (DB credentials, etc.)
├── backend/
│   ├── Dockerfile              # multi-stage: target `dev` or `prod`
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app factory
│       ├── db.py               # SQLAlchemy engine/session (MySQL)
│       ├── core/config.py      # settings (env vars) — app name, DB, API_PREFIX, CORS
│       └── api/routes/health.py
└── frontend/
    ├── Dockerfile              # multi-stage: `dev` (Vite) / `build` / `prod` (nginx)
    ├── nginx.conf              # SPA + /api reverse proxy
    ├── vite.config.js          # dev server + /api proxy
    ├── .env.development        # main API URL for dev
    ├── .env.production         # main API URL for production build
    └── src/                    # Vue app (App.vue shows a backend health check)
```

## Prerequisites

- Docker Engine 24+ and the Docker Compose plugin (`docker compose`)
- A reachable MySQL server (settings below)

## Database (MySQL)

The backend connects to MySQL via SQLAlchemy + PyMySQL. Settings come from environment variables in the root **`.env`** file (copy `.env.example` → `.env` and fill in; `.env` is git-ignored):

| Variable      | Value             |
| ------------- | ----------------- |
| `DB_HOST`     | `172.21.41.75`    |
| `DB_PORT`     | `3306`            |
| `DB_USER`     | `erfan.mohamadi`  |
| `DB_PASSWORD` | (set in `.env`)   |
| `DB_NAME`     | `incentive`       |

They build the connection URL in `backend/app/core/config.py` (`settings.database_url`); the engine/session live in `backend/app/database.py` — inject a session into a route with `db: Session = Depends(get_db)`.

- **Check connectivity:** `GET /api/health/db` returns `{database, user, server_version}`, or `503` with the connection error if MySQL is unreachable (fails fast after 5s).
- **Create the database once** on the MySQL server (the connector doesn't create it):
  `CREATE DATABASE incentive CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
- **If MySQL runs on the Windows host itself** (not the LAN IP), set `DB_HOST=host.docker.internal` in `.env` — Compose already adds the `host-gateway` mapping.
- Passwords with special characters are URL-encoded automatically when the connection URL is built.

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
- Frontend code in `frontend/` is mounted and Vite provides hot module replacement (HMR); newly added npm dependencies sync automatically on restart.
- The Vite dev server proxies `/api/*` to the `backend` container, so the frontend calls relative URLs.

Stop with `Ctrl+C`, then `docker compose down` (add `-v` to also clear the `node_modules` volume).

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

Stop with `docker compose -f docker-compose.prod.yml down`.

## Configuration

- **App name:** `app_name` in `backend/app/core/config.py` (env `APP_NAME`); image/container names live in the Compose files (`incentive-backend`, `incentive-frontend`).
- **API base path:** all routes mount under `api_prefix` (default `/api`; env `API_PREFIX`, e.g. `/api/v1`).
- **Frontend API URL:** `VITE_API_BASE_URL` in `frontend/.env.development` / `.env.production` — empty = same origin (default Docker setup), or a full URL to call a remote API directly (also allow that origin in `cors_origins`).

## Where to start coding

- Add API routes in `backend/app/api/routes/` and include them in `backend/app/main.py`; use `Depends(get_db)` to query MySQL.
- Define ORM models on `app.db.Base` and create tables (e.g. `Base.metadata.create_all(engine)` or Alembic) once your schema is known.
- Build UI in `frontend/src/`; add endpoint URLs to the `endpoints` object in `frontend/src/config.js`.
