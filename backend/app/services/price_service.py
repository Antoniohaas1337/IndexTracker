"""Price service for calculating and storing index values.

This module contains the CORE ALGORITHM for index valuation.
All calculations use MINIMUM PRICES ONLY across selected markets.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from ..models import Index, PricePoint, IndexItem
from .csmarket_service import CSMarketService

logger = logging.getLogger(__name__)


async def calculate_index_price(
    db: AsyncSession,
    index_id: int,
) -> Dict:
    """
    Calculate the sum of min prices for all items in an index.

    This is the CORE ALGORITHM for index valuation. It implements the
    portfolio approach: summing the minimum prices of all items.

    Algorithm Steps:
    1. Load index configuration and associated items from database
    2. Parse selected markets from index settings
    3. Fetch latest min prices for each item from CSMarketAPI (parallel)
    4. Sum all min prices (only successful fetches count)
    5. Store price point in database with metadata
    6. Return calculation result

    Args:
        db: Database session
        index_id: Index ID to calculate

    Returns:
        Dictionary with calculation results:
        {
            "index_id": int,
            "timestamp": datetime,
            "value": float (sum of min prices),
            "currency": str,
            "item_count": int,
            "items_succeeded": int,
            "items_failed": int,
            "markets_used": List[str]
        }

    Raises:
        ValueError: If index not found or has no items
    """
    logger.info(f"Starting price calculation for index {index_id}")

    # Step 1: Load index with items (eager loading for efficiency)
    stmt = (
        select(Index)
        .where(Index.id == index_id)
        .options(selectinload(Index.item_associations).selectinload(IndexItem.item))
    )
    result = await db.execute(stmt)
    index = result.scalar_one_or_none()

    if not index:
        raise ValueError(f"Index {index_id} not found")

    items = [assoc.item for assoc in index.item_associations]

    if not items:
        raise ValueError(f"Index {index_id} has no items")

    logger.info(
        f"Calculating price for index '{index.name}' ({index.type}) with {len(items)} items"
    )

    # Step 2: Parse markets from JSON
    markets = json.loads(index.selected_markets)
    logger.debug(f"Using markets: {markets}")

    # Step 3: Fetch min prices for all items using CSMarketAPI
    item_names = [item.market_hash_name for item in items]

    async with CSMarketService() as csmarket:
        price_results = await csmarket.batch_get_min_prices(
            item_market_hash_names=item_names,
            markets=markets,
            currency=index.currency,
        )

    # Step 4: Sum all min prices (core calculation)
    total_value = 0.0
    items_succeeded = 0
    items_failed = 0

    for item_name, min_price in price_results.items():
        if min_price is not None:
            total_value += min_price
            items_succeeded += 1
        else:
            items_failed += 1

    logger.info(
        f"Index '{index.name}' calculated value: ${total_value:.2f} "
        f"({items_succeeded} items succeeded, {items_failed} failed)"
    )

    # Step 5: Store price point in database
    timestamp = datetime.utcnow()

    price_point = PricePoint(
        index_id=index.id,
        timestamp=timestamp,
        value=total_value,
        currency=index.currency,
        item_count=len(items),
        markets_used=json.dumps(markets),
        extra_data=json.dumps(
            {
                "items_succeeded": items_succeeded,
                "items_failed": items_failed,
                "calculation_method": "sum_of_min_prices",
            }
        ),
    )

    db.add(price_point)
    await db.commit()
    await db.refresh(price_point)

    logger.info(f"Price point saved for index {index_id} at {timestamp}")

    # Step 6: Return result
    return {
        "index_id": index.id,
        "timestamp": timestamp,
        "value": total_value,
        "currency": index.currency,
        "item_count": len(items),
        "items_succeeded": items_succeeded,
        "items_failed": items_failed,
        "markets_used": markets,
    }


async def get_price_history(
    db: AsyncSession,
    index_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> List[PricePoint]:
    """
    Retrieve historical price points for an index.

    Args:
        db: Database session
        index_id: Index ID
        start: Start date (optional)
        end: End date (optional)
        limit: Maximum number of points (optional)

    Returns:
        List of PricePoint objects ordered by timestamp descending
    """
    query = select(PricePoint).where(PricePoint.index_id == index_id)

    if start:
        query = query.where(PricePoint.timestamp >= start)
    if end:
        query = query.where(PricePoint.timestamp <= end)

    query = query.order_by(desc(PricePoint.timestamp))

    if limit:
        query = query.limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_latest_price(
    db: AsyncSession, index_id: int
) -> Optional[PricePoint]:
    """
    Get the most recent price point for an index.

    Args:
        db: Database session
        index_id: Index ID

    Returns:
        Latest PricePoint or None if no data
    """
    stmt = (
        select(PricePoint)
        .where(PricePoint.index_id == index_id)
        .order_by(desc(PricePoint.timestamp))
        .limit(1)
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def batch_calculate_indices(
    db: AsyncSession, index_ids: List[int]
) -> Dict[int, Dict]:
    """
    Calculate prices for multiple indices in sequence.

    Note: Runs sequentially to avoid overwhelming the API.

    Args:
        db: Database session
        index_ids: List of index IDs

    Returns:
        Dictionary mapping index_id to calculation result
    """
    results = {}

    for index_id in index_ids:
        try:
            result = await calculate_index_price(db, index_id)
            results[index_id] = result
        except Exception as e:
            logger.error(f"Failed to calculate price for index {index_id}: {e}")
            results[index_id] = {"error": str(e)}

    return results


async def calculate_robust_sales_history(
    db: AsyncSession,
    index_id: int,
    days: int = 30,
    outlier_threshold: float = 0.25,
    stale_days: int = 7,
) -> Dict:
    """
    Calculate robust index history with illiquidity handling.

    This implements best practices from financial and crypto indices:
    - Carry-forward for missing days (use last known price)
    - Outlier removal (±threshold from median)
    - Volume-weighted price aggregation
    - Stale data handling (fallback after stale_days)

    Algorithm for each day:
    1. For each item, collect all sales from all markets
    2. Remove outliers (prices outside ±threshold from median)
    3. Calculate volume-weighted average price
    4. If no sales: use carry-forward (last known price)
    5. If data is stale (>stale_days): use median of last N sales
    6. Sum all item prices for the day's index value

    Args:
        db: Database session
        index_id: Index ID to calculate
        days: Number of days to look back
        outlier_threshold: Threshold for outlier removal (0.25 = ±25%)
        stale_days: Days after which data is considered stale

    Returns:
        Dictionary with calculation results including data_points
    """
    from datetime import date, timedelta
    from .price_utils import (
        ItemPriceState,
        SaleRecord,
        remove_outliers_with_volume,
        volume_weighted_price_simple,
        get_fallback_price,
    )

    logger.info(f"Starting robust sales history calculation for index {index_id}")

    # Step 1: Load index with items
    stmt = (
        select(Index)
        .where(Index.id == index_id)
        .options(selectinload(Index.item_associations).selectinload(IndexItem.item))
    )
    result = await db.execute(stmt)
    index = result.scalar_one_or_none()

    if not index:
        raise ValueError(f"Index {index_id} not found")

    items = [assoc.item for assoc in index.item_associations]

    if not items:
        raise ValueError(f"Index {index_id} has no items")

    logger.info(
        f"Calculating robust history for index '{index.name}' with {len(items)} items"
    )

    # Step 2: Parse markets
    markets = json.loads(index.selected_markets)
    if not markets:
        raise ValueError(f"Index {index_id} has no markets selected")

    # Step 3: Fetch all sales history in parallel
    item_names = [item.market_hash_name for item in items]

    async with CSMarketService() as csmarket:
        all_sales_history = await csmarket.batch_get_sales_history(
            item_market_hash_names=item_names,
            markets=markets,
            currency=index.currency,
        )

    # Step 4: Build date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    all_dates = [start_date + timedelta(days=i) for i in range(days + 1)]

    # Step 5: Process sales history into structured format
    # Dict: item_name -> Dict[date, List[SaleRecord]]
    item_daily_sales: Dict[str, Dict[date, List[SaleRecord]]] = {}

    for item_name, history in all_sales_history.items():
        if history is None:
            item_daily_sales[item_name] = {}
            continue

        daily_sales: Dict[date, List[SaleRecord]] = {}

        for hist_item in history.items:
            if not hasattr(hist_item, 'day'):
                continue

            try:
                # Parse the day string to date
                day_str = str(hist_item.day)
                item_date = date.fromisoformat(day_str)

                # Collect all sales from all markets
                sales_records = []
                for sale in hist_item.sales:
                    # Try to get a price - prefer avg_price, fall back to min_price
                    price = getattr(sale, 'avg_price', None)
                    if price is None or price <= 0:
                        price = getattr(sale, 'min_price', None)

                    if price is not None and price > 0:
                        # Use price with volume for weighting
                        volume = getattr(sale, 'volume', 1) or 1
                        market_name = getattr(sale, 'market', 'unknown')
                        if hasattr(market_name, 'value'):
                            market_name = market_name.value
                        sales_records.append(SaleRecord(
                            market=str(market_name),
                            price=price,
                            volume=volume,
                        ))

                if sales_records:
                    daily_sales[item_date] = sales_records

            except (ValueError, AttributeError) as e:
                logger.debug(f"Failed to parse sales data for {item_name}: {e}")
                continue

        item_daily_sales[item_name] = daily_sales

    # Step 6: Initialize item states
    item_states: Dict[str, ItemPriceState] = {}
    for item in items:
        item_states[item.market_hash_name] = ItemPriceState(
            item_id=item.id,
            market_hash_name=item.market_hash_name,
        )

    # Step 7: Process each date in chronological order
    daily_values = []

    for current_date in all_dates:
        day_total = 0.0
        items_with_data = 0
        items_carried_forward = 0
        items_skipped = 0

        for item in items:
            state = item_states[item.market_hash_name]
            daily_sales = item_daily_sales.get(item.market_hash_name, {})
            sales_today = daily_sales.get(current_date, [])

            if sales_today:
                # Has sales today - calculate robust price
                prices = [s.price for s in sales_today]
                volumes = [s.volume for s in sales_today]

                # Remove outliers
                filtered_prices, filtered_volumes = remove_outliers_with_volume(
                    prices, volumes, outlier_threshold
                )

                # Calculate volume-weighted price
                price = volume_weighted_price_simple(filtered_prices, filtered_volumes)

                if price is not None:
                    # Update state
                    state.last_known_price = price
                    state.last_sale_date = current_date
                    state.price_history.append((current_date, price))

                    day_total += price
                    items_with_data += 1
                else:
                    items_skipped += 1

            else:
                # No sales today - try carry-forward
                if state.last_known_price is not None and state.last_sale_date is not None:
                    days_since_last = (current_date - state.last_sale_date).days

                    if days_since_last <= stale_days:
                        # Use carry-forward
                        day_total += state.last_known_price
                        items_carried_forward += 1
                    else:
                        # Data is stale - use fallback
                        fallback = get_fallback_price(state.price_history)
                        if fallback is not None:
                            day_total += fallback
                            items_carried_forward += 1
                        else:
                            items_skipped += 1
                else:
                    # No history at all for this item yet
                    items_skipped += 1

        daily_values.append({
            "timestamp": current_date.isoformat(),
            "value": round(day_total, 2),
            "items_with_data": items_with_data,
            "items_carried_forward": items_carried_forward,
            "items_skipped": items_skipped,
        })

    logger.info(
        f"Robust history calculated for index '{index.name}': "
        f"{len(daily_values)} days"
    )

    return {
        "index_id": index.id,
        "index_name": index.name,
        "currency": index.currency,
        "days": days,
        "item_count": len(items),
        "markets_used": markets,
        "data_points": daily_values,
        "config": {
            "outlier_threshold": outlier_threshold,
            "stale_days": stale_days,
        },
    }
