import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.strategy.engine import StrategyEngine
from backend.strategy.config import SYMBOLS, STARTING_CAPITAL_USD
from backend.market_data.delta_ws import stream_prices
from backend.database.store import Store
from backend.execution.delta_demo import DeltaDemoClient

capital = float(os.getenv("STARTING_CAPITAL_USD", STARTING_CAPITAL_USD))
engine = StrategyEngine(capital)
store = Store()
delta = DeltaDemoClient()
stream_task = None
checkpoint_task = None


async def execute_event(event):
    """Mirror strategy events to Delta Demo only when explicitly enabled.

    The paper engine remains the strategy/accounting source of truth in this
    phase. Delta responses are attached to the event log for reconciliation.
    """
    if not delta.ready:
        return
    event_type = event.get("type")
    symbol = event.get("symbol")
    if event_type == "ENTRY":
        # The engine's notional is exactly the configured 5% allocation.
        contracts = delta.contracts_for_notional(symbol, float(event["price"]), float(event["notional"]))
        response = await asyncio.to_thread(
            delta.place_market,
            symbol,
            event["side"],
            contracts,
            reduce_only=False,
            tag="entry",
        )
        event["delta_demo"] = {"status": "submitted", "contracts": contracts, "response": response}
    elif event_type in ("PARTIAL_EXIT", "EXIT"):
        contracts = delta.contracts_for_coin_qty(symbol, float(event.get("qty", 0)))
        if contracts <= 0:
            event["delta_demo"] = {"status": "skipped", "reason": "qty_below_one_contract"}
            return
        # Exit side is opposite the open position side.
        exit_side = "SHORT" if event.get("side") == "LONG" else "LONG"
        response = await asyncio.to_thread(
            delta.place_market,
            symbol,
            exit_side,
            contracts,
            reduce_only=True,
            tag="partial" if event_type == "PARTIAL_EXIT" else "exit",
        )
        event["delta_demo"] = {"status": "submitted", "contracts": contracts, "response": response}


async def handle_price(symbol, price):
    events = engine.on_price(symbol, price)
    for event in events:
        try:
            await execute_event(event)
        except Exception as exc:
            event["delta_demo"] = {"status": "error", "message": str(exc)}
            if event.get("type") == "ENTRY":
                # Do not leave a paper position open when the corresponding
                # Delta Demo entry could not be submitted.
                engine.rollback_entry(event["symbol"])
        store.log_event(event)
    if events:
        store.save_state(engine.snapshot())


@asynccontextmanager
async def lifespan(app):
    global stream_task, checkpoint_task
    saved = store.load_state()
    if saved:
        engine.restore(saved)

    # Product metadata is public; loading it at startup avoids discovering
    # contract sizes in the middle of an entry event.
    if delta.ready:
        try:
            await asyncio.to_thread(delta.load_products)
            await asyncio.to_thread(delta.account_smoke_test)
            print("Delta Demo authenticated connection: OK")
        except Exception as exc:
            print(f"Delta Demo authenticated connection: FAILED: {exc}")

    stream_task = asyncio.create_task(stream_prices(handle_price))

    async def checkpoint_loop():
        while True:
            await asyncio.sleep(10)
            store.save_state(engine.snapshot())

    checkpoint_task = asyncio.create_task(checkpoint_loop())
    yield
    checkpoint_task.cancel()
    try:
        await checkpoint_task
    except asyncio.CancelledError:
        pass
    stream_task.cancel()
    try:
        await stream_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Golden Setup Paper Bot", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {
        "status": "ok",
        "paper_trading": True,
        "symbols": list(SYMBOLS),
        "delta_demo_enabled": delta.ready,
        "delta_environment": "testnet",
    }


@app.get("/api/status")
def status():
    return {
        "capital": engine.capital,
        "prices": engine.last_prices,
        "positions": {s: {**vars(p), "trail": vars(p.trail)} for s, p in engine.positions.items()},
        "daily_trades": {s: engine.count(s) for s in SYMBOLS},
        "events": store.recent_events(50),
        "delta_demo_enabled": delta.ready,
        "delta_environment": "testnet",
    }


@app.get("/api/delta-status")
def delta_status():
    return {
        "enabled": delta.ready,
        "environment": "testnet",
        "authenticated": bool(delta.ready and delta.products),
        "products": {
            s: {
                "symbol": p.symbol,
                "product_id": p.product_id,
                "contract_value": p.contract_value,
                "tick_size": p.tick_size,
            }
            for s, p in delta.products.items()
        },
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return open("dashboard/index.html", encoding="utf-8").read()
