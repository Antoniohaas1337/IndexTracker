"""Index service for CRUD operations and prebuilt index generation."""

import json
import logging
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from ..models import Index, IndexItem, Item
from ..schemas import IndexType

logger = logging.getLogger(__name__)


async def create_index(
    db: AsyncSession,
    name: str,
    description: Optional[str],
    index_type: IndexType,
    category: Optional[str],
    selected_markets: List[str],
    currency: str,
    item_ids: List[int],
) -> Index:
    """
    Create a new index with associated items.

    Args:
        db: Database session
        name: Index name
        description: Optional description
        index_type: CUSTOM or PREBUILT
        category: Category for prebuilt indices
        selected_markets: List of market names
        currency: Currency code
        item_ids: List of item IDs to include

    Returns:
        Created Index object

    Raises:
        ValueError: If item IDs are invalid
    """
    logger.info(f"Creating {index_type} index '{name}' with {len(item_ids)} items")

    # Validate items exist
    stmt = select(func.count()).select_from(Item).where(Item.id.in_(item_ids))
    result = await db.execute(stmt)
    count = result.scalar()

    if count != len(item_ids):
        raise ValueError(f"Some item IDs are invalid: expected {len(item_ids)}, found {count}")

    # Create index
    new_index = Index(
        name=name,
        description=description,
        type=index_type.value,
        category=category,
        selected_markets=json.dumps(selected_markets),
        currency=currency,
    )

    db.add(new_index)
    await db.flush()  # Get the index ID

    # Add item associations
    for item_id in item_ids:
        association = IndexItem(index_id=new_index.id, item_id=item_id)
        db.add(association)

    await db.commit()
    await db.refresh(new_index)

    logger.info(f"Index created with ID {new_index.id}")

    return new_index


async def get_index(
    db: AsyncSession, index_id: int, include_items: bool = False
) -> Optional[Index]:
    """
    Get index by ID.

    Args:
        db: Database session
        index_id: Index ID
        include_items: Whether to eager load items

    Returns:
        Index object or None
    """
    query = select(Index).where(Index.id == index_id)

    if include_items:
        query = query.options(
            selectinload(Index.item_associations).selectinload(IndexItem.item)
        )

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_indices(
    db: AsyncSession, index_type: Optional[IndexType] = None
) -> List[Index]:
    """
    Get all indices, optionally filtered by type.

    Args:
        db: Database session
        index_type: Optional filter by CUSTOM or PREBUILT

    Returns:
        List of Index objects
    """
    query = select(Index).options(selectinload(Index.item_associations))

    if index_type:
        query = query.where(Index.type == index_type.value)

    query = query.order_by(Index.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def update_index(
    db: AsyncSession,
    index_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    selected_markets: Optional[List[str]] = None,
    currency: Optional[str] = None,
    item_ids: Optional[List[int]] = None,
) -> Index:
    """
    Update an existing index.

    Args:
        db: Database session
        index_id: Index ID
        name: New name (optional)
        description: New description (optional)
        selected_markets: New markets (optional)
        currency: New currency (optional)
        item_ids: New item IDs (optional, replaces all items)

    Returns:
        Updated Index object

    Raises:
        ValueError: If index not found or item IDs invalid
    """
    index = await get_index(db, index_id)

    if not index:
        raise ValueError(f"Index {index_id} not found")

    # Update fields
    if name is not None:
        index.name = name
    if description is not None:
        index.description = description
    if selected_markets is not None:
        index.selected_markets = json.dumps(selected_markets)
    if currency is not None:
        index.currency = currency

    # Update items if provided
    if item_ids is not None:
        # Validate items
        stmt = select(func.count()).select_from(Item).where(Item.id.in_(item_ids))
        result = await db.execute(stmt)
        count = result.scalar()

        if count != len(item_ids):
            raise ValueError(f"Some item IDs are invalid")

        # Delete existing associations
        await db.execute(delete(IndexItem).where(IndexItem.index_id == index_id))

        # Add new associations
        for item_id in item_ids:
            association = IndexItem(index_id=index_id, item_id=item_id)
            db.add(association)

    await db.commit()
    await db.refresh(index)

    logger.info(f"Updated index {index_id}")

    return index


async def delete_index(db: AsyncSession, index_id: int) -> bool:
    """
    Delete an index.

    Args:
        db: Database session
        index_id: Index ID

    Returns:
        True if deleted, False if not found
    """
    index = await get_index(db, index_id)

    if not index:
        return False

    await db.delete(index)
    await db.commit()

    logger.info(f"Deleted index {index_id}")

    return True


async def generate_prebuilt_indices(db: AsyncSession) -> Dict[str, Index]:
    """
    Generate prebuilt indices for common categories.

    Creates or updates indices for:
    - RIFLES (all rifle skins)
    - PISTOLS (all pistol skins)
    - SMGS (all SMG skins)
    - KNIVES (all knife skins)
    - GLOVES (all glove skins)
    - CASES (all weapon cases)
    - STICKERS (all stickers)

    Args:
        db: Database session

    Returns:
        Dictionary mapping category name to Index object
    """
    logger.info("Generating prebuilt indices...")

    # Define categories and their filters (based on actual CSMarketAPI data)
    categories = {
        "RIFLES": {"type": "Rifle"},
        "PISTOLS": {"type": "Pistol"},
        "SMGS": {"type": "SMG"},
        "KNIVES": {"type": "Knife"},
        "GLOVES": {"type": "Gloves"},
        "CASES": {"type": "Container"},
        "GRAFFITI": {"type": "Graffiti"},
    }

    created_indices = {}

    for category_name, filters in categories.items():
        # Query items matching filters
        query = select(Item)

        for key, value in filters.items():
            query = query.where(getattr(Item, key) == value)

        result = await db.execute(query)
        items = result.scalars().all()

        if not items:
            logger.warning(f"No items found for category '{category_name}', skipping")
            continue

        item_ids = [item.id for item in items]

        # Check if prebuilt index exists
        stmt = select(Index).where(
            Index.type == IndexType.PREBUILT.value, Index.category == category_name
        )
        result = await db.execute(stmt)
        existing_index = result.scalar_one_or_none()

        if existing_index:
            logger.info(
                f"Updating existing prebuilt index '{category_name}' with {len(items)} items"
            )

            # Delete old associations
            await db.execute(
                delete(IndexItem).where(IndexItem.index_id == existing_index.id)
            )

            # Add new associations
            for item_id in item_ids:
                association = IndexItem(index_id=existing_index.id, item_id=item_id)
                db.add(association)

            await db.commit()
            await db.refresh(existing_index)

            created_indices[category_name] = existing_index

        else:
            logger.info(f"Creating new prebuilt index '{category_name}' with {len(items)} items")

            new_index = await create_index(
                db=db,
                name=f"{category_name.title()} Index",
                description=f"All {category_name.lower()} items",
                index_type=IndexType.PREBUILT,
                category=category_name,
                selected_markets=["STEAMCOMMUNITY"],
                currency="USD",
                item_ids=item_ids,
            )

            created_indices[category_name] = new_index

    logger.info(f"Prebuilt index generation complete: {len(created_indices)} indices")

    return created_indices


async def get_prebuilt_index_by_category(
    db: AsyncSession, category: str
) -> Optional[Index]:
    """
    Get a prebuilt index by category name.

    Args:
        db: Database session
        category: Category name (e.g., "RIFLES", "KNIVES")

    Returns:
        Index object or None
    """
    stmt = (
        select(Index)
        .where(Index.type == IndexType.PREBUILT.value, Index.category == category)
        .options(selectinload(Index.item_associations).selectinload(IndexItem.item))
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()
