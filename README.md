# CS:GO Market Index Tracker

Track custom CS:GO item price indices using the [CSMarketAPI](https://csmarketapi.com).

## What is this?

A web application that lets you create and monitor custom "indices" (collections) of CS:GO items and track their aggregate market value over time.

**Perfect for:**
- Tracking the value of your favorite skin collections
- Monitoring market trends across item categories
- Creating investment portfolios of CS:GO items
- Analyzing price movements of specific weapon types

## Key Features

- **Custom Indices**: Create your own collections from any CS:GO items
- **Pre-built Indices**: Ready-made indices for Rifles, Knives, Cases, Stickers, etc.
- **Historical Tracking**: Store and visualize price history over time
- **Multi-Market Support**: Query prices from Steam, Skinport, CSFloat, and more
- **Min Price Focus**: All calculations use minimum prices across markets
- **Modern UI**: Clean, responsive interface built with React
- **Fast Search**: Find items quickly with autocomplete search
- **Real-time Calculation**: Calculate index values on demand

## How It Works

This tool uses the CSMarketAPI to:

1. **Fetch CS:GO item data** - Get item names, types, categories, and metadata
2. **Query market prices** - Fetch current prices from multiple marketplaces
3. **Calculate index values** - Sum the minimum prices of selected items
4. **Store historical data** - Track price changes over time

**Important**: All price calculations use **MINIMUM PRICE ONLY** (not average, median, or max). Index values are calculated as the **sum of minimum prices** for all items in the collection.

## Architecture

- **Backend**: Python FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + TypeScript + Vite + Recharts (coming soon)
- **API**: CSMarketAPI Python library v2.0.0
- **Database**: SQLite (file-based, zero configuration)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- CSMarketAPI key ([get one here](https://csmarketapi.com))

### Backend Setup

1. **Navigate to backend directory**:
```bash
cd backend
```

2. **Create and activate virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Create environment file**:
```bash
cp .env.example .env
```

5. **Edit `.env` and add your API key**:
```env
CSMARKET_API_KEY=your_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./index.db
CORS_ORIGINS=http://localhost:5173
```

6. **Run the backend**:
```bash
uvicorn app.main:app --reload
```

The API will start at http://localhost:8000

### Frontend Setup

The frontend is already set up! Dependencies are installed.

```bash
cd frontend
npm run dev
```

The frontend will start at http://localhost:5173

**Open two terminals** and run backend + frontend together for the full application.

## Using the API

### Interactive Documentation

Visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

### Example Requests

**Get all items (paginated)**:
```bash
curl http://localhost:8000/api/items?page=1&limit=10
```

**Search for items**:
```bash
curl http://localhost:8000/api/items/search?q=AK-47
```

**Get prebuilt indices**:
```bash
curl http://localhost:8000/api/prebuilt
```

**Get Knives index**:
```bash
curl http://localhost:8000/api/prebuilt/KNIVES
```

**Create custom index**:
```bash
curl -X POST http://localhost:8000/api/indices \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My AWP Collection",
    "description": "Favorite AWP skins",
    "type": "CUSTOM",
    "selected_markets": ["STEAMCOMMUNITY", "SKINPORT"],
    "currency": "USD",
    "item_ids": [1, 2, 3]
  }'
```

**Calculate index price**:
```bash
curl -X POST http://localhost:8000/api/prices/{index_id}/calculate
```

**Get price history**:
```bash
curl http://localhost:8000/api/prices/{index_id}/history
```

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── routers/        # API endpoints
│   │   ├── config.py       # Settings
│   │   ├── database.py     # Database setup
│   │   └── main.py         # FastAPI app
│   ├── requirements.txt
│   └── README.md
│
├── frontend/               # React frontend (coming soon)
│   ├── src/
│   ├── package.json
│   └── README.md
│
├── docs/                   # Documentation
├── README.md              # This file
└── .gitignore
```

## Pre-built Indices

The application automatically generates these indices on startup:

1. **Rifles Index** - All rifle skins (AK-47, M4A4, AWP, etc.)
2. **Pistols Index** - All pistol skins (Glock, USP-S, Desert Eagle, etc.)
3. **SMGs Index** - All SMG skins (MP7, MP9, P90, etc.)
4. **Knives Index** - All knife skins (Karambit, Butterfly, Bayonet, etc.)
5. **Gloves Index** - All glove skins
6. **Cases Index** - All weapon cases
7. **Stickers Index** - All stickers

## Index Calculation Method

**Algorithm**: Sum of minimum prices

For each index:
1. Fetch the latest listings for all items from selected markets
2. Extract the **minimum price** from each item's listings across all markets
3. **Sum** all minimum prices
4. Store the total as the index value

**Example**:
- Item A min price: $10.50
- Item B min price: $25.00
- Item C min price: $5.25
- **Index Value: $40.75**

This "portfolio approach" tracks the total value of item collections over time.

## Technology Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - ORM with async support
- **SQLite** - File-based database (no server required)
- **Pydantic** - Data validation and settings
- **CSMarketAPI** - Official CS:GO market data API

### Frontend (Coming Soon)
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Recharts** - Chart library for price visualization
- **TailwindCSS** - Utility-first CSS framework
- **TanStack Query** - Data fetching and caching

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database

The SQLite database (`index.db`) is created automatically on first run.

**Tables**:
- `items` - CS:GO item catalog
- `indices` - Custom and prebuilt indices
- `index_items` - Many-to-many relationship
- `price_points` - Historical price data

### Running Tests (Coming Soon)

```bash
cd backend
pytest
```

## Future Features

This project is designed with extensibility in mind:

- [ ] **Sales History Integration** - Track actual transaction data
- [ ] **Weighted Indices** - Weight by trading volume or market cap
- [ ] **Real-time Updates** - WebSocket support for live price updates
- [ ] **Portfolio Tracking** - Import and track your Steam inventory
- [ ] **Alerts** - Price threshold notifications
- [ ] **Export Data** - CSV/JSON export of price history
- [ ] **Comparison Tools** - Compare multiple indices
- [ ] **Mobile App** - Native mobile applications

## Use Cases

### 1. Portfolio Tracking
Create an index of items you own and track their total value over time.

### 2. Market Research
Compare "Knives Index" vs "Rifles Index" to understand market trends.

### 3. Investment Analysis
Track specific item categories to identify investment opportunities.

### 4. Content Creation
Generate data and charts for CS:GO market analysis videos/articles.

## Contributing

This is an open-source example project demonstrating CSMarketAPI capabilities. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Disclaimer

This tool is for informational purposes only. Price data is sourced from CSMarketAPI and may not reflect real-time market values. This is not financial or investment advice.

## Links

- [CSMarketAPI Documentation](https://csmarketapi.com)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [React Documentation](https://react.dev)

## Support

For issues or questions:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review the plan file for architecture details

---

**Built with ❤️ using CSMarketAPI**
