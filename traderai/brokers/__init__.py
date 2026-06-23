"""証券会社・取引所アダプタ層。

実際の口座と連携して残高取得・発注を行うための抽象インターフェースと、
具体的なアダプタ実装を置く。デフォルトの運用はペーパートレード(Portfolio)で
完結し、ここで定義する実発注アダプタは明示的に有効化したときのみ使用する。

現時点の実装状況:
- PaperBroker: 仮想売買(常に利用可能・既定)
- BitFlyerBroker: bitFlyer Lightning REST API のスケルトン(要 API キー設定)
- RakutenBroker: 楽天証券は公開 REST API が無いため CSV インポート方針のスタブ
"""

from .base import Broker, BrokerError, Order, Balance
from .paper import PaperBroker

__all__ = ["Broker", "BrokerError", "Order", "Balance", "PaperBroker"]
