"""Common schemas and enums."""

from enum import Enum


class IndexType(str, Enum):
    """Type of index."""

    CUSTOM = "CUSTOM"
    PREBUILT = "PREBUILT"


class Market(str, Enum):
    """Available markets for price queries."""

    STEAMCOMMUNITY = "STEAMCOMMUNITY"
    BUFFMARKET = "BUFFMARKET"
    SKINS = "SKINS"
    SKINPORT = "SKINPORT"
    MARKETCSGO = "MARKETCSGO"
    DMARKET = "DMARKET"
    GAMERPAYGG = "GAMERPAYGG"
    CSDEALS = "CSDEALS"
    SKINBARON = "SKINBARON"
    CSFLOAT = "CSFLOAT"
    CSMONEY = "CSMONEY"
    WHITEMARKET = "WHITEMARKET"


class Currency(str, Enum):
    """Supported currencies."""

    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"
    RUB = "RUB"
    INR = "INR"
