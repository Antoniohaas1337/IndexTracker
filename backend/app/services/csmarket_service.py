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
        max_concurrent: int = 50,
        on_progress=None,
    ) -> Dict[str, Optional[float]]:
        """
        Fetch min prices for multiple items in parallel with rate limiting.

        This is the core method for price fetching. It queries the CSMarketAPI
        for each item and extracts the MINIMUM price across all specified markets.

        Args:
            item_market_hash_names: List of item market hash names
            markets: List of market names (e.g., ["STEAMCOMMUNITY", "SKINPORT"])
            currency: Currency code (default: USD)
            max_concurrent: Maximum concurrent API requests (default: 50)
            on_progress: Optional callback function(completed, total) for progress tracking

        Returns:
            Dictionary mapping market_hash_name to min_price (or None if failed)
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0
        total_count = len(item_market_hash_names)
        current_delay = 0  # Adaptive delay in seconds
        max_delay = 5  # Maximum delay between retries

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
            """Fetch min price for a single item with adaptive retry."""
            nonlocal completed_count, current_delay

            async with semaphore:
                retry_count = 0
                max_retries = 5

                while retry_count < max_retries:
                    try:
                        # Apply adaptive delay if needed
                        if current_delay > 0:
                            await asyncio.sleep(current_delay)

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

                        # Success - reduce delay
                        if current_delay > 0:
                            current_delay = max(0, current_delay - 0.1)

                        completed_count += 1
                        if on_progress:
                            on_progress(completed_count, total_count)

                        logger.debug(f"Fetched min price for '{name}': ${min_price}")
                        return (name, min_price)

                    except Exception as e:
                        error_msg = str(e)

                        # Check if it's a rate limit error
                        if "429" in error_msg or "rate limit" in error_msg.lower():
                            retry_count += 1
                            # Increase delay adaptively
                            current_delay = min(max_delay, current_delay + 0.5)
                            wait_time = current_delay * (2 ** retry_count)
                            logger.warning(
                                f"Rate limit hit for '{name}'. "
                                f"Retry {retry_count}/{max_retries} after {wait_time:.1f}s"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            # Non-rate-limit error, fail immediately
                            logger.error(f"Failed to fetch price for '{name}': {e}")
                            completed_count += 1
                            if on_progress:
                                on_progress(completed_count, total_count)
                            return (name, None)

                # Max retries exceeded
                logger.error(f"Failed to fetch price for '{name}' after {max_retries} retries")
                completed_count += 1
                if on_progress:
                    on_progress(completed_count, total_count)
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

    async def get_sales_history(
        self,
        market_hash_name: str,
        markets: List[str],
        currency: str = "USD",
    ):
        """
        Fetch sales history for a single item.

        Args:
            market_hash_name: Item market hash name
            markets: List of market names
            currency: Currency code

        Returns:
            SalesHistoryAggregated response
        """
        try:
            market_enums = [CSMarket[m] for m in markets]
            currency_enum = CSCurrency[currency.upper()]

            history = await self._client.get_sales_history_aggregated(
                market_hash_name=market_hash_name,
                markets=market_enums,
                currency=currency_enum,
            )

            logger.debug(
                f"Fetched sales history for '{market_hash_name}': "
                f"{len(history.items)} data points"
            )

            return history

        except Exception as e:
            logger.error(f"Failed to fetch sales history for '{market_hash_name}': {e}")
            raise

    async def batch_get_listing_history(
        self,
        item_market_hash_names: List[str],
        markets: List[str],
        currency: str = "USD",
        max_concurrent: int = 50,
        on_progress=None,
    ) -> Dict[str, Optional[any]]:
        """
        Fetch listing history for multiple items in parallel with adaptive rate limiting.

        Args:
            item_market_hash_names: List of item market hash names
            markets: List of market names
            currency: Currency code (default: USD)
            max_concurrent: Maximum concurrent API requests (default: 50)
            on_progress: Optional callback function(completed, total) for progress tracking

        Returns:
            Dictionary mapping market_hash_name to history response (or None if failed)
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0
        total_count = len(item_market_hash_names)
        current_delay = 0  # Adaptive delay in seconds
        max_delay = 5  # Maximum delay between retries

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

        async def fetch_single_history(name: str) -> tuple[str, Optional[any]]:
            """Fetch listing history for a single item with adaptive retry."""
            nonlocal completed_count, current_delay

            async with semaphore:
                retry_count = 0
                max_retries = 5

                while retry_count < max_retries:
                    try:
                        # Apply adaptive delay if needed
                        if current_delay > 0:
                            await asyncio.sleep(current_delay)

                        history = await self._client.get_listings_history_aggregated(
                            market_hash_name=name,
                            markets=market_enums,
                            currency=currency_enum,
                        )

                        # Success - reduce delay
                        if current_delay > 0:
                            current_delay = max(0, current_delay - 0.1)

                        completed_count += 1
                        if on_progress:
                            on_progress(completed_count, total_count)

                        logger.debug(
                            f"Fetched listing history for '{name}': "
                            f"{len(history.items)} data points"
                        )
                        return (name, history)

                    except Exception as e:
                        error_msg = str(e)

                        # Check if it's a rate limit error
                        if "429" in error_msg or "rate limit" in error_msg.lower():
                            retry_count += 1
                            # Increase delay adaptively
                            current_delay = min(max_delay, current_delay + 0.5)
                            wait_time = current_delay * (2 ** retry_count)
                            logger.warning(
                                f"Rate limit hit for '{name}'. "
                                f"Retry {retry_count}/{max_retries} after {wait_time:.1f}s"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            # Non-rate-limit error, fail immediately
                            logger.error(f"Failed to fetch history for '{name}': {e}")
                            completed_count += 1
                            if on_progress:
                                on_progress(completed_count, total_count)
                            return (name, None)

                # Max retries exceeded
                logger.error(f"Failed to fetch history for '{name}' after {max_retries} retries")
                completed_count += 1
                if on_progress:
                    on_progress(completed_count, total_count)
                return (name, None)

        # Execute all requests in parallel
        logger.info(
            f"Fetching listing history for {len(item_market_hash_names)} items "
            f"across {len(markets)} markets with {max_concurrent} concurrent requests"
        )

        tasks = [fetch_single_history(name) for name in item_market_hash_names]
        results_list = await asyncio.gather(*tasks)

        results = dict(results_list)

        # Log summary
        succeeded = sum(1 for hist in results.values() if hist is not None)
        failed = len(results) - succeeded
        logger.info(
            f"Listing history fetch complete: {succeeded} succeeded, {failed} failed out of {len(results)}"
        )

        return results

    async def batch_get_sales_history(
        self,
        item_market_hash_names: List[str],
        markets: List[str],
        currency: str = "USD",
        max_concurrent: int = 50,
        on_progress=None,
    ) -> Dict[str, Optional[any]]:
        """
        Fetch sales history for multiple items in parallel with adaptive rate limiting.

        Args:
            item_market_hash_names: List of item market hash names
            markets: List of market names
            currency: Currency code (default: USD)
            max_concurrent: Maximum concurrent API requests (default: 50)
            on_progress: Optional callback function(completed, total) for progress tracking

        Returns:
            Dictionary mapping market_hash_name to sales history response (or None if failed)
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0
        total_count = len(item_market_hash_names)
        current_delay = 0  # Adaptive delay in seconds
        max_delay = 5  # Maximum delay between retries

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

        async def fetch_single_sales_history(name: str) -> tuple[str, Optional[any]]:
            """Fetch sales history for a single item with adaptive retry."""
            nonlocal completed_count, current_delay

            async with semaphore:
                retry_count = 0
                max_retries = 5

                while retry_count < max_retries:
                    try:
                        # Apply adaptive delay if needed
                        if current_delay > 0:
                            await asyncio.sleep(current_delay)

                        history = await self._client.get_sales_history_aggregated(
                            market_hash_name=name,
                            markets=market_enums,
                            currency=currency_enum,
                        )

                        # Success - reduce delay
                        if current_delay > 0:
                            current_delay = max(0, current_delay - 0.1)

                        completed_count += 1
                        if on_progress:
                            on_progress(completed_count, total_count)

                        logger.debug(
                            f"Fetched sales history for '{name}': "
                            f"{len(history.items)} data points"
                        )
                        return (name, history)

                    except Exception as e:
                        error_msg = str(e)

                        # Check if it's a rate limit error
                        if "429" in error_msg or "rate limit" in error_msg.lower():
                            retry_count += 1
                            # Increase delay adaptively
                            current_delay = min(max_delay, current_delay + 0.5)
                            wait_time = current_delay * (2 ** retry_count)
                            logger.warning(
                                f"Rate limit hit for '{name}'. "
                                f"Retry {retry_count}/{max_retries} after {wait_time:.1f}s"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            # Non-rate-limit error, fail immediately
                            logger.error(f"Failed to fetch sales history for '{name}': {e}")
                            completed_count += 1
                            if on_progress:
                                on_progress(completed_count, total_count)
                            return (name, None)

                # Max retries exceeded
                logger.error(f"Failed to fetch sales history for '{name}' after {max_retries} retries")
                completed_count += 1
                if on_progress:
                    on_progress(completed_count, total_count)
                return (name, None)

        # Execute all requests in parallel
        logger.info(
            f"Fetching sales history for {len(item_market_hash_names)} items "
            f"across {len(markets)} markets with {max_concurrent} concurrent requests"
        )

        tasks = [fetch_single_sales_history(name) for name in item_market_hash_names]
        results_list = await asyncio.gather(*tasks)

        results = dict(results_list)

        # Log summary
        succeeded = sum(1 for hist in results.values() if hist is not None)
        failed = len(results) - succeeded
        logger.info(
            f"Sales history fetch complete: {succeeded} succeeded, {failed} failed out of {len(results)}"
        )

        return results


def get_csmarket_service() -> CSMarketService:
    """Dependency for getting CSMarketService instance."""
    return CSMarketService()
