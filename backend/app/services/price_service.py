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
