from .config import POSITION_ALLOCATION_PCT, SymbolConfig


def position_qty(capital: float, entry: float) -> tuple[float, float]:
    """Allocate exactly 5% of paper capital by notional value."""
    allocation = capital * POSITION_ALLOCATION_PCT
    if entry <= 0:
        raise ValueError("Entry price must be positive")
    return allocation / entry, allocation


def initial_stop(entry: float, side: str, cfg: SymbolConfig) -> float:
    if side == "LONG":
        return entry - cfg.stop_distance
    if side == "SHORT":
        return entry + cfg.stop_distance
    raise ValueError("side must be LONG or SHORT")
