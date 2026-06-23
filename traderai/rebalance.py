"""リバランス提案。

現在の資産配分と目標配分の乖離を計算し、目標に近づけるための
買い増し/売却の金額(売買候補)を提示する。実発注は行わない。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RebalanceAction:
    asset_class: str
    current_value: float
    current_pct: float
    target_pct: float
    target_value: float
    delta: float  # +なら買い増し / −なら売却
    action: str  # "買い増し" | "売却" | "維持"


def rebalance(
    current_values: dict[str, float],
    target_weights: dict[str, float],
    threshold_pct: float = 1.0,
) -> list[RebalanceAction]:
    """現在評価額(クラス別)と目標配分(%)から売買候補を返す。

    threshold_pct: 乖離がこの%未満なら「維持」とする。
    """
    total = sum(current_values.values())
    classes = set(current_values) | set(target_weights)
    actions: list[RebalanceAction] = []
    for cls in classes:
        cur = current_values.get(cls, 0.0)
        target_pct = target_weights.get(cls, 0.0)
        target_value = total * target_pct / 100
        delta = target_value - cur
        cur_pct = (cur / total * 100) if total else 0.0
        if abs(cur_pct - target_pct) < threshold_pct:
            action = "維持"
        elif delta > 0:
            action = "買い増し"
        else:
            action = "売却"
        actions.append(
            RebalanceAction(
                asset_class=cls,
                current_value=cur,
                current_pct=cur_pct,
                target_pct=target_pct,
                target_value=target_value,
                delta=delta,
                action=action,
            )
        )
    return sorted(actions, key=lambda a: abs(a.delta), reverse=True)


def parse_target(spec: str) -> dict[str, float]:
    """"外国株式=40,投資信託=25,..." 形式を辞書に変換する。"""
    result: dict[str, float] = {}
    for part in spec.split(","):
        if "=" not in part:
            continue
        key, _, val = part.partition("=")
        result[key.strip()] = float(val.strip())
    return result
