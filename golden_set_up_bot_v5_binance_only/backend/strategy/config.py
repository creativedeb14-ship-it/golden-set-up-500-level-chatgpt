from dataclasses import dataclass

@dataclass(frozen=True)
class SymbolConfig:
    symbol: str
    round_size: float
    buffer: float
    stop_distance: float
    profit_trigger: float
    initial_trail: float
    trail_step: float
    max_trades_per_day: int = 2
    partial_exit_pct: float = 0.80

BTC = SymbolConfig(
    symbol="BTCUSDT", round_size=500.0, buffer=50.0,
    stop_distance=150.0, profit_trigger=400.0,
    initial_trail=400.0, trail_step=150.0,
)

ETH = SymbolConfig(
    symbol="ETHUSDT", round_size=50.0, buffer=5.0,
    stop_distance=10.0, profit_trigger=20.0,
    initial_trail=15.0, trail_step=7.0,
)

SYMBOLS = {BTC.symbol: BTC, ETH.symbol: ETH}
POSITION_ALLOCATION_PCT = 0.05
STARTING_CAPITAL_USD = 10_000.0  # paper-trading default; change in env/dashboard
# Fees intentionally excluded for v1 because user asked to add them later.
