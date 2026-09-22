# Limit Order Book

This project is a trading-system simulation based on a limit order book, which is the core data structure used by modern financial exchanges. A limit order book keeps track of all pending buy and sell orders by price level and matches them when a valid trade can occur. It is the foundation behind order execution, price discovery, liquidity, and market microstructure.

This repository combines a Python backend with a React frontend to model how orders flow through a matching engine, how prices are formed, and how trade data can be analyzed in a market-like environment.

## What this project includes

- Matching engine for buy and sell orders
- Order book state management for bids and asks
- Trade execution and analytics
- Replay and simulation capabilities using market data
- Simple strategy and trader logic
- A lightweight frontend market terminal

## Project structure

- `engine/` — matching logic, order book, strategies, replay engine
- `main.py` — FastAPI application entry point
- `state.py` and `database.py` — backend state and persistence
- `frontend/` — React + Vite user interface
- `datasets/` — sample LOBSTER-style market data

## Why it matters

A limit order book matters because it determines which orders get executed first and at what price. The system prioritizes orders by price and then by time, which makes it a realistic model of how exchanges operate. By studying this structure, you can better understand real-world market behavior, liquidity, spread dynamics, and execution logic.

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
