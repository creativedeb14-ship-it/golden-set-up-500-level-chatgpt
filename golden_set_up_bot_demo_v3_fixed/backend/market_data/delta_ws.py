import asyncio
import json
import logging
import websockets

LOG = logging.getLogger(__name__)
WS_URL = "wss://socket-ind-pub.testnet.deltaex.org"

EXCHANGE_TO_INTERNAL = {
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
}


async def stream_prices(on_price):
    """Delta India Demo/Testnet public ticker stream; no API key required."""
    backoff = 1
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                subscribe = {
                    "type": "subscribe",
                    "payload": {
                        "channels": [
                            {"name": "trades", "symbols": ["BTCUSD", "ETHUSD"]}
                        ]
                    },
                }
                await ws.send(json.dumps(subscribe))
                LOG.info("Connected to Delta India Demo market stream")
                backoff = 1
                async for raw in ws:
                    msg = json.loads(raw)
                    symbol = msg.get("sy") or msg.get("symbol")
                    internal = EXCHANGE_TO_INTERNAL.get(symbol)
                    if not internal:
                        continue
                    # Trade channel gives individual trade prices, which is
                    # much closer to the strategy's tick-crossing requirement
                    # than a 5-second ticker snapshot.
                    if msg.get("type") == "trades":
                        price = msg.get("p")
                        if price is not None:
                            await on_price(internal, float(price))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOG.warning("Delta market stream disconnected: %s", exc)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
