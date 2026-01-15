"""Pydantic schemas for items."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    """Base item schema."""

    market_hash_name: str
    hash_name: str
    nameid: Optional[int] = None
    classid: Optional[str] = None
    exterior: Optional[str] = None
    category: Optional[str] = None
    weapon: Optional[str] = None
    type: Optional[str] = None
    quality: Optional[str] = None
    collection: Optional[str] = None
    min_float: Optional[float] = None
    max_float: Optional[float] = None
    icon_url: Optional[str] = None


class ItemResponse(ItemBase):
    """Response schema for item."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    """Paginated list of items."""

    items: list[ItemResponse]
    total: int
    page: int
    limit: int
    pages: int


class ItemSearchResponse(BaseModel):
    """Search results for items."""

    items: list[ItemResponse]
    query: str
    count: int
