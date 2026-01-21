"""Prices router for price calculation and history."""

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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


@router.get("/{index_id}/sales-history")
async def get_sales_history(
    index_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch (1-365)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated sales history for all items in the index.

    This fetches historical sales data (actual transactions) directly from the markets
    instead of using our calculated price points or listings.

    - **days**: Number of days to look back (default: 30, max: 365)

    Returns aggregated min sale prices summed across all items in the index.
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

    # Fetch sales history for all items in PARALLEL (optimized)
    async with get_csmarket_service() as csmarket:
        # Dictionary to store history data: {timestamp: total_value}
        aggregated_history = {}

        # Use batch method for parallel fetching
        history_results = await csmarket.batch_get_sales_history(
            item_market_hash_names=item_names,
            markets=markets,
            currency=index.currency,
        )

        # Process all sales history results
        for item_name, history in history_results.items():
            if history is None:
                continue

            try:
                # Process each historical data point
                for hist_item in history.items:
                    # Sales history uses 'day' attribute (date as string)
                    if not hasattr(hist_item, 'day'):
                        continue

                    day_str = str(hist_item.day)  # Convert to string for consistent key

                    # Find the minimum sale price across all market sales at this day
                    min_price_at_day = None
                    for sale in hist_item.sales:
                        if sale.min_price is not None:
                            if min_price_at_day is None or sale.min_price < min_price_at_day:
                                min_price_at_day = sale.min_price

                    # Add to aggregated history
                    if min_price_at_day is not None:
                        if day_str in aggregated_history:
                            aggregated_history[day_str] += min_price_at_day
                        else:
                            aggregated_history[day_str] = min_price_at_day

            except Exception as e:
                # Log error but continue with other items
                print(f"Failed to process sales history for {item_name}: {e}")
                continue

    # Convert to sorted list of data points
    data_points = [
        {
            "timestamp": timestamp,
            "value": value,
        }
        for timestamp, value in sorted(aggregated_history.items())
    ]

    # Filter by days (day strings are date-only, so compare dates)
    cutoff_date = datetime.now().date() - timedelta(days=days)
    filtered_points = [
        point for point in data_points
        if datetime.fromisoformat(point["timestamp"]).date() >= cutoff_date
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


@router.get("/{index_id}/sales-history-stream")
async def get_sales_history_stream(
    index_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch (1-365)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated sales history with real-time progress updates via SSE.

    This is a Server-Sent Events (SSE) endpoint that streams progress updates
    as items are fetched from the API.

    - **days**: Number of days to look back (default: 30, max: 365)

    Event types:
    - progress: {"completed": int, "total": int, "percentage": float}
    - data: {"data_points": [...], "index_id": int, ...}
    - error: {"error": str}
    """
    async def event_generator():
        try:
            # Check if index exists and load items
            index = await index_service.get_index(db=db, index_id=index_id, include_items=True)

            if not index:
                yield f"event: error\ndata: {json.dumps({'error': 'Index not found'})}\n\n"
                return

            if not index.item_associations:
                yield f"event: error\ndata: {json.dumps({'error': 'Index has no items'})}\n\n"
                return

            # Get markets from index
            markets = json.loads(index.selected_markets)

            if not markets:
                yield f"event: error\ndata: {json.dumps({'error': 'No markets selected'})}\n\n"
                return

            # Collect all item names
            item_names = [assoc.item.market_hash_name for assoc in index.item_associations]
            total_items = len(item_names)

            # Progress callback
            def on_progress(completed: int, total: int):
                percentage = (completed / total * 100) if total > 0 else 0
                progress_data = {
                    "completed": completed,
                    "total": total,
                    "percentage": round(percentage, 1)
                }
                # Note: Can't yield from callback, so we'll handle this differently
                asyncio.create_task(
                    asyncio.sleep(0)  # Placeholder - we'll use a different approach
                )

            # Send initial progress
            yield f"event: progress\ndata: {json.dumps({'completed': 0, 'total': total_items, 'percentage': 0})}\n\n"

            # Fetch sales history for all items in PARALLEL
            async with get_csmarket_service() as csmarket:
                aggregated_history = {}

                # Create a queue for progress updates
                progress_queue = asyncio.Queue()

                def progress_callback(completed: int, total: int):
                    """Non-blocking progress callback"""
                    percentage = (completed / total * 100) if total > 0 else 0
                    progress_queue.put_nowait({
                        "completed": completed,
                        "total": total,
                        "percentage": round(percentage, 1)
                    })

                # Start fetching in background
                fetch_task = asyncio.create_task(
                    csmarket.batch_get_sales_history(
                        item_market_hash_names=item_names,
                        markets=markets,
                        currency=index.currency,
                        on_progress=progress_callback,
                    )
                )

                # Stream progress updates while fetching
                while not fetch_task.done():
                    try:
                        progress_data = await asyncio.wait_for(
                            progress_queue.get(), timeout=0.1
                        )
                        yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"
                    except asyncio.TimeoutError:
                        continue

                # Drain remaining progress updates
                while not progress_queue.empty():
                    progress_data = progress_queue.get_nowait()
                    yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"

                # Get results
                history_results = await fetch_task

                # Process all sales history results
                for item_name, history in history_results.items():
                    if history is None:
                        continue

                    try:
                        for hist_item in history.items:
                            # Sales history uses 'day' attribute (date as string)
                            if not hasattr(hist_item, 'day'):
                                continue

                            day_str = str(hist_item.day)  # Convert to string for consistent key
                            min_price_at_day = None

                            for sale in hist_item.sales:
                                if sale.min_price is not None:
                                    if min_price_at_day is None or sale.min_price < min_price_at_day:
                                        min_price_at_day = sale.min_price

                            if min_price_at_day is not None:
                                if day_str in aggregated_history:
                                    aggregated_history[day_str] += min_price_at_day
                                else:
                                    aggregated_history[day_str] = min_price_at_day

                    except Exception as e:
                        print(f"Failed to process sales history for {item_name}: {e}")
                        continue

            # Convert to sorted list of data points
            data_points = [
                {"timestamp": timestamp, "value": value}
                for timestamp, value in sorted(aggregated_history.items())
            ]

            # Filter by days (day strings are date-only, so compare dates)
            cutoff_date = datetime.now().date() - timedelta(days=days)
            filtered_points = [
                point for point in data_points
                if datetime.fromisoformat(point["timestamp"]).date() >= cutoff_date
            ]

            # Send final data
            result = {
                "index_id": index.id,
                "index_name": index.name,
                "currency": index.currency,
                "days": days,
                "item_count": len(item_names),
                "markets_used": markets,
                "data_points": filtered_points,
            }

            yield f"event: data\ndata: {json.dumps(result)}\n\n"
            yield f"event: complete\ndata: {json.dumps({'success': True})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )


@router.get("/{index_id}/robust-sales-history")
async def get_robust_sales_history(
    index_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch (1-365)"),
    outlier_threshold: float = Query(
        0.25, ge=0.1, le=0.5,
        description="Outlier threshold (0.25 = ±25% from median)"
    ),
    stale_days: int = Query(
        7, ge=1, le=30,
        description="Days after which data is considered stale"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get robust sales history with illiquidity handling.

    This endpoint implements best practices from financial and crypto indices:
    - **Carry-forward**: If an item has no sale on a given day, the last known price is used
    - **Outlier removal**: Prices outside ±threshold from median are filtered
    - **Volume-weighted**: Larger trades have more weight in price calculation
    - **Stale data handling**: After stale_days, uses median of recent sales as fallback

    Parameters:
    - **days**: Number of days to look back (default: 30, max: 365)
    - **outlier_threshold**: Percentage threshold for outlier detection (default: 0.25 = ±25%)
    - **stale_days**: Days after which carry-forward becomes stale (default: 7)

    Response includes:
    - data_points: Array of daily values with metadata
    - Each point shows items_with_data, items_carried_forward, items_skipped
    - config: The configuration used for this calculation
    """
    try:
        result = await price_service.calculate_robust_sales_history(
            db=db,
            index_id=index_id,
            days=days,
            outlier_threshold=outlier_threshold,
            stale_days=stale_days,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
