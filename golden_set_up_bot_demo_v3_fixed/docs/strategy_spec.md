# Strategy Specification v1.0

## Source-derived rules supplied by user

### BTC
- Round interval: 500.
- Buffer after round crossing: 50.
- Initial stop: 150 points from actual entry.
- Minimum profit trigger: 400.
- Initial trailing stop: lock 400 points of profit.
- Further trailing: +150 favorable movement => +150 stop movement.
- Maximum 2 trades/day.

### ETH
- Round interval: 50.
- Buffer: 5.
- Initial stop: 10 points from actual entry.
- Minimum profit trigger: 20+.
- Initial trailing stop: lock 15 points of profit.
- Further trailing: +7 favorable movement => +7 stop movement.
- Maximum 2 trades/day.

### Common
- No candle-close confirmation.
- Entry is based on live price crossing the buffered round trigger.
- Position allocation is 5% of paper capital per trade.
- Fees are deferred.
- Pre-entry price movement cannot count as the trade's SL.

## Explicit test parameter

- Partial exit: 80% at the minimum profit trigger; 20% runner.

## Not implemented / intentionally excluded

- Fixed session/time filter.
- Subjective concepts such as “strong selling”, “junction”, “bull trap”, “bear trap”, or “liquidity sweep” unless later converted into objective rules.
- Live order execution.
