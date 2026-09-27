from dataclasses import dataclass
from .config import SymbolConfig

@dataclass
class TrailState:
    active: bool = False
    stop: float | None = None
    next_step_price: float | None = None
    last_step_index: int = 0


def update_trailing(entry: float, price: float, side: str, state: TrailState, cfg: SymbolConfig) -> TrailState:
    """Trail only after the symbol's minimum profit trigger is reached.

    Once activated, the initial stop locks the minimum profit threshold.
    Thereafter, every additional trail_step of favorable movement advances the
    stop by trail_step. No candle-close dependency is used.
    """
    if side == "LONG":
        profit = price - entry
        if not state.active and profit >= cfg.profit_trigger:
            state.active = True
            state.stop = entry + cfg.initial_trail
            state.next_step_price = entry + cfg.profit_trigger + cfg.trail_step
            state.last_step_index = 0
        elif state.active and price >= (state.next_step_price or float("inf")):
            steps = int((price - (entry + cfg.profit_trigger)) // cfg.trail_step)
            if steps > state.last_step_index:
                state.last_step_index = steps
                state.stop = entry + cfg.initial_trail + steps * cfg.trail_step
                state.next_step_price = entry + cfg.profit_trigger + (steps + 1) * cfg.trail_step
    else:
        profit = entry - price
        if not state.active and profit >= cfg.profit_trigger:
            state.active = True
            state.stop = entry - cfg.initial_trail
            state.next_step_price = entry - cfg.profit_trigger - cfg.trail_step
            state.last_step_index = 0
        elif state.active and price <= (state.next_step_price or -float("inf")):
            steps = int(((entry - cfg.profit_trigger) - price) // cfg.trail_step)
            if steps > state.last_step_index:
                state.last_step_index = steps
                state.stop = entry - cfg.initial_trail - steps * cfg.trail_step
                state.next_step_price = entry - cfg.profit_trigger - (steps + 1) * cfg.trail_step
    return state
