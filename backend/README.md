# CS:GO Market Index Tracker - Backend

FastAPI backend for tracking CS:GO item price indices using the CSMarketAPI.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Edit `.env` and add your CSMarketAPI key:
```env
CSMARKET_API_KEY=your_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./index.db
CORS_ORIGINS=http://localhost:5173
```

## Running

Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Items
- `GET /api/items` - List items (paginated, filterable)
- `GET /api/items/search?q=AK-47` - Search items
- `POST /api/items/sync` - Sync items from API

### Indices
- `GET /api/indices` - List all indices
- `POST /api/indices` - Create custom index
- `GET /api/indices/{id}` - Get index details
- `PUT /api/indices/{id}` - Update index
- `DELETE /api/indices/{id}` - Delete index

### Prebuilt Indices
- `GET /api/prebuilt` - List available categories
- `GET /api/prebuilt/{category}` - Get prebuilt index
- `POST /api/prebuilt/generate` - Generate all prebuilt indices

### Prices
- `POST /api/prices/{id}/calculate` - Calculate index price
- `GET /api/prices/{id}/history` - Get price history
- `GET /api/prices/{id}/latest` - Get latest price

### Markets
- `GET /api/markets` - List available markets

## Database

The application uses SQLite for data storage:
- **File**: `index.db` (created automatically)
- **Tables**: items, indices, index_items, price_points

## Architecture

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings
├── database.py          # SQLAlchemy setup
├── models/              # Database models
├── schemas/             # Pydantic schemas
├── services/            # Business logic
└── routers/             # API endpoints
```

## Key Features

- **Async/Await**: Full async support for better performance
- **Type Safety**: Pydantic schemas and SQLAlchemy models
- **Auto Docs**: Interactive API documentation
- **CORS Enabled**: Ready for frontend integration
- **Min Price Algorithm**: All calculations use minimum prices only
