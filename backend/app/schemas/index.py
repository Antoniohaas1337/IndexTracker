"""Pydantic schemas for indices."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .common import IndexType, Currency


class IndexCreate(BaseModel):
    """Schema for creating a new index."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: IndexType
    category: Optional[str] = None
    selected_markets: List[str] = Field(..., min_items=1)
    currency: Currency = Currency.USD
    item_ids: List[int] = Field(..., min_items=1)


class IndexUpdate(BaseModel):
    """Schema for updating an index."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    selected_markets: Optional[List[str]] = Field(None, min_items=1)
    currency: Optional[Currency] = None
    item_ids: Optional[List[int]] = Field(None, min_items=1)


class IndexResponse(BaseModel):
    """Response schema for index."""

    id: int
    name: str
    description: Optional[str]
    type: IndexType
    category: Optional[str]
    selected_markets: List[str]
    currency: Currency
    item_count: int
    created_at: datetime
    updated_at: datetime
    latest_price: Optional[float] = None

    class Config:
        from_attributes = True


class IndexDetailResponse(IndexResponse):
    """Detailed index response with items."""

    items: List[dict]  # Will contain item details


class IndexListResponse(BaseModel):
    """List of indices."""

    indices: List[IndexResponse]
    total: int
