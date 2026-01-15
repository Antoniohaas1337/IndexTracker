# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CS:GO Market Index Tracker - A full-stack application for tracking custom CS:GO item price indices. The backend (FastAPI + Python) fetches prices from CSMarketAPI and calculates index values using a **portfolio approach** (summing minimum prices across markets). The frontend (React + TypeScript + shadcn/ui) provides a modern dashboard for creating and monitoring custom item collections.

## Repository Structure

```
IndexTracker/
├── backend/          # FastAPI Python backend
│   └── app/
│       ├── models/   # SQLAlchemy database models
│       ├── schemas/  # Pydantic request/response schemas
│       ├── routers/  # API endpoints
│       └── services/ # Business logic layer
└── frontend/         # React TypeScript frontend
    └── src/
        ├── components/ # React components (UI + feature)
        ├── pages/      # Route pages
        ├── hooks/      # Custom React hooks
        ├── data/       # Mock data (temporary)
        └── types/      # TypeScript type definitions
```

## Development Commands

### Backend (from `backend/` directory)

```bash
# Run development server
uv run uvicorn app.main:app --reload --port 8000

# Install/sync dependencies
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate
```

### Frontend (from `frontend/` directory)

```bash
# Run development server (port 8080)
npm run dev

# Install dependencies
npm install

# Build for production
npm run build

# Run tests
npm test

# Run tests in watch mode
npm test:watch

# Lint
npm run lint
```

## Backend Architecture

See `backend/CLAUDE.md` for detailed backend documentation. Key points:

### Core Algorithm: Portfolio-Based Index Calculation

The system's fundamental algorithm (`app/services/price_service.py:calculate_index_price`):
1. Load all items in an index
2. Fetch **minimum price** for each item across selected markets (STEAMCOMMUNITY, SKINPORT, etc.)
3. **Sum all minimum prices** to get the index value
4. Store as PricePoint with timestamp

**This is NOT an average** - it represents the total cost to acquire all items in the collection.

### Database Models

- **Item**: CS:GO items with metadata (type, weapon, exterior, category)
- **Index**: Collections of items (CUSTOM or PREBUILT types)
- **IndexItem**: Many-to-many join table between indices and items
- **PricePoint**: Historical price snapshots for indices

### Service Layer

- **CSMarketService**: Async wrapper for CSMarketAPI with rate limiting
- **IndexService**: CRUD operations and prebuilt index generation
- **PriceService**: Core price calculation logic
- **ItemService**: Item syncing from CSMarketAPI

### API Endpoints

All routers use dependency injection for database sessions via `get_db()`:
- `/items/` - Item management and syncing
- `/indices/` - Custom index CRUD
- `/prebuilt/` - Prebuilt indices listing
- `/prices/` - Price calculation and history
- `/markets/` - Available markets info

### Environment Variables

Required (see `backend/.env.example`):
- `CSMARKET_API_KEY`: API key for CSMarketAPI
- `DATABASE_URL`: SQLAlchemy async database URL (default: `sqlite+aiosqlite:///./index.db`)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (default: `http://localhost:5173`)

## Frontend Architecture

### Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **React Router** for routing
- **TanStack Query** for data fetching (configured but currently using mock data)
- **shadcn/ui** components built on Radix UI
- **Tailwind CSS** for styling
- **Vitest** for testing

### Component Organization

```
components/
├── ui/              # shadcn/ui components (Alert, Button, Card, etc.)
├── layout/          # Layout components (AppSidebar, MainLayout)
├── chart/           # Chart components (PriceChart, ChartModal)
├── dashboard/       # Dashboard-specific components
├── index-form/      # Index creation/editing form components
└── overview/        # Overview page components
```

### Pages and Routing

- `/` - Dashboard: Overview of all indices with mini-charts
- `/manage` - ManageIndices: List and manage custom indices
- `/create` - CreateIndex: Create new custom index
- `/edit/:id` - EditIndex: Edit existing custom index

### State Management

Currently using:
- **Local React state** with `useState` for component state
- **Custom hooks** (`useIndices`) for data operations
- **Mock data** from `data/mockData.ts` (will be replaced with API calls)

The app is structured to easily swap mock data hooks with real API calls using TanStack Query.

### Custom Hooks

- `useIndices`: Manages index CRUD operations (currently mock, ready for API integration)
- `use-mobile`: Responsive design helper
- `use-toast`: Toast notification system

### Type System

All types defined in `src/types/index.ts`:
- `MarketIndex`: Index data structure
- `Item`: CS:GO item definition
- `PricePoint`: Price history point
- `ChartData`: Chart data response
- `CreateIndexPayload`: Index creation payload
- `TimeRange`: Chart time range options

### Styling Conventions

- Uses **Tailwind CSS** utility classes
- Theme system via `next-themes` for dark/light mode support
- Component variants via `class-variance-authority`
- Global styles in `src/index.css`

## Integration Points

### API Integration (Planned)

Frontend expects backend API at `http://localhost:8000` (configurable). The current `useIndices` hook structure mirrors the backend API shape:

```typescript
// GET /indices/ -> fetch indices
// GET /indices/{id} -> get index by id
// POST /indices/ -> create index
// PUT /indices/{id} -> update index
// DELETE /indices/{id} -> delete index
// POST /prices/calculate/{id} -> calculate price
```

### CORS Configuration

Backend CORS is configured via `CORS_ORIGINS` environment variable. For development:
```bash
CORS_ORIGINS=http://localhost:8080,http://localhost:5173
```

Frontend dev server runs on port **8080** (configured in `frontend/vite.config.ts`).

## Important Implementation Notes

### Backend

- All price calculations use **minimum prices only** across selected markets
- Index values are **sums**, not averages or weighted values
- Prebuilt indices auto-regenerate on startup
- Database uses UTC timestamps
- SQLAlchemy 2.0 async API throughout

### Frontend

- Currently uses **mock data** - real API integration pending
- TanStack Query is configured but not yet used for data fetching
- All UI components are from shadcn/ui (self-contained, customizable)
- TypeScript strict mode enabled
- Path alias `@/` maps to `src/`

## Common Development Patterns

### Adding a New Backend Endpoint

1. Define Pydantic schemas in `app/schemas/`
2. Add business logic to appropriate service in `app/services/`
3. Create router endpoint in `app/routers/`
4. Register router in `app/main.py`

### Adding a New Frontend Page

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Update navigation in `src/components/layout/AppSidebar.tsx`
4. Add TypeScript types to `src/types/index.ts` if needed

### Creating a New shadcn/ui Component

```bash
cd frontend
npx shadcn@latest add [component-name]
```

This adds the component to `src/components/ui/`.

## Testing

### Backend
Currently no test framework configured.

### Frontend
- **Vitest** configured with React Testing Library
- Run tests: `npm test` or `npm test:watch`
- Test setup in `src/test/setup.ts`

## Known Limitations

1. Frontend currently uses **mock data** - API integration incomplete
2. No authentication/authorization implemented
3. Backend has no test coverage
4. No CI/CD pipeline configured
5. Database migrations not managed (uses `create_all()` on startup)
