"""Indices router for index CRUD operations."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas import (
    IndexCreate,
    IndexUpdate,
    IndexResponse,
    IndexDetailResponse,
    IndexListResponse,
)
from ..services import index_service, price_service

router = APIRouter()


@router.post("/", response_model=IndexResponse, status_code=201)
async def create_index(
    index_data: IndexCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new custom index.

    - **name**: Index name (required)
    - **description**: Optional description
    - **type**: Must be "CUSTOM" for user-created indices
    - **selected_markets**: List of market names (at least one required)
    - **currency**: Currency code (default: USD)
    - **item_ids**: List of item IDs to include (at least one required)
    """
    try:
        index = await index_service.create_index(
            db=db,
            name=index_data.name,
            description=index_data.description,
            index_type=index_data.type,
            category=index_data.category,
            selected_markets=index_data.selected_markets,
            currency=index_data.currency.value,
            item_ids=index_data.item_ids,
        )

        # Get item count from input (more efficient than loading associations)
        item_count = len(index_data.item_ids)

        # Get latest price if available
        latest_price_point = await price_service.get_latest_price(db=db, index_id=index.id)

        return IndexResponse(
            id=index.id,
            name=index.name,
            description=index.description,
            type=index.type,
            category=index.category,
            selected_markets=json.loads(index.selected_markets),
            currency=index.currency,
            item_count=item_count,
            created_at=index.created_at,
            updated_at=index.updated_at,
            latest_price=latest_price_point.value if latest_price_point else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=IndexListResponse)
async def get_indices(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all indices (custom and prebuilt).
    """
    indices = await index_service.get_all_indices(db=db)

    response_indices = []
    for index in indices:
        item_count = len(index.item_associations)

        # Get latest price
        latest_price_point = await price_service.get_latest_price(db=db, index_id=index.id)

        response_indices.append(
            IndexResponse(
                id=index.id,
                name=index.name,
                description=index.description,
                type=index.type,
                category=index.category,
                selected_markets=json.loads(index.selected_markets),
                currency=index.currency,
                item_count=item_count,
                created_at=index.created_at,
                updated_at=index.updated_at,
                latest_price=latest_price_point.value if latest_price_point else None,
            )
        )

    return IndexListResponse(
        indices=response_indices,
        total=len(response_indices),
    )


@router.get("/{index_id}", response_model=IndexDetailResponse)
async def get_index(
    index_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific index, including items.
    """
    index = await index_service.get_index(db=db, index_id=index_id, include_items=True)

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")

    # Build items list with details
    items = []
    for assoc in index.item_associations:
        item = assoc.item
        items.append(
            {
                "id": item.id,
                "market_hash_name": item.market_hash_name,
                "type": item.type,
                "category": item.category,
                "weapon": item.weapon,
                "exterior": item.exterior,
                "icon_url": item.icon_url,
            }
        )

    # Get latest price
    latest_price_point = await price_service.get_latest_price(db=db, index_id=index.id)

    return IndexDetailResponse(
        id=index.id,
        name=index.name,
        description=index.description,
        type=index.type,
        category=index.category,
        selected_markets=json.loads(index.selected_markets),
        currency=index.currency,
        item_count=len(items),
        created_at=index.created_at,
        updated_at=index.updated_at,
        latest_price=latest_price_point.value if latest_price_point else None,
        items=items,
    )


@router.put("/{index_id}", response_model=IndexResponse)
async def update_index(
    index_id: int,
    index_data: IndexUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing index.

    - **name**: New name (optional)
    - **description**: New description (optional)
    - **selected_markets**: New markets (optional)
    - **currency**: New currency (optional)
    - **item_ids**: New item IDs (optional, replaces all items)
    """
    try:
        index = await index_service.update_index(
            db=db,
            index_id=index_id,
            name=index_data.name,
            description=index_data.description,
            selected_markets=index_data.selected_markets,
            currency=index_data.currency.value if index_data.currency else None,
            item_ids=index_data.item_ids,
        )

        item_count = len(index.item_associations)

        # Get latest price
        latest_price_point = await price_service.get_latest_price(db=db, index_id=index.id)

        return IndexResponse(
            id=index.id,
            name=index.name,
            description=index.description,
            type=index.type,
            category=index.category,
            selected_markets=json.loads(index.selected_markets),
            currency=index.currency,
            item_count=item_count,
            created_at=index.created_at,
            updated_at=index.updated_at,
            latest_price=latest_price_point.value if latest_price_point else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{index_id}")
async def delete_index(
    index_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an index."""
    success = await index_service.delete_index(db=db, index_id=index_id)

    if not success:
        raise HTTPException(status_code=404, detail="Index not found")

    return {"message": "Index deleted successfully"}
