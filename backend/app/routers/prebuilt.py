"""Prebuilt indices router."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas import IndexResponse
from ..services import index_service, price_service

router = APIRouter()


@router.get("/")
async def get_prebuilt_categories():
    """
    Get list of available prebuilt index categories.
    """
    categories = [
        {
            "category": "RIFLES",
            "name": "Rifles Index",
            "description": "All rifle skins",
        },
        {
            "category": "PISTOLS",
            "name": "Pistols Index",
            "description": "All pistol skins",
        },
        {
            "category": "SMGS",
            "name": "SMGs Index",
            "description": "All SMG skins",
        },
        {
            "category": "KNIVES",
            "name": "Knives Index",
            "description": "All knife skins",
        },
        {
            "category": "GLOVES",
            "name": "Gloves Index",
            "description": "All glove skins",
        },
        {
            "category": "CASES",
            "name": "Cases Index",
            "description": "All weapon cases",
        },
        {
            "category": "STICKERS",
            "name": "Stickers Index",
            "description": "All stickers",
        },
    ]

    return {"categories": categories}


@router.get("/{category}", response_model=IndexResponse)
async def get_prebuilt_index(
    category: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a prebuilt index by category.

    Available categories:
    - RIFLES
    - PISTOLS
    - SMGS
    - KNIVES
    - GLOVES
    - CASES
    - STICKERS
    """
    index = await index_service.get_prebuilt_index_by_category(
        db=db, category=category.upper()
    )

    if not index:
        raise HTTPException(
            status_code=404,
            detail=f"Prebuilt index for category '{category}' not found",
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


@router.post("/generate")
async def generate_prebuilt_indices(
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger generation of all prebuilt indices.

    This endpoint creates or updates prebuilt indices for all categories.
    """
    indices = await index_service.generate_prebuilt_indices(db=db)

    return {
        "message": "Prebuilt indices generated successfully",
        "count": len(indices),
        "categories": list(indices.keys()),
    }
