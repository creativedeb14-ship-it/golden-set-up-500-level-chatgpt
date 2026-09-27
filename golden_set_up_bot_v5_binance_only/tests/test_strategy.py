from backend.strategy.config import BTC, ETH
from backend.strategy.round_levels import levels
from backend.strategy.engine import StrategyEngine


def test_btc_levels_example():
    x = levels(87456, BTC)
    assert x["upper"] == 87500
    assert x["lower"] == 87000
    assert x["buy_trigger"] == 87550
    assert x["sell_trigger"] == 86950


def test_eth_levels():
    x = levels(3256, ETH)
    assert x["upper"] == 3300
    assert x["lower"] == 3250
    assert x["buy_trigger"] == 3305
    assert x["sell_trigger"] == 3245


def test_entry_and_pre_entry_movement_do_not_sl():
    e = StrategyEngine(10000)
    assert e.on_price("BTCUSDT", 87400) == []
    events = e.on_price("BTCUSDT", 87550)
    assert events[0]["type"] == "ENTRY"
    assert events[0]["stop"] == 87400


def test_btc_partial_and_trailing():
    e = StrategyEngine(10000)
    e.on_price("BTCUSDT", 87456)
    e.on_price("BTCUSDT", 87550)
    events = e.on_price("BTCUSDT", 87950)
    assert any(x["type"] == "PARTIAL_EXIT" for x in events)
    assert e.positions["BTCUSDT"].stop == 87950
    e.on_price("BTCUSDT", 88100)
    assert e.positions["BTCUSDT"].stop == 88100


def test_eth_stop_is_entry_based():
    e = StrategyEngine(10000)
    e.on_price("ETHUSDT", 3256)
    e.on_price("ETHUSDT", 3305)
    assert e.positions["ETHUSDT"].stop == 3295
