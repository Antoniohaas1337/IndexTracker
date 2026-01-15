# Quick Start Guide

## Prerequisites

1. Add your CSMarketAPI key to `backend/.env`:
   ```env
   CSMARKET_API_KEY=your_api_key_here
   ```

## Starting the Application

### Option 1: Run Both (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open: **http://localhost:5173**

### Option 2: Backend Only (API Testing)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Then open: **http://localhost:8000/docs**

## What You'll See

1. **Backend starts** (Terminal 1):
   - Syncs items from CSMarketAPI (30-60 seconds)
   - Generates 7 prebuilt indices
   - API ready at http://localhost:8000

2. **Frontend starts** (Terminal 2):
   - Loads in ~2 seconds
   - Opens at http://localhost:5173
   - Shows dashboard with indices

## First Steps

1. **View Pre-built Indices**: The dashboard shows 7 prebuilt indices (Rifles, Knives, etc.)

2. **Calculate a Price**: Click "Calculate Price" on any index to fetch current market values

3. **Create Custom Index**:
   - Click "Create Index" in the navigation
   - Search for items (e.g., "AWP", "AK-47")
   - Select items to track
   - Choose markets
   - Create!

4. **View Charts**: Click "View Chart" to see price history (after calculating prices a few times)

## Troubleshooting

**Backend won't start?**
- Check your API key in `backend/.env`
- Make sure Python 3.11+ is installed
- Try: `pip install -r backend/requirements.txt`

**Frontend won't start?**
- Make sure you're in the `frontend` directory
- Try: `npm install` first

**Can't see any data?**
- Wait for backend item sync to complete (~60 seconds)
- Check backend terminal for errors

## Features

✅ **Dashboard** - View all your indices
✅ **Create Custom Indices** - Track specific items
✅ **Price Calculation** - Sum of min prices across markets
✅ **Price History** - View charts over time
✅ **Pre-built Indices** - 7 categories ready to use
✅ **Dark Theme** - Modern CS:GO-inspired design

Enjoy tracking CS:GO market indices! 🎮📈
