"""PricePoint model for storing historical index values."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index as SQLIndex
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class PricePoint(Base):
    """Represents a historical price point for an index."""

    __tablename__ = "price_points"

    id = Column(Integer, primary_key=True, index=True)
    index_id = Column(
        Integer,
        ForeignKey("indices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)  # Sum of min prices
    currency = Column(String, default="USD")
    item_count = Column(Integer, nullable=False)  # Number of items in index
    markets_used = Column(Text, nullable=False)  # JSON array of markets queried
    extra_data = Column(Text, nullable=True)  # JSON for additional info (success/failure counts)

    # Relationships
    index = relationship("Index", back_populates="price_points")

    def __repr__(self):
        return f"<PricePoint(index_id={self.index_id}, timestamp={self.timestamp}, value={self.value})>"


# Composite index for efficient time-range queries
SQLIndex("idx_price_points_index_timestamp", PricePoint.index_id, PricePoint.timestamp)
