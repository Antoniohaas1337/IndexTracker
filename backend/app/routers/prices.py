"""Prices router for price calculation and history."""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
from ..database import get_db
from ..schemas import (
    PriceHistoryResponse,
    PriceCalculationResponse,
    LatestPriceResponse,
    PricePointResponse,
)
from ..services import price_service, index_service
from ..services.csmarket_service import get_csmarket_service

router = APIRouter()


@router.post("/{index_id}/calculate", response_model=PriceCalculationResponse)
async def calculate_price(
    index_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate and store the current price for an index.

    This endpoint triggers a price calculation by:
    1. Fetching min prices for all items in the index
    2. Summing the min prices
    3. Storing the result as a price point

    The calculation uses the MIN PRICE across all selected markets.
    """
    try:
        result = await price_service.calculate_index_price(db=db, index_id=index_id)

        return PriceCalculationResponse(
            index_id=result["index_id"],
            timestamp=result["timestamp"],
            value=result["value"],
            currency=result["currency"],
            item_count=result["item_count"],
            items_succeeded=result["items_succeeded"],
            items_failed=result["items_failed"],
            markets_used=result["markets_used"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")


@router.get("/{index_id}/history", response_model=PriceHistoryResponse)
async def get_price_history(
    index_id: int,
    start: Optional[datetime] = Query(None, description="Start date"),
    end: Optional[datetime] = Query(None, description="End date"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum data points"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical price data for an index.

    - **start**: Optional start date filter
    - **end**: Optional end date filter
    - **limit**: Maximum number of price points (default: 100, max: 1000)
    """
    # Check if index exists
    index = await index_service.get_index(db=db, index_id=index_id)

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")

    # Get price history
    price_points = await price_service.get_price_history(
        db=db,
        index_id=index_id,
        start=start,
        end=end,
        limit=limit,
    )

    # Convert to response format
    data_points = []
    for point in price_points:
        data_points.append(
            PricePointResponse(
                timestamp=point.timestamp,
                value=point.value,
                currency=point.currency,
                item_count=point.item_count,
                markets_used=json.loads(point.markets_used),
            )
        )

    return PriceHistoryResponse(
        index_id=index.id,
        index_name=index.name,
        currency=index.currency,
        data_points=data_points,
    )


@router.get("/{index_id}/latest", response_model=LatestPriceResponse)
async def get_latest_price(
    index_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the most recent price point for an index.
    """
    # Check if index exists
    index = await index_service.get_index(db=db, index_id=index_id)

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")

    # Get latest price
    price_point = await price_service.get_latest_price(db=db, index_id=index_id)

    if price_point:
        return LatestPriceResponse(
            index_id=index.id,
            latest_price=PricePointResponse(
                timestamp=price_point.timestamp,
                value=price_point.value,
                currency=price_point.currency,
                item_count=price_point.item_count,
                markets_used=json.loads(price_point.markets_used),
            ),
            has_data=True,
        )
    else:
        return LatestPriceResponse(
            index_id=index.id,
            latest_price=None,
            has_data=False,
        )


@router.get("/{index_id}/listings-history")
async def get_listings_history(
    index_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch (1-365)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated listings history for all items in the index.

    This fetches historical price data directly from the markets
    instead of using our calculated price points.

    - **days**: Number of days to look back (default: 30, max: 365)

    Returns aggregated min prices summed across all items in the index.
    """
    # Check if index exists and load items
    index = await index_service.get_index(db=db, index_id=index_id, include_items=True)

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")

    if not index.item_associations:
        raise HTTPException(
            status_code=400,
            detail="Index has no items. Add items to view history."
        )

    # Get markets from index
    markets = json.loads(index.selected_markets)

    if not markets:
        raise HTTPException(
            status_code=400,
            detail="Index has no markets selected"
        )

    # Collect all item names
    item_names = [assoc.item.market_hash_name for assoc in index.item_associations]

    # Fetch history for all items in parallel
    async with get_csmarket_service() as csmarket:
        # Dictionary to store history data: {timestamp: total_value}
        aggregated_history = {}

        for item_name in item_names:
            try:
                history = await csmarket.get_listing_history(
                    market_hash_name=item_name,
                    markets=markets,
                    currency=index.currency,
                )

                # Process each historical data point
                for hist_item in history.items:
                    timestamp = hist_item.timestamp.isoformat()

                    # Find the minimum price across all market listings at this timestamp
                    min_price_at_timestamp = None
                    for listing in hist_item.listings:
                        if listing.min_price is not None:
                            if min_price_at_timestamp is None or listing.min_price < min_price_at_timestamp:
                                min_price_at_timestamp = listing.min_price

                    # Add to aggregated history
                    if min_price_at_timestamp is not None:
                        if timestamp in aggregated_history:
                            aggregated_history[timestamp] += min_price_at_timestamp
                        else:
                            aggregated_history[timestamp] = min_price_at_timestamp

            except Exception as e:
                # Log error but continue with other items
                print(f"Failed to fetch history for {item_name}: {e}")
                continue

    # Convert to sorted list of data points
    data_points = [
        {
            "timestamp": timestamp,
            "value": value,
        }
        for timestamp, value in sorted(aggregated_history.items())
    ]

    # Filter by days (make cutoff_date timezone-aware to match API timestamps)
    from datetime import timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    filtered_points = [
        point for point in data_points
        if datetime.fromisoformat(point["timestamp"]) >= cutoff_date
    ]

    return {
        "index_id": index.id,
        "index_name": index.name,
        "currency": index.currency,
        "days": days,
        "item_count": len(item_names),
        "markets_used": markets,
        "data_points": filtered_points,
    }
