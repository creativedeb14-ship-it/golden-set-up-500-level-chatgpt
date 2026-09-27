from .round_levels import levels
from .config import SymbolConfig


def signal(price: float, cfg: SymbolConfig, armed_side: str | None = None) -> tuple[str | None, dict]:
    """No candle-close requirement. Trigger is crossed by live price + buffer."""
    lv = levels(price, cfg)
    side = None
    if price >= lv["buy_trigger"]:
        side = "LONG"
    elif price <= lv["sell_trigger"]:
        side = "SHORT"
    return side, lv
