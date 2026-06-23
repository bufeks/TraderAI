from traderai.brokers.base import Balance, BrokerError
from traderai.brokers.bitflyer import value_balances


def _fake_ticker(product_code: str) -> float:
    table = {"BTC_JPY": 10_000_000.0, "ETH_JPY": 280_000.0}
    if product_code not in table:
        raise BrokerError(f"no ticker for {product_code}")
    return table[product_code]


def test_value_balances_crypto():
    balances = [Balance("BTC", 0.0004942), Balance("ETH", 0.01082424)]
    valued = value_balances(balances, ticker_fn=_fake_ticker)
    assert valued[0][0] == "BTC"
    assert abs(valued[0][2] - 0.0004942 * 10_000_000) < 1e-6
    assert abs(valued[1][2] - 0.01082424 * 280_000) < 1e-6


def test_value_balances_jpy_passthrough():
    valued = value_balances([Balance("JPY", 5000)], ticker_fn=_fake_ticker)
    assert valued[0] == ("JPY", 5000, 5000)


def test_value_balances_missing_ticker_is_none():
    valued = value_balances([Balance("LSK", 2)], ticker_fn=_fake_ticker)
    assert valued[0][0] == "LSK"
    assert valued[0][2] is None
