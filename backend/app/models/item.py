"""Item model for storing CS:GO item data."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index as SQLIndex
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Item(Base):
    """Represents a CS:GO item with metadata from CSMarketAPI."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    market_hash_name = Column(String, unique=True, nullable=False, index=True)
    hash_name = Column(String, nullable=False)
    nameid = Column(Integer, nullable=True)
    classid = Column(String, nullable=True)
    exterior = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    weapon = Column(String, nullable=True, index=True)
    type = Column(String, nullable=True, index=True)
    quality = Column(String, nullable=True)
    collection = Column(String, nullable=True)
    sticker_type = Column(String, nullable=True)
    graffiti_type = Column(String, nullable=True)
    patch_type = Column(String, nullable=True)
    min_float = Column(Float, nullable=True)
    max_float = Column(Float, nullable=True)
    icon_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    index_associations = relationship(
        "IndexItem", back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.market_hash_name}')>"


# Additional indexes for common query patterns
SQLIndex("idx_items_type_category", Item.type, Item.category)
SQLIndex("idx_items_weapon_exterior", Item.weapon, Item.exterior)
