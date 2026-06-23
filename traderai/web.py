"""Web ダッシュボード。

標準ライブラリの HTTP サーバで、純資産の推移(ジャーナル)と資産配分
(ネットワース)を Chart.js(CDN)で可視化する。追加依存は不要。
`/` が HTML、`/data` が JSON を返す。
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .accounts import AccountBook
from .config import Config
from .journal import Journal


def dashboard_data(config: Config) -> dict:
    """ダッシュボード描画用のデータを組み立てる。"""
    book = AccountBook(config.accounts_path)
    journal = Journal(config.journal_path)
    trend = [
        {"date": s.timestamp[:10], "value": s.total_value} for s in journal.load()
    ]
    return {
        "total_value": round(book.total_value(), 0),
        "total_pl": round(book.total_pl(), 0),
        "allocation": book.allocation(),
        "by_account": {k: round(v, 0) for k, v in book.by_account().items()},
        "trend": trend,
        "currency": config.base_currency,
    }


_HTML = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<title>TraderAI ダッシュボード</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:system-ui,sans-serif;margin:24px;background:#f7f7f9;color:#222}
h1{font-size:20px} .cards{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}
.card{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.val{font-size:24px;font-weight:700} .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
canvas{background:#fff;border-radius:10px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.note{color:#888;font-size:12px;margin-top:24px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>📊 TraderAI ダッシュボード</h1>
<div class="cards">
  <div class="card"><div>純資産</div><div class="val" id="total">-</div></div>
  <div class="card"><div>評価損益</div><div class="val" id="pl">-</div></div>
</div>
<div class="grid">
  <canvas id="trend" height="180"></canvas>
  <canvas id="alloc" height="180"></canvas>
</div>
<div class="note">※ 推移は <code>traderai journal snapshot</code> の蓄積を表示。投資助言ではありません。</div>
<script>
fetch('/data').then(r=>r.json()).then(d=>{
  const cur=d.currency||'JPY';
  document.getElementById('total').textContent=Number(d.total_value).toLocaleString()+' '+cur;
  const pl=Number(d.total_pl);
  const plEl=document.getElementById('pl');
  plEl.textContent=(pl>=0?'+':'')+pl.toLocaleString()+' '+cur;
  plEl.style.color=pl>=0?'#c0392b':'#1e8449';
  new Chart(document.getElementById('trend'),{type:'line',
    data:{labels:d.trend.map(t=>t.date),datasets:[{label:'純資産推移',data:d.trend.map(t=>t.value),borderColor:'#2980b9',tension:.2,fill:false}]},
    options:{plugins:{title:{display:true,text:'純資産推移'}}}});
  const a=d.allocation||{};
  new Chart(document.getElementById('alloc'),{type:'doughnut',
    data:{labels:Object.keys(a),datasets:[{data:Object.values(a)}]},
    options:{plugins:{title:{display:true,text:'資産配分(%)'}}}});
});
</script></body></html>"""


def make_handler(config: Config):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path.startswith("/data"):
                body = json.dumps(dashboard_data(config), ensure_ascii=False).encode()
                self._send(body, "application/json; charset=utf-8")
            elif self.path in ("/", "/index.html"):
                self._send(_HTML.encode(), "text/html; charset=utf-8")
            else:
                self.send_error(404)

        def log_message(self, *args):  # サーバログを抑制
            pass

    return Handler


def serve(config: Config, host: str = "127.0.0.1", port: int = 8787) -> None:
    server = HTTPServer((host, port), make_handler(config))
    print(f"ダッシュボード: http://{host}:{port}  (Ctrl-C で停止)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
