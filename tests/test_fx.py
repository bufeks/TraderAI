from traderai import fx


def test_same_currency_is_identity(monkeypatch):
    assert fx.convert(1000, "JPY", "JPY") == 1000
    assert fx.fx_rate("JPY", "JPY") == 1.0


def test_convert_uses_rate(monkeypatch):
    # fx_rate をモックして為替依存を排除
    fx.fx_rate.cache_clear()
    monkeypatch.setattr(fx, "fx_rate", lambda base, quote="JPY": 160.0)
    assert fx.convert(10, "USD", "JPY") == 1600.0


def test_convert_case_insensitive(monkeypatch):
    monkeypatch.setattr(fx, "fx_rate", lambda base, quote="JPY": 160.0)
    assert fx.convert(1, "usd", "jpy") == 160.0
