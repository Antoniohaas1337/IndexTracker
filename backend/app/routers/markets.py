"""Markets router for market information."""

from fastapi import APIRouter
from ..schemas import Market

router = APIRouter()


@router.get("/")
async def get_markets():
    """
    Get list of available markets.

    Returns all supported markets for price queries.
    """
    markets = [
        {
            "id": market.value,
            "name": market.value.replace("_", " ").title(),
        }
        for market in Market
    ]

    return {"markets": markets}
