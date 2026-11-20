# FlowForge AI

## Docker

Copy `.env.example` to `.env`, replace the placeholder password and JWT secret, then run `docker compose up --build`.

The frontend is available at http://localhost:5173 and the API at http://localhost:8000. The backend waits for PostgreSQL, runs `alembic upgrade head`, and starts Uvicorn. PostgreSQL data persists in the `postgres_data` volume.

Useful commands: `docker compose ps`, `docker compose logs -f backend`, `docker compose exec backend alembic current`, and `docker compose down`.

The images exclude `.env`, virtual environments, SQLite databases, and secrets. Existing SQLite data is not migrated automatically; use `backend/scripts/migrate_sqlite_to_postgres.py` explicitly with source and target URLs after PostgreSQL is running.

## Cloud deployment

The production layout uses Vercel for the React frontend, Render for the Dockerized FastAPI backend, and a Render PostgreSQL database. `render.yaml` is a Blueprint starting point; review names and approve secret values in the Render dashboard.

### Render backend

Create the Blueprint (or create a Docker web service manually) with the repository root `backend`, Dockerfile `backend/Dockerfile`, and health check path `/health`. Render supplies the PostgreSQL connection string through `DATABASE_URL`. Set these environment variables in the Render service:

- `DATABASE_URL` — Render PostgreSQL internal connection string.
- `JWT_SECRET` — long random signing secret; mark it secret.
- `GEMINI_API_KEY` — Gemini key; mark it secret.
- `FRONTEND_ORIGIN` — the exact Vercel origin, for example `https://flowforge-ai.vercel.app`. Multiple origins may be comma-separated.

The container runs `alembic upgrade head` before Uvicorn and listens on Render's `PORT`. Do not use `create_tables()` as a production migration process beyond the existing compatibility behavior. Check `https://your-api.onrender.com/health` after deployment; it should return `{"status":"healthy"}` without configuration details.

### Vercel frontend

Import the repository into Vercel with root directory `frontend`, framework preset Vite, build command `npm run build`, and output directory `dist`. Set the build-time variable `VITE_API_BASE_URL` to the public Render API URL, such as `https://flowforge-api.onrender.com`. Vite variables are embedded during the build and are not runtime secrets; never place JWT secrets or database credentials in them. `vercel.json` keeps React SPA routes working after refresh.

After both services are deployed, register a user, log in, create and execute a workflow, refresh the browser, and verify dashboard metrics and execution history. Confirm browser requests use the Render API URL and that the API health endpoint is reachable.
