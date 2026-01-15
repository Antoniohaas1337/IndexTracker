"""Main FastAPI application for CS:GO Market Index Tracker."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .routers import items, indices, prebuilt, prices, markets
from .services import item_service, index_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Startup:
    - Initialize database tables
    - Sync items from CSMarketAPI
    - Generate prebuilt indices

    Shutdown:
    - Cleanup resources
    """
    # Startup
    logger.info("Starting CS:GO Market Index Tracker API...")

    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Import here to avoid circular imports
    from .database import AsyncSessionLocal

    # Sync items on startup
    try:
        logger.info("Syncing items from CSMarketAPI...")
        async with AsyncSessionLocal() as db:
            item_count = await item_service.sync_items_from_api(db)
            logger.info(f"Items sync completed: {item_count} items")
    except Exception as e:
        logger.error(f"Failed to sync items: {e}")
        logger.warning("Continuing without item sync - use /api/items/sync endpoint manually")

    # Generate prebuilt indices
    try:
        logger.info("Generating prebuilt indices...")
        async with AsyncSessionLocal() as db:
            indices = await index_service.generate_prebuilt_indices(db)
            logger.info(f"Prebuilt indices generated: {len(indices)} categories")
    except Exception as e:
        logger.error(f"Failed to generate prebuilt indices: {e}")
        logger.warning("Continuing without prebuilt indices")

    logger.info("Startup complete!")

    yield

    # Shutdown
    logger.info("Shutting down CS:GO Market Index Tracker API...")


# Create FastAPI application
app = FastAPI(
    title="CS:GO Market Index Tracker API",
    description="""
    Track custom CS:GO item price indices using the CSMarketAPI.

    ## Features

    * Create custom indices from any CS:GO items
    * Pre-built indices for common categories (Rifles, Knives, Cases, etc.)
    * Historical price tracking
    * Multi-market support
    * All calculations use **minimum prices** across selected markets

    ## Index Calculation

    Index values are calculated as the **sum of minimum prices** for all items in the index.
    This portfolio approach tracks the total value of item collections over time.

    ## Links

    * [GitHub Repository](https://github.com/yourusername/csgo-index-tracker)
    * [CSMarketAPI Documentation](https://csmarketapi.com)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(items.router, prefix="/api/items", tags=["Items"])
app.include_router(indices.router, prefix="/api/indices", tags=["Indices"])
app.include_router(prebuilt.router, prefix="/api/prebuilt", tags=["Prebuilt Indices"])
app.include_router(prices.router, prefix="/api/prices", tags=["Prices"])
app.include_router(markets.router, prefix="/api/markets", tags=["Markets"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CS:GO Market Index Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "items": "/api/items",
            "indices": "/api/indices",
            "prebuilt": "/api/prebuilt",
            "prices": "/api/prices",
            "markets": "/api/markets",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "csgo-index-tracker-api",
        "version": "1.0.0",
    }
