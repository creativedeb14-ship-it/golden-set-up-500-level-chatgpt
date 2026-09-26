import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.strategy.engine import StrategyEngine
from backend.strategy.config import SYMBOLS, STARTING_CAPITAL_USD
from backend.market_data.binance_ws import stream_prices
from backend.database.store import Store
from dataclasses import asdict

capital = float(os.getenv("STARTING_CAPITAL_USD", STARTING_CAPITAL_USD))
engine = StrategyEngine(capital)
store = Store()
stream_task = None



async def handle_price(symbol, price):
    for event in engine.on_price(symbol, price):
        store.log_event(event)
    if events:
        store.save_state(engine.snapshot())

@asynccontextmanager
async def lifespan(app):
    global stream_task, checkpoint_task
    saved = store.load_state()
    if saved:
        engine.restore(saved)
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
    return {"status": "ok", "paper_trading": True, "symbols": list(SYMBOLS)}

@app.get("/api/status")
def status():
    return {
        "capital": engine.capital,
        "prices": engine.last_prices,
        "positions": {s: {**vars(p), "trail": vars(p.trail)} for s, p in engine.positions.items()},
        "daily_trades": {s: engine.count(s) for s in SYMBOLS},
        "events": store.recent_events(50),
    }

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return open("dashboard/index.html", encoding="utf-8").read()
