"""Items router for item-related endpoints."""

import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..schemas import ItemListResponse, ItemSearchResponse, ItemResponse
from ..services import item_service

router = APIRouter()


@router.get("/", response_model=ItemListResponse)
async def get_items(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    type: Optional[str] = Query(None, description="Filter by type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    weapon: Optional[str] = Query(None, description="Filter by weapon"),
    exterior: Optional[str] = Query(None, description="Filter by exterior"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of items with optional filters.

    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 50, max: 100)
    - **type**: Filter by item type (e.g., "Weapon", "Sticker")
    - **category**: Filter by category (e.g., "Rifle", "Knife")
    - **weapon**: Filter by weapon name
    - **exterior**: Filter by exterior (e.g., "Factory New")
    """
    items, total = await item_service.get_items_paginated(
        db=db,
        page=page,
        limit=limit,
        type_filter=type,
        category_filter=category,
        weapon_filter=weapon,
        exterior_filter=exterior,
    )

    pages = math.ceil(total / limit) if total > 0 else 0

    return ItemListResponse(
        items=[ItemResponse.from_orm(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/search", response_model=ItemSearchResponse)
async def search_items(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search items by name (case-insensitive).

    - **q**: Search query
    - **limit**: Maximum results (default: 10, max: 50)
    """
    items = await item_service.search_items(db=db, query=q, limit=limit)

    return ItemSearchResponse(
        items=[ItemResponse.from_orm(item) for item in items],
        query=q,
        count=len(items),
    )


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single item by ID."""
    from fastapi import HTTPException

    item = await item_service.get_item_by_id(db=db, item_id=item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemResponse.from_orm(item)


@router.post("/sync")
async def sync_items(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger item synchronization from CSMarketAPI.

    This endpoint fetches all items from the API and updates the local database.
    Note: This operation can take several seconds.
    """
    count = await item_service.sync_items_from_api(db=db)

    return {
        "message": "Items synced successfully",
        "count": count,
    }
