"""Web ダッシュボード。

標準ライブラリの HTTP サーバで、純資産の推移・資産配分・口座別評価額・
ストレステスト・リスク指標(集中度)・保有一覧を Chart.js(CDN)で可視化する。
追加依存は不要。`/` が HTML、`/data` が JSON を返す。
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from .accounts import AccountBook
from .analysis import rsi as compute_rsi
from .config import Config
from .journal import Journal
from .market import MarketDataError, get_history
from .portfolio import Portfolio
from .simulation import future_value
from .stress import run_all as stress_run_all
from .watchlist import Watchlist


def dashboard_data(config: Config) -> dict:
    """ダッシュボード描画用のデータを組み立てる。"""
    book = AccountBook(config.accounts_path)
    journal = Journal(config.journal_path)

    trend = [
        {"date": s.timestamp[:10], "value": s.total_value} for s in journal.load()
    ]

    holdings = sorted(
        (
            {
                "name": h.name,
                "account": h.account,
                "asset_class": h.asset_class,
                "value": round(h.value, 0),
                "pl": round(h.pl, 0),
                "pl_pct": round(h.pl_pct, 1) if h.pl_pct is not None else None,
            }
            for h in book.holdings
        ),
        key=lambda x: x["value"],
        reverse=True,
    )

    # ストレステスト(資産クラス別の想定下落)
    stress = [
        {"scenario": r.scenario, "loss": round(r.loss, 0), "loss_pct": round(r.loss_pct, 1)}
        for r in (stress_run_all(book.by_asset_class()) if book.holdings else [])
    ]

    # 集中度(保有単位の HHI / 実効銘柄数 / 最大構成比)
    by_holding = {h.name: h.value for h in book.holdings}
    total = sum(by_holding.values())
    hhi = sum((v / total) ** 2 for v in by_holding.values()) if total else 0.0
    top_name, top_val = (
        max(by_holding.items(), key=lambda kv: kv[1]) if by_holding else (None, 0.0)
    )
    risk = {
        "hhi": round(hhi, 3),
        "effective_n": round(1 / hhi, 1) if hhi else 0,
        "top_name": top_name,
        "top_pct": round(top_val / total * 100, 1) if total else 0,
    }

    # 未来:現在の純資産を元本に、毎月積立を続けた場合の予測。
    # 積立額は 環境変数 > 設定ファイル(settings.json) > 既定 の順で解決。
    settings = config.load_settings()
    total = book.total_value()
    monthly = float(
        os.environ.get("TRADERAI_MONTHLY") or settings.get("monthly_contribution") or 0
    )
    years = int(
        os.environ.get("TRADERAI_FORECAST_YEARS") or settings.get("forecast_years") or 20
    )
    forecast = {
        "monthly": monthly,
        "years": years,
        "labels": [f"+{y}年" for y in range(years + 1)],
        "rates": {
            str(int(r * 100)): [round(future_value(total, monthly, r, y), 0) for y in range(years + 1)]
            for r in (0.03, 0.05, 0.07)
        },
    }

    return {
        "total_value": round(total, 0),
        "total_cost": round(book.total_cost(), 0),
        "total_pl": round(book.total_pl(), 0),
        "allocation": book.allocation(),
        "by_account": {k: round(v, 0) for k, v in book.by_account().items()},
        "trend": trend,
        "holdings": holdings,
        "stress": stress,
        "risk": risk,
        "forecast": forecast,
        "currency": config.base_currency,
    }


def symbols_data(config: Config) -> dict:
    """保有銘柄(個別株)とウォッチリストの現在値・前日比・RSI・直近値動きを返す。

    1 銘柄につき yfinance のヒストリカル取得 1 回(period=3mo)。取得失敗は
    error フィールドに格納してスキップしない。
    """
    held = {p.symbol for p in Portfolio(config.portfolio_path).positions()}
    watch = set(Watchlist(config.watchlist_path).symbols())
    out: list[dict] = []
    for sym in sorted(held | watch):
        sources = []
        if sym in held:
            sources.append("保有")
        if sym in watch:
            sources.append("ウォッチ")
        row: dict = {"symbol": sym, "sources": sources}
        try:
            hist = get_history(sym, period="3mo")
            close = hist["Close"].dropna()
            price = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else None
            row["price"] = round(price, 2)
            row["change_pct"] = round((price - prev) / prev * 100, 2) if prev else None
            r = compute_rsi(close)
            row["rsi"] = round(r, 1) if r is not None else None
            row["history"] = [round(float(x), 2) for x in close.tolist()][-60:]
            row["error"] = None
        except MarketDataError as exc:
            row["error"] = str(exc)
        out.append(row)
    return {"symbols": out}


_HTML = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<title>TraderAI ダッシュボード</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:system-ui,-apple-system,sans-serif;margin:24px;background:#f5f6f8;color:#222}
h1{font-size:20px;margin:0 0 16px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
.card{background:#fff;border-radius:10px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:150px}
.card .lbl{color:#888;font-size:12px} .card .val{font-size:22px;font-weight:700;margin-top:2px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
canvas{background:#fff;border-radius:10px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}
th,td{padding:8px 12px;text-align:right;font-size:13px;border-bottom:1px solid #eee}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
thead th{background:#fafafa;color:#555}
.pos{color:#c0392b}.neg{color:#1e8449}
.note{color:#999;font-size:12px;margin-top:20px}
h2{font-size:15px;margin:24px 0 10px;border-left:4px solid #2980b9;padding-left:8px}
.syms{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.sym{background:#fff;border-radius:10px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.sym .top{display:flex;justify-content:space-between;align-items:baseline}
.sym .nm{font-weight:700} .sym .px{font-size:18px;font-weight:700}
.badge{font-size:11px;color:#fff;background:#888;border-radius:4px;padding:1px 6px;margin-left:6px}
.badge.h{background:#2980b9}.badge.w{background:#e67e22}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>📊 TraderAI ダッシュボード</h1>
<div class="cards" id="cards"></div>

<h2>現在 — 資産の内訳とリスク</h2>
<div class="grid">
  <canvas id="alloc" height="200"></canvas>
  <canvas id="acct" height="200"></canvas>
  <canvas id="stress" height="200"></canvas>
  <canvas id="trend" height="200"></canvas>
</div>
<table id="holdings"><thead><tr>
  <th>銘柄</th><th>口座</th><th>資産クラス</th><th>評価額</th><th>損益</th><th>損益率</th>
</tr></thead><tbody></tbody></table>

<h2>未来 — 積立を続けた場合の資産予測</h2>
<canvas id="forecast" height="120"></canvas>
<div class="note" id="fcnote"></div>

<h2>過去・現在 — 保有/ウォッチ銘柄の値動き(直近3ヶ月)</h2>
<div class="syms" id="syms">読み込み中…(ライブ価格を取得しています)</div>

<div class="note">※ 推移は起動のたびに記録。ストレス/予測は想定シナリオで将来を保証しません。投資助言ではありません。</div>
<script>
const yen = n => Number(n).toLocaleString();
const spark = (ctx, data, color) => new Chart(ctx,{type:'line',
  data:{labels:data.map((_,i)=>i),datasets:[{data,borderColor:color,borderWidth:1.5,pointRadius:0,tension:.2,fill:false}]},
  options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{display:false}},elements:{line:{borderJoinStyle:'round'}}}});

fetch('/data').then(r=>r.json()).then(d=>{
  const cur=d.currency||'JPY', pl=Number(d.total_pl), r=d.risk||{};
  const cards=[
    ['純資産', yen(d.total_value)+' '+cur],
    ['評価損益', (pl>=0?'+':'')+yen(pl)+' '+cur],
    ['集中度(HHI)', (r.hhi??'-')+' / 実効'+(r.effective_n??'-')+'銘柄'],
    ['最大保有', (r.top_name||'-')+' '+(r.top_pct??0)+'%'],
  ];
  document.getElementById('cards').innerHTML = cards.map((c,i)=>
    `<div class="card"><div class="lbl">${c[0]}</div><div class="val" ${i===1?`style="color:${pl>=0?'#c0392b':'#1e8449'}"`:''}>${c[1]}</div></div>`
  ).join('');

  new Chart(trend,{type:'line',data:{labels:d.trend.map(t=>t.date),
    datasets:[{label:'純資産推移',data:d.trend.map(t=>t.value),borderColor:'#2980b9',tension:.2,fill:false}]},
    options:{plugins:{title:{display:true,text:'純資産推移(記録)'}}}});

  const a=d.allocation||{};
  new Chart(alloc,{type:'doughnut',data:{labels:Object.keys(a),datasets:[{data:Object.values(a)}]},
    options:{plugins:{title:{display:true,text:'資産配分(%)'}}}});

  const ac=d.by_account||{};
  new Chart(acct,{type:'bar',data:{labels:Object.keys(ac),datasets:[{label:'評価額',data:Object.values(ac),backgroundColor:'#16a085'}]},
    options:{indexAxis:'y',plugins:{legend:{display:false},title:{display:true,text:'口座別 評価額'}}}});

  const s=d.stress||[];
  new Chart(stress,{type:'bar',data:{labels:s.map(x=>x.scenario),datasets:[{label:'下落率%',data:s.map(x=>x.loss_pct),backgroundColor:'#c0392b'}]},
    options:{indexAxis:'y',plugins:{legend:{display:false},title:{display:true,text:'ストレステスト(下落率%)'}}}});

  const tb=document.querySelector('#holdings tbody');
  tb.innerHTML=(d.holdings||[]).map(h=>{
    const cls=h.pl>=0?'pos':'neg', sign=h.pl>=0?'+':'';
    const pct=h.pl_pct==null?'-':(sign+h.pl_pct+'%');
    return `<tr><td>${h.name}</td><td>${h.account}</td><td>${h.asset_class}</td>
      <td>${yen(h.value)}</td><td class="${cls}">${sign}${yen(h.pl)}</td><td class="${cls}">${pct}</td></tr>`;
  }).join('');

  // 未来:予測
  const f=d.forecast||{rates:{}}; const colors={'3':'#95a5a6','5':'#2980b9','7':'#27ae60'};
  new Chart(forecast,{type:'line',data:{labels:f.labels||[],
    datasets:Object.keys(f.rates||{}).map(k=>({label:'年利'+k+'%',data:f.rates[k],borderColor:colors[k]||'#888',borderDash:k==='5'?[]:[5,4],tension:.2,pointRadius:0,fill:false}))},
    options:{plugins:{title:{display:true,text:'将来資産予測(現在の純資産＋毎月積立)'}}}});
  document.getElementById('fcnote').textContent =
    `前提: 毎月積立 ${yen(f.monthly||0)} ${cur} / ${f.years||0}年(積立額は環境変数 TRADERAI_MONTHLY で変更可)`;
});

// 過去・現在:保有/ウォッチ銘柄(ライブ取得は後追い)
fetch('/symbols').then(r=>r.json()).then(d=>{
  const el=document.getElementById('syms');
  const rows=d.symbols||[];
  if(!rows.length){el.textContent='保有・ウォッチ銘柄がありません(portfolio.json / watchlist.json に登録)。';return;}
  el.innerHTML='';
  rows.forEach(s=>{
    const div=document.createElement('div'); div.className='sym';
    const badges=(s.sources||[]).map(x=>`<span class="badge ${x==='保有'?'h':'w'}">${x}</span>`).join('');
    if(s.error){div.innerHTML=`<div class="top"><span class="nm">${s.symbol}${badges}</span></div><div class="note">取得失敗</div>`;el.appendChild(div);return;}
    const chg=s.change_pct, cls=chg>=0?'pos':'neg', sign=chg>=0?'+':'';
    div.innerHTML=`<div class="top"><span class="nm">${s.symbol}${badges}</span><span class="px">${yen(s.price)}</span></div>
      <div class="${cls}">${sign}${chg==null?'-':chg}%　RSI ${s.rsi??'-'}</div>
      <canvas height="50"></canvas>`;
    el.appendChild(div);
    spark(div.querySelector('canvas'), s.history||[], chg>=0?'#c0392b':'#1e8449');
  });
}).catch(()=>{document.getElementById('syms').textContent='価格取得に失敗しました(ネットワークをご確認ください)。';});
</script></body></html>"""


def make_handler(config: Config):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            # ブラウザが古い画面/データをキャッシュしないようにする
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path.startswith("/data"):
                body = json.dumps(dashboard_data(config), ensure_ascii=False).encode()
                self._send(body, "application/json; charset=utf-8")
            elif self.path.startswith("/symbols"):
                body = json.dumps(symbols_data(config), ensure_ascii=False).encode()
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
