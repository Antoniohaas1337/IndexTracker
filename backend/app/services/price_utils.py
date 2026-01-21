"""Utility functions for robust price calculations.

This module provides helper functions for handling illiquidity in price data:
- Outlier removal using median-based filtering
- Volume-weighted price aggregation
- Fallback price calculation for stale data
"""

import statistics
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple


@dataclass
class SaleRecord:
    """Single sale record from a marketplace."""
    market: str
    price: float
    volume: int


@dataclass
class DailySaleData:
    """Sales data for a single day."""
    day: date
    sales: List[SaleRecord] = field(default_factory=list)


@dataclass
class ItemPriceState:
    """State tracking for an item during price calculation."""
    item_id: int
    market_hash_name: str
    last_known_price: Optional[float] = None
    last_sale_date: Optional[date] = None
    price_history: List[Tuple[date, float]] = field(default_factory=list)


def remove_outliers(prices: List[float], threshold: float = 0.25) -> List[float]:
    """
    Remove prices outside ±threshold from the median.

    Args:
        prices: List of prices to filter
        threshold: Percentage threshold (0.25 = ±25% from median)

    Returns:
        Filtered list of prices with outliers removed

    Example:
        >>> remove_outliers([100, 105, 110, 200, 95])  # 200 is outlier
        [100, 105, 110, 95]
    """
    if len(prices) < 3:
        return prices

    median = statistics.median(prices)
    lower = median * (1 - threshold)
    upper = median * (1 + threshold)

    return [p for p in prices if lower <= p <= upper]


def remove_outliers_with_volume(
    prices: List[float],
    volumes: List[int],
    threshold: float = 0.25
) -> Tuple[List[float], List[int]]:
    """
    Remove outliers while preserving corresponding volume data.

    Args:
        prices: List of prices
        volumes: Corresponding list of volumes
        threshold: Percentage threshold for outlier detection

    Returns:
        Tuple of (filtered_prices, filtered_volumes)
    """
    if len(prices) < 3 or len(prices) != len(volumes):
        return prices, volumes

    median = statistics.median(prices)
    lower = median * (1 - threshold)
    upper = median * (1 + threshold)

    filtered_prices = []
    filtered_volumes = []

    for price, volume in zip(prices, volumes):
        if lower <= price <= upper:
            filtered_prices.append(price)
            filtered_volumes.append(volume)

    # If all prices were filtered out, return original data
    if not filtered_prices:
        return prices, volumes

    return filtered_prices, filtered_volumes


def volume_weighted_price(sales: List[SaleRecord]) -> Optional[float]:
    """
    Calculate volume-weighted average price from sales records.

    Args:
        sales: List of SaleRecord objects with price and volume

    Returns:
        Volume-weighted average price, or None if no valid data

    Example:
        >>> sales = [SaleRecord('A', 100, 10), SaleRecord('B', 110, 5)]
        >>> volume_weighted_price(sales)
        103.33...  # (100*10 + 110*5) / 15
    """
    if not sales:
        return None

    total_volume = sum(s.volume for s in sales if s.volume > 0)

    if total_volume == 0:
        # Fall back to simple average if no volume data
        prices = [s.price for s in sales if s.price is not None]
        return statistics.mean(prices) if prices else None

    weighted_sum = sum(s.price * s.volume for s in sales if s.volume > 0 and s.price is not None)
    return weighted_sum / total_volume


def volume_weighted_price_simple(
    prices: List[float],
    volumes: List[int]
) -> Optional[float]:
    """
    Calculate volume-weighted average price from parallel lists.

    Args:
        prices: List of prices
        volumes: Corresponding list of volumes

    Returns:
        Volume-weighted average price, or None if no valid data
    """
    if not prices or len(prices) != len(volumes):
        return None

    total_volume = sum(v for v in volumes if v > 0)

    if total_volume == 0:
        # Fall back to simple average if no volume data
        return statistics.mean(prices) if prices else None

    weighted_sum = sum(p * v for p, v in zip(prices, volumes) if v > 0)
    return weighted_sum / total_volume


def get_fallback_price(
    price_history: List[Tuple[date, float]],
    current_listing_price: Optional[float] = None,
    n_median: int = 5
) -> Optional[float]:
    """
    Calculate fallback price for stale data.

    Strategy:
    1. Use median of last N sales if available
    2. Fall back to current listing price if provided
    3. Return None if no data available

    Args:
        price_history: List of (date, price) tuples
        current_listing_price: Optional current listing price
        n_median: Number of recent prices to use for median

    Returns:
        Fallback price or None
    """
    if price_history:
        # Sort by date descending and take last N
        sorted_history = sorted(price_history, key=lambda x: x[0], reverse=True)
        recent_prices = [p for _, p in sorted_history[:n_median]]

        if recent_prices:
            return statistics.median(recent_prices)

    return current_listing_price


def calculate_daily_item_price(
    sales: List[SaleRecord],
    outlier_threshold: float = 0.25
) -> Optional[float]:
    """
    Calculate the price for an item on a given day.

    Algorithm:
    1. Extract all prices and volumes from sales
    2. Remove outliers (±threshold from median)
    3. Calculate volume-weighted average

    Args:
        sales: List of sales for the day
        outlier_threshold: Threshold for outlier removal

    Returns:
        Calculated price or None if no valid data
    """
    if not sales:
        return None

    prices = [s.price for s in sales if s.price is not None and s.price > 0]
    volumes = [s.volume for s in sales if s.price is not None and s.price > 0]

    if not prices:
        return None

    # Remove outliers
    filtered_prices, filtered_volumes = remove_outliers_with_volume(
        prices, volumes, outlier_threshold
    )

    # Calculate volume-weighted price
    return volume_weighted_price_simple(filtered_prices, filtered_volumes)
