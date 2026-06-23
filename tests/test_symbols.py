from traderai.symbols import to_yahoo_symbol


def test_japanese_code_gets_t_suffix():
    assert to_yahoo_symbol("7203") == "7203.T"
    assert to_yahoo_symbol("1306") == "1306.T"


def test_us_ticker_uppercased():
    assert to_yahoo_symbol("aapl") == "AAPL"
    assert to_yahoo_symbol("NVDA") == "NVDA"


def test_crypto_pair_passthrough():
    assert to_yahoo_symbol("btc-usd") == "BTC-USD"


def test_whitespace_trimmed():
    assert to_yahoo_symbol("  7011 ") == "7011.T"
