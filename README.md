# Limit Order Book

A FastAPI matching engine with a React/Vite market terminal.

## Local development

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` when you need to change backend settings. Copy `frontend/.env.example` to `frontend/.env` to point the browser at a separately hosted API.

## Deployment

1. Deploy the backend from the repository root using the `Dockerfile`, or run `uvicorn main:app --host 0.0.0.0 --port $PORT` on a Python service.
2. Set `DATABASE_URL` to a managed PostgreSQL connection string. The bundled SQLite default is for local development and is not suitable for multiple instances or ephemeral disks.
3. Set `CORS_ORIGINS` to the exact frontend origin(s), separated by commas. Do not use `*` with credentials enabled.
4. Build and deploy `frontend` as a static Vite site with `npm run build`. Set `VITE_API_URL` and `VITE_WS_URL` at build time when the API is hosted separately.
5. Ensure the hosting platform supports WebSocket connections and persistent or managed storage for uploaded datasets.

The backend listens on `0.0.0.0` in the container and honors the platform-provided `PORT` value.

## Production considerations

The admin replay, dataset upload, reset, and scenario endpoints currently have no authentication. Put them behind an authenticated gateway or add application authentication before exposing this service publicly. Also add migrations, rate limits, structured logging, and monitoring before handling real users or funds.
