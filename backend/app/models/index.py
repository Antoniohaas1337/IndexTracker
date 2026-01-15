"""Index and IndexItem models for tracking CS:GO item collections."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Index(Base):
    """Represents a collection of items to track (custom or prebuilt)."""

    __tablename__ = "indices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=False, index=True)  # CUSTOM or PREBUILT
    category = Column(String, nullable=True, index=True)  # For prebuilt indices
    selected_markets = Column(Text, nullable=False)  # JSON array of market enums
    currency = Column(String, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("type IN ('CUSTOM', 'PREBUILT')", name="check_index_type"),
    )

    # Relationships
    item_associations = relationship(
        "IndexItem", back_populates="index", cascade="all, delete-orphan"
    )
    price_points = relationship(
        "PricePoint", back_populates="index", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Index(id={self.id}, name='{self.name}', type={self.type})>"


class IndexItem(Base):
    """Many-to-many relationship between indices and items."""

    __tablename__ = "index_items"

    id = Column(Integer, primary_key=True, index=True)
    index_id = Column(
        Integer,
        ForeignKey("indices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("index_id", "item_id", name="unique_index_item"),)

    # Relationships
    index = relationship("Index", back_populates="item_associations")
    item = relationship("Item", back_populates="index_associations")

    def __repr__(self):
        return f"<IndexItem(index_id={self.index_id}, item_id={self.item_id})>"
