# CS:GO Market Index Tracker

A full-stack application for tracking custom CS:GO item price indices. Create custom collections of CS:GO items and monitor their combined market value across multiple marketplaces.

## Prerequisites

- Python 3.13+
- Node.js 18+ and npm
- uv (Python package manager) - https://github.com/astral-sh/uv
- CSMarket API Key - https://csmarketapi.com/

## Getting Started

### Backend Setup

```bash
cd backend

# Copy environment file
cp .env.example .env

# Edit .env and add your CSMarket API key
# CSMARKET_API_KEY=your_actual_api_key_here

# Install dependencies
uv sync

# Run the server
uv run uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000

API documentation at http://localhost:8000/docs

### Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

Frontend runs at http://localhost:8080

## Environment Configuration

Create `backend/.env` with:

```
CSMARKET_API_KEY=your_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./index.db
CORS_ORIGINS=http://localhost:8080
```

## First Run

On first startup, the backend will:
- Create the database
- Sync all CS:GO items from CSMarketAPI
- Generate pre-built indices

This takes 1-2 minutes.

## Development Commands

### Backend

```bash
# Run server with auto-reload
uv run uvicorn app.main:app --reload --port 8000

# Sync dependencies
uv sync
```

### Frontend

```bash
# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint
npm run lint
```

## Project Structure

```
IndexTracker/
├── backend/          # FastAPI backend
│   └── app/
│       ├── models/   # Database models
│       ├── routers/  # API endpoints
│       ├── services/ # Business logic
│       └── schemas/  # Pydantic schemas
└── frontend/         # React frontend
    └── src/
        ├── components/
        ├── pages/
        └── hooks/
```

## Troubleshooting

**Backend won't start:**
- Verify CSMarket API key in `.env`
- Check Python 3.13+ is installed
- Run `uv sync` to reinstall dependencies

**Frontend won't start:**
- Check Node.js 18+ is installed
- Delete `node_modules` and run `npm install`
- Verify port 8080 is available

**CORS errors:**
- Check `CORS_ORIGINS` in `backend/.env` includes `http://localhost:8080`
- Restart backend after changing `.env`
