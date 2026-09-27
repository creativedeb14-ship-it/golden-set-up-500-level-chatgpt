import asyncio, json, logging
import websockets

LOG = logging.getLogger(__name__)
WS_URL = "wss://fstream.binance.com/stream?streams=btcusdt@aggTrade/ethusdt@aggTrade"

async def stream_prices(on_price):
    """Public Binance USDⓈ-M aggregate-trade stream; no API key required."""
    backoff = 1
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                LOG.info("Connected to Binance market stream")
                backoff = 1
                async for raw in ws:
                    msg = json.loads(raw)
                    data = msg.get("data", msg)
                    symbol = data.get("s")
                    price = data.get("p")
                    if symbol in ("BTCUSDT", "ETHUSDT") and price:
                        await on_price(symbol, float(price))
        except Exception as exc:
            LOG.warning("Market stream disconnected: %s", exc)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
