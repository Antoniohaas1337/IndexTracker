"""Item service for syncing and managing CS:GO item data."""

import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from ..models import Item
from .csmarket_service import CSMarketService

logger = logging.getLogger(__name__)


async def sync_items_from_api(db: AsyncSession) -> int:
    """
    Fetch all items from CSMarketAPI and upsert into database.

    This function is called on application startup to populate/update
    the local items cache.

    Args:
        db: Database session

    Returns:
        Number of items synced
    """
    logger.info("Starting item sync from CSMarketAPI...")

    async with CSMarketService() as csmarket:
        items_response = await csmarket.get_all_items()

    logger.info(f"Received {len(items_response.items)} items from API")

    synced_count = 0

    # Process items in batches for better performance
    for item_data in items_response.items:
        try:
            # Check if item exists
            stmt = select(Item).where(
                Item.market_hash_name == item_data.market_hash_name
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing item
                existing.hash_name = item_data.hash_name
                existing.nameid = item_data.nameid
                existing.classid = item_data.classid
                existing.exterior = item_data.exterior
                existing.category = item_data.category
                existing.weapon = item_data.weapon
                existing.type = item_data.type
                existing.quality = item_data.quality
                existing.collection = item_data.collection
                existing.min_float = item_data.min_float
                existing.max_float = item_data.max_float
                existing.icon_url = (
                    item_data.cloudflare_icon_url or item_data.akamai_icon_url
                )
                existing.updated_at = datetime.utcnow()
            else:
                # Create new item
                new_item = Item(
                    market_hash_name=item_data.market_hash_name,
                    hash_name=item_data.hash_name,
                    nameid=item_data.nameid,
                    classid=item_data.classid,
                    exterior=item_data.exterior,
                    category=item_data.category,
                    weapon=item_data.weapon,
                    type=item_data.type,
                    quality=item_data.quality,
                    collection=item_data.collection,
                    min_float=item_data.min_float,
                    max_float=item_data.max_float,
                    icon_url=item_data.cloudflare_icon_url or item_data.akamai_icon_url,
                )
                db.add(new_item)

            synced_count += 1

        except Exception as e:
            logger.error(f"Failed to sync item '{item_data.market_hash_name}': {e}")
            continue

    await db.commit()
    logger.info(f"Item sync completed: {synced_count} items synced")

    return synced_count


async def get_items_paginated(
    db: AsyncSession,
    page: int = 1,
    limit: int = 50,
    type_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    weapon_filter: Optional[str] = None,
    exterior_filter: Optional[str] = None,
) -> tuple[List[Item], int]:
    """
    Get items with pagination and filtering.

    Args:
        db: Database session
        page: Page number (1-indexed)
        limit: Items per page
        type_filter: Filter by type (e.g., "Weapon", "Sticker")
        category_filter: Filter by category (e.g., "Rifle", "Knife")
        weapon_filter: Filter by weapon name
        exterior_filter: Filter by exterior (e.g., "Factory New")

    Returns:
        Tuple of (items list, total count)
    """
    query = select(Item)

    # Apply filters
    if type_filter:
        query = query.where(Item.type == type_filter)
    if category_filter:
        query = query.where(Item.category == category_filter)
    if weapon_filter:
        query = query.where(Item.weapon == weapon_filter)
    if exterior_filter:
        query = query.where(Item.exterior == exterior_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    return items, total


async def search_items(
    db: AsyncSession, query: str, limit: int = 10
) -> List[Item]:
    """
    Search items by name with case-insensitive matching.

    Args:
        db: Database session
        query: Search query
        limit: Maximum results

    Returns:
        List of matching items
    """
    search_term = f"%{query.lower()}%"

    stmt = (
        select(Item)
        .where(
            or_(
                func.lower(Item.market_hash_name).like(search_term),
                func.lower(Item.hash_name).like(search_term),
            )
        )
        .limit(limit)
    )

    result = await db.execute(stmt)
    items = result.scalars().all()

    return items


async def get_item_by_id(db: AsyncSession, item_id: int) -> Optional[Item]:
    """Get item by ID."""
    stmt = select(Item).where(Item.id == item_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_item_by_market_hash_name(
    db: AsyncSession, market_hash_name: str
) -> Optional[Item]:
    """Get item by market hash name."""
    stmt = select(Item).where(Item.market_hash_name == market_hash_name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_items_by_ids(db: AsyncSession, item_ids: List[int]) -> List[Item]:
    """Get multiple items by IDs."""
    stmt = select(Item).where(Item.id.in_(item_ids))
    result = await db.execute(stmt)
    return result.scalars().all()
