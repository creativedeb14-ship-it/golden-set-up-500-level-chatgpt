from math import floor, ceil
from .config import SymbolConfig


def levels(price: float, cfg: SymbolConfig) -> dict:
    """Return the nearest lower and upper round levels around the current price."""
    lower = floor(price / cfg.round_size) * cfg.round_size
    upper = ceil(price / cfg.round_size) * cfg.round_size
    if lower == upper:
        upper += cfg.round_size
    return {
        "lower": lower,
        "upper": upper,
        "buy_trigger": upper + cfg.buffer,
        "sell_trigger": lower - cfg.buffer,
    }
