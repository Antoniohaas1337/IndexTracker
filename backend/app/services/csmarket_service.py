"""CSMarketAPI service wrapper with error handling and batching."""

import asyncio
import logging
from typing import Dict, List, Optional
from csmarketapi import CSMarketAPI
from csmarketapi.enums import Market as CSMarket, Currency as CSCurrency
from ..config import settings

logger = logging.getLogger(__name__)


class CSMarketService:
    """Wrapper service for CSMarketAPI with batching and error handling."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the service with API key."""
        self.api_key = api_key or settings.CSMARKET_API_KEY
        self._client: Optional[CSMarketAPI] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = CSMarketAPI(self.api_key)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_all_items(self):
        """Fetch all CS:GO items from the API."""
        try:
            logger.info("Fetching all items from CSMarketAPI...")
            items_response = await self._client.get_items()
            logger.info(f"Successfully fetched {len(items_response.items)} items")
            return items_response
        except Exception as e:
            logger.error(f"Failed to fetch items: {e}")
            raise

    async def get_available_markets(self):
        """Fetch available markets information."""
        try:
            logger.info("Fetching markets from CSMarketAPI...")
            markets_response = await self._client.get_markets()
            logger.info(f"Successfully fetched {len(markets_response.items)} markets")
            return markets_response
        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            raise

    async def batch_get_min_prices(
        self,
        item_market_hash_names: List[str],
        markets: List[str],
        currency: str = "USD",
        max_concurrent: int = 10,
    ) -> Dict[str, Optional[float]]:
        """
        Fetch min prices for multiple items in parallel with rate limiting.

        This is the core method for price fetching. It queries the CSMarketAPI
        for each item and extracts the MINIMUM price across all specified markets.

        Args:
            item_market_hash_names: List of item market hash names
            markets: List of market names (e.g., ["STEAMCOMMUNITY", "SKINPORT"])
            currency: Currency code (default: USD)
            max_concurrent: Maximum concurrent API requests (default: 10)

        Returns:
            Dictionary mapping market_hash_name to min_price (or None if failed)
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        # Convert market strings to CSMarket enums
        try:
            market_enums = [CSMarket[m] for m in markets]
        except KeyError as e:
            logger.error(f"Invalid market name: {e}")
            raise ValueError(f"Invalid market name: {e}")

        # Convert currency string to CSCurrency enum
        try:
            currency_enum = CSCurrency[currency.upper()]
        except KeyError:
            logger.error(f"Invalid currency: {currency}")
            raise ValueError(f"Invalid currency: {currency}")

        async def fetch_single(name: str) -> tuple[str, Optional[float]]:
            """Fetch min price for a single item."""
            async with semaphore:
                try:
                    data = await self._client.get_listings_latest_aggregated(
                        market_hash_name=name,
                        markets=market_enums,
                        currency=currency_enum,
                    )

                    # Extract min price across all requested markets
                    min_price = None
                    for listing in data.listings:
                        if listing.min_price is not None:
                            if min_price is None or listing.min_price < min_price:
                                min_price = listing.min_price

                    logger.debug(f"Fetched min price for '{name}': ${min_price}")
                    return (name, min_price)

                except Exception as e:
                    logger.error(f"Failed to fetch price for '{name}': {e}")
                    return (name, None)

        # Execute all requests in parallel
        logger.info(
            f"Fetching min prices for {len(item_market_hash_names)} items "
            f"across {len(markets)} markets with {max_concurrent} concurrent requests"
        )

        tasks = [fetch_single(name) for name in item_market_hash_names]
        results_list = await asyncio.gather(*tasks)

        results = dict(results_list)

        # Log summary
        succeeded = sum(1 for price in results.values() if price is not None)
        failed = len(results) - succeeded
        logger.info(
            f"Price fetch complete: {succeeded} succeeded, {failed} failed out of {len(results)}"
        )

        return results

    async def get_listing_history(
        self,
        market_hash_name: str,
        markets: List[str],
        currency: str = "USD",
    ):
        """
        Fetch listing history for a single item.

        Args:
            market_hash_name: Item market hash name
            markets: List of market names
            currency: Currency code

        Returns:
            ListingsHistoryAggregated response
        """
        try:
            market_enums = [CSMarket[m] for m in markets]
            currency_enum = CSCurrency[currency.upper()]

            history = await self._client.get_listings_history_aggregated(
                market_hash_name=market_hash_name,
                markets=market_enums,
                currency=currency_enum,
            )

            logger.debug(
                f"Fetched listing history for '{market_hash_name}': "
                f"{len(history.items)} data points"
            )

            return history

        except Exception as e:
            logger.error(f"Failed to fetch listing history for '{market_hash_name}': {e}")
            raise


def get_csmarket_service() -> CSMarketService:
    """Dependency for getting CSMarketService instance."""
    return CSMarketService()
