from dataclasses import dataclass, field
from datetime import datetime, timezone
from .config import SYMBOLS, SymbolConfig
from .round_levels import levels
from .risk import initial_stop, position_qty
from .trailing import TrailState, update_trailing

@dataclass
class Position:
    symbol: str
    side: str
    entry: float
    qty: float
    notional: float
    stop: float
    opened_at: str
    trail: TrailState = field(default_factory=TrailState)
    partial_closed: bool = False
    realized_pnl: float = 0.0

class StrategyEngine:
    def __init__(self, capital: float):
        self.capital = capital
        self.positions: dict[str, Position] = {}
        self.daily_counts: dict[tuple[str, str], int] = {}
        self.last_prices: dict[str, float] = {}
        self.armed_levels: dict[str, dict | None] = {s: None for s in SYMBOLS}

    def _day(self):
        return datetime.now(timezone.utc).date().isoformat()

    def count(self, symbol: str) -> int:
        return self.daily_counts.get((symbol, self._day()), 0)

    def _increment(self, symbol: str):
        k = (symbol, self._day())
        self.daily_counts[k] = self.daily_counts.get(k, 0) + 1

    def snapshot(self):
        return {
            "capital": self.capital,
            "positions": {
                s: {
                    "symbol": p.symbol, "side": p.side, "entry": p.entry,
                    "qty": p.qty, "notional": p.notional, "stop": p.stop,
                    "opened_at": p.opened_at, "partial_closed": p.partial_closed,
                    "realized_pnl": p.realized_pnl,
                    "trail": vars(p.trail),
                } for s, p in self.positions.items()
            },
            "daily_counts": {f"{s}|{d}": n for (s, d), n in self.daily_counts.items()},
            "armed_levels": self.armed_levels,
        }

    def restore(self, state: dict):
        if not state:
            return
        self.capital = float(state.get("capital", self.capital))
        self.positions = {}
        for s, raw in state.get("positions", {}).items():
            trail_raw = raw.get("trail", {})
            trail = TrailState(**trail_raw)
            self.positions[s] = Position(
                symbol=raw["symbol"], side=raw["side"], entry=float(raw["entry"]),
                qty=float(raw["qty"]), notional=float(raw["notional"]),
                stop=float(raw["stop"]), opened_at=raw["opened_at"], trail=trail,
                partial_closed=bool(raw.get("partial_closed", False)),
                realized_pnl=float(raw.get("realized_pnl", 0.0)),
            )
        self.armed_levels = state.get("armed_levels", {s: None for s in SYMBOLS})
        self.daily_counts = {}
        for k, n in state.get("daily_counts", {}).items():
            s, d = k.split("|", 1)
            self.daily_counts[(s, d)] = int(n)

    def rollback_entry(self, symbol: str):
        """Remove a newly-created entry after an execution-layer failure."""
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return
        key = (symbol, self._day())
        current = self.daily_counts.get(key, 0)
        self.daily_counts[key] = max(0, current - 1)
        self.armed_levels[symbol] = None

    def on_price(self, symbol: str, price: float):
        cfg: SymbolConfig = SYMBOLS[symbol]
        self.last_prices[symbol] = price
        events = []
        pos = self.positions.get(symbol)

        # Manage an already-open position first. Pre-entry movement can never trigger its SL.
        if pos:
            old_stop = pos.stop
            was_trailing = pos.trail.active
            pos.trail = update_trailing(pos.entry, price, pos.side, pos.trail, cfg)
            if pos.trail.active and pos.trail.stop is not None:
                if pos.side == "LONG":
                    pos.stop = max(pos.stop, pos.trail.stop)
                else:
                    pos.stop = min(pos.stop, pos.trail.stop)

            # Partial exit once minimum profit threshold is reached.
            if not pos.partial_closed:
                profit = (price - pos.entry) if pos.side == "LONG" else (pos.entry - price)
                if profit >= cfg.profit_trigger:
                    partial_qty = pos.qty * cfg.partial_exit_pct
                    pnl = (price - pos.entry) * partial_qty if pos.side == "LONG" else (pos.entry - price) * partial_qty
                    pos.qty -= partial_qty
                    pos.realized_pnl += pnl
                    pos.partial_closed = True
                    events.append({"type": "PARTIAL_EXIT", "symbol": symbol, "side": pos.side, "price": price, "qty": partial_qty, "pnl": pnl})

            # A newly advanced trailing stop becomes active for the NEXT price
            # update. This prevents the bot from raising a stop to the current
            # tick and immediately filling itself at that same tick.
            effective_stop = old_stop if (pos.trail.active and not was_trailing and pos.stop != old_stop) else (old_stop if pos.trail.active and pos.stop != old_stop else pos.stop)
            stopped = (price <= effective_stop) if pos.side == "LONG" else (price >= effective_stop)
            if stopped:
                pnl = (price - pos.entry) * pos.qty if pos.side == "LONG" else (pos.entry - price) * pos.qty
                total = pos.realized_pnl + pnl
                events.append({"type": "EXIT", "symbol": symbol, "side": pos.side, "price": price, "qty": pos.qty, "pnl": total, "reason": "TRAIL_OR_SL" if pos.trail.active else "INITIAL_SL", "old_stop": old_stop})
                self.capital += total
                del self.positions[symbol]
                self.armed_levels[symbol] = None
            return events

        # No position: arm the nearest round levels once, then wait for the
        # buffered trigger. We must NOT recalculate the levels on every tick,
        # otherwise a price crossing the round number would move the target
        # to the next round before the trigger can fire.
        if self.armed_levels.get(symbol) is None:
            self.armed_levels[symbol] = levels(price, cfg)
        lv = self.armed_levels[symbol]
        side = None
        if price >= lv["buy_trigger"]:
            side = "LONG"
        elif price <= lv["sell_trigger"]:
            side = "SHORT"

        if side and self.count(symbol) < cfg.max_trades_per_day:
            qty, notional = position_qty(self.capital, price)
            stop = initial_stop(price, side, cfg)
            pos = Position(
                symbol=symbol, side=side, entry=price, qty=qty,
                notional=notional, stop=stop,
                opened_at=datetime.now(timezone.utc).isoformat()
            )
            self.positions[symbol] = pos
            self._increment(symbol)
            events.append({"type": "ENTRY", "symbol": symbol, "side": side, "price": price, "qty": qty, "notional": notional, "stop": stop, "levels": lv})
        return events
