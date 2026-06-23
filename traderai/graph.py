"""知識グラフ(軽量版)。

知識ループの記録(タグ付き)から、銘柄とタグの関係グラフを構築する。
外部のグラフDB(Neo4j 等)を必要とせず、標準ライブラリのみで「共通タグを
持つ関連銘柄」「タグ別クラスタ」を辿れるようにする。
"""

from __future__ import annotations

from collections import defaultdict

from .knowledge import Entry


def symbol_tags(entries: list[Entry]) -> dict[str, set[str]]:
    """銘柄 → 紐づくタグ集合(symbol を持つ記録のみ対象)。"""
    out: dict[str, set[str]] = defaultdict(set)
    for e in entries:
        if e.symbol and e.tags:
            out[e.symbol.upper()].update(t.strip() for t in e.tags if t.strip())
    return {k: v for k, v in out.items()}


def tag_clusters(entries: list[Entry]) -> dict[str, list[str]]:
    """タグ → そのタグを持つ銘柄一覧(クラスタ)。"""
    clusters: dict[str, set[str]] = defaultdict(set)
    for symbol, tags in symbol_tags(entries).items():
        for tag in tags:
            clusters[tag].add(symbol)
    return {tag: sorted(syms) for tag, syms in sorted(clusters.items())}


def related_symbols(entries: list[Entry], symbol: str) -> dict[str, list[str]]:
    """指定銘柄と共通タグを持つ他銘柄を、共通タグごとに返す。"""
    symbol = symbol.upper()
    st = symbol_tags(entries)
    own_tags = st.get(symbol, set())
    related: dict[str, list[str]] = {}
    for tag in sorted(own_tags):
        others = sorted(
            s for s, tags in st.items() if s != symbol and tag in tags
        )
        if others:
            related[tag] = others
    return related
