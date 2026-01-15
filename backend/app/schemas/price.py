"""Pydantic schemas for price data."""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PricePointResponse(BaseModel):
    """Response schema for a single price point."""

    timestamp: datetime
    value: float
    currency: str
    item_count: int
    markets_used: List[str]

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Response schema for price history."""

    index_id: int
    index_name: str
    currency: str
    data_points: List[PricePointResponse]


class PriceCalculationResponse(BaseModel):
    """Response schema for price calculation."""

    index_id: int
    timestamp: datetime
    value: float
    currency: str
    item_count: int
    items_succeeded: int
    items_failed: int
    markets_used: List[str]


class LatestPriceResponse(BaseModel):
    """Response schema for latest price."""

    index_id: int
    latest_price: Optional[PricePointResponse]
    has_data: bool
