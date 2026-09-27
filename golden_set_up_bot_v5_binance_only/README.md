# Golden Setup — 500/50 Level Paper Bot v1

**Paper trading only. No live exchange orders are implemented.**

## Strategy locked for v1

- Symbols: BTCUSDT and ETHUSDT.
- BTC round level: 500 points; buffer: 50 points.
- ETH round level: 50 points; buffer: 5 points.
- No candle-close confirmation: live price crossing the buffered trigger is enough.
- BTC initial SL: 150 points from the actual entry price.
- ETH initial SL: 10 points from the actual entry price.
- Position allocation: exactly 5% of paper capital by notional value per trade.
- Max 2 entries/day per symbol (BTC 2 + ETH 2).
- BTC profit trigger: +400 points. Initial trailing stop locks +400; every further +150 favorable points advances the stop by +150.
- ETH profit trigger: +20 points. Initial trailing stop locks +15; every further +7 favorable points advances the stop by +7.
- Partial exit: 80% at the minimum profit trigger; 20% runner remains. This 80/20 split is a **test parameter**, not a claim about the source video.
- Fees are intentionally excluded in v1 and can be added later.
- Pre-entry price movement can never trigger the position's SL.

## Important execution note

The strategy is tick/price based rather than candle-close based. The public Binance USDⓈ-M aggregate trade stream is used for paper data. Binance documents aggregate trade streams as market-trade updates and recommends WebSocket market streams for live market data. The WebSocket connection is expected to reconnect because individual connections are limited in lifetime.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Render

This repo includes `render.yaml`. Connect the GitHub repository to a Render Web Service and add the Supabase environment variables if you want persistent event/state storage.

Render Free services can spin down after 15 minutes without inbound traffic and have ephemeral local files. Therefore Supabase is recommended for persistent paper-trade state/history; do not rely on SQLite/local files for a six-month record.

## Supabase

Create a free Supabase project, run `supabase.sql`, then add:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Never commit the service-role key to GitHub.

## Before live trading

This version deliberately has no live-order code. Fees, slippage, exchange-specific contract rules, minimum quantities, leverage, liquidation behavior, and order acknowledgements must be tested and explicitly configured before any live integration.


## Binance India Demo execution

The project includes an explicit Binance India Testnet executor. It is OFF by default.

Required Render environment variables:


The strategy remains paper-accounting-first. Binance responses are recorded on ENTRY/PARTIAL_EXIT/EXIT events.
