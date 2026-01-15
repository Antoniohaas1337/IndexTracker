# Getting Started with CS:GO Market Index Tracker

## Quick Setup Guide (5 minutes)

### Step 1: Get Your CSMarketAPI Key

1. Visit [https://csmarketapi.com](https://csmarketapi.com)
2. Sign up for an account
3. Generate an API key
4. Copy the API key (you'll need it in Step 3)

### Step 2: Install Dependencies

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

All dependencies should install successfully. If you see any errors, make sure you're using Python 3.11+.

### Step 3: Configure Environment

1. Open the file `backend/.env` in a text editor
2. Replace `your_api_key_here` with your actual CSMarketAPI key:

```env
CSMARKET_API_KEY=your_actual_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./index.db
CORS_ORIGINS=http://localhost:5173
```

3. Save the file

### Step 4: Start the Backend

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Starting CS:GO Market Index Tracker API...
INFO:     Initializing database...
INFO:     Syncing items from CSMarketAPI...
INFO:     Items sync completed: 5000+ items
INFO:     Generating prebuilt indices...
INFO:     Prebuilt indices generated: 7 categories
INFO:     Startup complete!
```

**Note**: The first startup takes 30-60 seconds to sync all CS:GO items.

### Step 5: Test the API

Open your browser and visit:

**📚 Interactive Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

Or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Get first 5 items
curl http://localhost:8000/api/items?limit=5

# Search for AK-47 skins
curl http://localhost:8000/api/items/search?q=AK-47

# Get all prebuilt indices
curl http://localhost:8000/api/prebuilt
```

## Your First Index

### Using the API Documentation

1. Go to [http://localhost:8000/docs](http://localhost:8000/docs)
2. Expand **Prebuilt Indices** → `GET /api/prebuilt`
3. Click **"Try it out"** → **"Execute"**
4. You'll see 7 prebuilt indices listed

### Get the Knives Index

In the docs, expand **Prebuilt Indices** → `GET /api/prebuilt/{category}`:

1. Click **"Try it out"**
2. Enter `KNIVES` in the category field
3. Click **"Execute"**

You'll see the Knives Index with all knife skins and their item count.

### Calculate the Price

Now let's calculate the current total value:

1. Note the `id` from the Knives Index response (probably `1`)
2. Expand **Prices** → `POST /api/prices/{index_id}/calculate`
3. Click **"Try it out"**
4. Enter the index ID (e.g., `1`)
5. Click **"Execute"**

The API will:
- Fetch min prices for all knife skins from Steam Community Market
- Sum all the prices
- Return the total value

This might take 10-30 seconds depending on the number of items.

### View Price History

After calculating prices a few times, view the history:

1. Expand **Prices** → `GET /api/prices/{index_id}/history`
2. Click **"Try it out"**
3. Enter the index ID
4. Click **"Execute"**

You'll see all historical price points with timestamps.

## Create a Custom Index

### Find Items You Want to Track

First, find item IDs:

```bash
# Search for AWP skins
curl "http://localhost:8000/api/items/search?q=AWP"
```

Note down the `id` values of items you want to track.

### Create Your Index

Using the API docs at `/docs`:

1. Expand **Indices** → `POST /api/indices`
2. Click **"Try it out"**
3. Replace the example JSON with your data:

```json
{
  "name": "My AWP Collection",
  "description": "Tracking my favorite AWP skins",
  "type": "CUSTOM",
  "category": null,
  "selected_markets": ["STEAMCOMMUNITY", "SKINPORT"],
  "currency": "USD",
  "item_ids": [123, 456, 789]
}
```

Replace `[123, 456, 789]` with your actual item IDs.

4. Click **"Execute"**

Your custom index is created! Note the `id` in the response.

### Calculate Your Index Price

Use the Prices endpoints as shown above to calculate and track your custom index.

## Understanding the Data

### Index Types

- **PREBUILT**: Auto-generated (Rifles, Knives, Cases, etc.)
- **CUSTOM**: User-created collections

### Markets

Available markets you can query:
- STEAMCOMMUNITY (Steam Community Market)
- SKINPORT
- CSFLOAT
- BUFFMARKET
- DMARKET
- And 7 more...

### Price Calculation

The index value is calculated as:
```
Total Value = Sum of all item minimum prices
```

For example:
- AWP | Dragon Lore (FN): $4,500
- AWP | Gungnir (FN): $10,000
- AWP | The Prince (FN): $2,000
- **Index Value: $16,500**

## Common Use Cases

### 1. Track Your Inventory

1. Find your items using search
2. Create a custom index with those items
3. Calculate price regularly to track value

### 2. Monitor Market Segments

Use prebuilt indices:
- Compare Rifles vs Pistols performance
- Track Cases value over time
- Monitor Knife market trends

### 3. Investment Research

1. Create multiple indices for different strategies
2. Calculate prices daily/weekly
3. Compare historical performance

## Troubleshooting

### "Items sync failed"

**Issue**: API key might be invalid

**Solution**:
1. Check your `.env` file
2. Verify API key is correct
3. Test at https://csmarketapi.com

### "Prebuilt indices: 0 categories"

**Issue**: Item sync didn't complete

**Solution**:
```bash
curl -X POST http://localhost:8000/api/items/sync
curl -X POST http://localhost:8000/api/prebuilt/generate
```

### "Price calculation taking too long"

**Normal**: Large indices (500+ items) take 20-60 seconds

**Why**: The API fetches prices for each item individually

**Tip**: Use smaller custom indices for faster calculations

### "Database locked" errors

**Issue**: SQLite concurrency

**Solution**: Only one write at a time. If you need concurrent writes, switch to PostgreSQL (requires code changes).

## Next Steps

Now that you have the backend running:

1. **Explore the API**: Try all endpoints at `/docs`
2. **Create Custom Indices**: Build collections that interest you
3. **Track Prices**: Calculate prices multiple times to build history
4. **Build Frontend** (Optional): Follow the plan to create a UI

## API Endpoints Quick Reference

### Items
- `GET /api/items` - List all items (paginated)
- `GET /api/items/search?q={query}` - Search items
- `GET /api/items/{id}` - Get single item
- `POST /api/items/sync` - Sync from API

### Indices
- `GET /api/indices` - List all indices
- `POST /api/indices` - Create custom index
- `GET /api/indices/{id}` - Get index details
- `PUT /api/indices/{id}` - Update index
- `DELETE /api/indices/{id}` - Delete index

### Prebuilt
- `GET /api/prebuilt` - List categories
- `GET /api/prebuilt/{category}` - Get prebuilt index
- `POST /api/prebuilt/generate` - Regenerate all

### Prices
- `POST /api/prices/{id}/calculate` - Calculate current price
- `GET /api/prices/{id}/history` - Get price history
- `GET /api/prices/{id}/latest` - Get latest price

### Markets
- `GET /api/markets` - List available markets

## Tips for Best Results

1. **Start Small**: Create indices with 5-10 items first
2. **Calculate Regularly**: Build up historical data over time
3. **Use Multiple Markets**: Get better price coverage
4. **Monitor Specific Niches**: Create focused indices for better insights
5. **Export Data**: Use the API to export data for external analysis

## Need Help?

- **API Documentation**: http://localhost:8000/docs
- **Architecture Details**: See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Full README**: See [README.md](README.md)
- **Plan File**: `/Users/antoniohaas/.claude/plans/mossy-plotting-scott.md`

---

**You're all set! Start tracking CS:GO market indices.** 🎮📈
