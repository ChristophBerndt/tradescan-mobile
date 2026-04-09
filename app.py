"""
TradeScan Mobile - Christoph Range-Reversion Strategie
"""

import datetime, time, os
import pandas as pd

try:
    import yfinance as yf
    import ta
except ImportError:
    raise SystemExit("pip install yfinance ta pandas flask gunicorn")

from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

TICKERS = [
    ("SAP.DE",   "SAP SE",            "DAX"),
    ("ALV.DE",   "Allianz",           "DAX"),
    ("DTE.DE",   "Dt. Telekom",       "DAX"),
    ("BAYN.DE",  "Bayer AG",          "DAX"),
    ("VNA.DE",   "Vonovia",           "DAX"),
    ("DBK.DE",   "Deutsche Bank",     "DAX"),
    ("EOAN.DE",  "E.ON",              "DAX"),
    ("RWE.DE",   "RWE AG",            "DAX"),
    ("CON.DE",   "Continental",       "DAX"),
    ("MBG.DE",   "Mercedes-Benz",     "DAX"),
    ("BMW.DE",   "BMW AG",            "DAX"),
    ("BAS.DE",   "BASF SE",           "DAX"),
    ("SIE.DE",   "Siemens AG",        "DAX"),
    ("IFX.DE",   "Infineon",          "DAX"),
    ("MUV2.DE",  "Munich Re",         "DAX"),
    ("ADS.DE",   "Adidas",            "DAX"),
    ("HEN3.DE",  "Henkel",            "DAX"),
    ("ZAL.DE",   "Zalando",           "DAX"),
    ("PUM.DE",   "Puma SE",           "DAX"),
    ("LHA.DE",   "Lufthansa",         "DAX"),
    ("CBK.DE",   "Commerzbank",       "DAX"),
    ("KO",       "Coca-Cola",         "US"),
    ("PEP",      "PepsiCo",           "US"),
    ("PG",       "Procter & Gamble",  "US"),
    ("JNJ",      "Johnson & Johnson", "US"),
    ("MCD",      "McDonald's",        "US"),
    ("T",        "AT&T",              "US"),
    ("VZ",       "Verizon",           "US"),
    ("PFE",      "Pfizer",            "US"),
    ("INTC",     "Intel",             "US"),
    ("IBM",      "IBM",               "US"),
    ("CVX",      "Chevron",           "US"),
    ("XOM",      "ExxonMobil",        "US"),
    ("MO",       "Altria Group",      "US"),
    ("AAL",      "American Airlines", "US"),
    ("DAL",      "Delta Air Lines",   "US"),
    ("UAL",      "United Airlines",   "US"),
    ("LUV",      "Southwest",         "US"),
    ("JBLU",     "JetBlue",           "US"),
    ("RYAAY",    "Ryanair",           "US"),
    ("SNAP",     "Snap Inc",          "US"),
    ("PLTR",     "Palantir",          "US"),
    ("SOFI",     "SoFi",              "US"),
    ("SAN.PA",   "Sanofi",            "EU"),
    ("TTE.PA",   "TotalEnergies",     "EU"),
    ("BNP.PA",   "BNP Paribas",       "EU"),
    ("AF.PA",    "Air France-KLM",    "EU"),
]

WATCHLIST = [
    ("AAL",     "American Airlines", "US"),
    ("DAL",     "Delta Air Lines",   "US"),
    ("BAYN.DE", "Bayer AG",          "DAX"),
    ("VNA.DE",  "Vonovia",           "DAX"),
    ("KO",      "Coca-Cola",         "US"),
    ("PFE",     "Pfizer",            "US"),
    ("INTC",    "Intel",             "US"),
    ("T",       "AT&T",              "US"),
    ("LHA.DE",  "Lufthansa",         "DAX"),
    ("DBK.DE",  "Deutsche Bank",     "DAX"),
]

def analyze(ticker, name, market):
    try:
        time.sleep(1.2)
        df = yf.download(ticker, period="300d", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 60:
            return None

        close = df["Close"].squeeze()
        bb    = ta.volatility.BollingerBands(close=close, window=20, window_dev=2.0)
        bb_lo = bb.bollinger_lband()
        bb_hi = bb.bollinger_hband()
        bb_mi = bb.bollinger_mavg()
        bb_pct= bb.bollinger_pband()
        rsi   = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        ma200 = close.rolling(200).mean()

        price     = float(close.iloc[-1])
        prev      = float(close.iloc[-2])
        chg       = round((price - prev) / prev * 100, 2)
        rsi_now   = round(float(rsi.iloc[-1]), 1)
        bb_lo_now = float(bb_lo.iloc[-1])
        bb_hi_now = float(bb_hi.iloc[-1])
        bb_mi_now = float(bb_mi.iloc[-1])
        bb_p_now  = round(float(bb_pct.iloc[-1]) * 100, 1)
        ma200_now = float(ma200.iloc[-1])

        # Kern-Signal: gestern unter BB, heute wieder drüber
        prev_below = float(close.iloc[-2]) < float(bb_lo.iloc[-2])
        now_above  = price > bb_lo_now

        cond_bb    = prev_below and now_above
        cond_rsi   = rsi_now < 35
        cond_trend = price > ma200_now
        score      = sum([cond_bb, cond_rsi, cond_trend])

        sell_signal = rsi_now > 65 and bb_p_now > 85

        # Wann wäre Einstieg möglich? (für "noch nicht"-Karten)
        entry_when = []
        if not cond_bb:
            entry_when.append(f"Preis fällt unter {round(bb_lo_now,2)} und erholt sich")
        if not cond_rsi:
            entry_when.append(f"RSI fällt unter 35 (aktuell: {rsi_now})")
        if not cond_trend:
            entry_when.append(f"Preis steigt über MA200 ({round(ma200_now,2)})")

        # Signal
        if score == 3:
            signal = "KAUFEN"
            color  = "#00d4aa"
            label  = "Jetzt kaufen"
        elif score == 2:
            signal = "FAST"
            color  = "#f7b731"
            label  = "Morgen prüfen"
        elif score == 1 and cond_bb:
            signal = "BEOBACHTEN"
            color  = "#4a9eff"
            label  = "Beobachten"
        elif sell_signal:
            signal = "VERKAUFEN"
            color  = "#ff4757"
            label  = "Jetzt verkaufen"
        else:
            signal = "NEUTRAL"
            color  = "#5a6478"
            label  = "Abwarten"

        # Ziele (immer berechnen, auch für noch-nicht-Signale)
        stop_loss  = round(price * 0.92, 2)
        target1    = round(bb_mi_now, 2)
        target2    = round(bb_hi_now, 2)
        potential1 = round((target1 - price) / price * 100, 1)
        potential2 = round((target2 - price) / price * 100, 1)

        # Wann würde Einstiegspreis ungefähr sein?
        future_entry = round(bb_lo_now * 0.99, 2)  # ca. an unterer BB

        high52 = float(close.rolling(min(252,len(close))).max().iloc[-1])
        low52  = float(close.rolling(min(252,len(close))).min().iloc[-1])
        pos52  = round((price - low52) / (high52 - low52) * 100, 1) if high52 != low52 else 50

        conditions = [
            ("BB-Umkehr (unter BB → wieder drüber)", cond_bb),
            (f"RSI {rsi_now} unter 35", cond_rsi),
            (f"Aufwärtstrend (über MA200)", cond_trend),
        ]

        return {
            "ticker":       ticker,
            "name":         name,
            "market":       market,
            "price":        round(price, 2),
            "change":       chg,
            "rsi":          rsi_now,
            "bb_pct":       bb_p_now,
            "bb_lower":     round(bb_lo_now, 2),
            "bb_upper":     round(bb_hi_now, 2),
            "bb_mid":       round(bb_mi_now, 2),
            "ma200":        round(ma200_now, 2),
            "pos52":        pos52,
            "signal":       signal,
            "color":        color,
            "label":        label,
            "score":        score,
            "conditions":   conditions,
            "stop_loss":    stop_loss,
            "target1":      target1,
            "target2":      target2,
            "potential1":   potential1,
            "potential2":   potential2,
            "future_entry": future_entry,
            "entry_when":   entry_when,
            "cond_bb":      cond_bb,
            "cond_rsi":     cond_rsi,
            "cond_trend":   cond_trend,
        }
    except Exception as e:
        print(f"  Fehler {ticker}: {e}")
        return None

CACHE = {"data": [], "time": None}
ORDER = {"KAUFEN":0,"FAST":1,"BEOBACHTEN":2,"VERKAUFEN":3,"NEUTRAL":4}

def do_scan(pairs):
    results = []
    for ticker, name, market in pairs:
        print(f"  {ticker}...", flush=True)
        r = analyze(ticker, name, market)
        if r: results.append(r)
    results.sort(key=lambda x: (ORDER.get(x["signal"],9), -x["score"]))
    CACHE["data"] = results
    CACHE["time"] = datetime.datetime.now()
    return results

TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>TradeScan</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{background:#0a0c0f;color:#e8eaf0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;max-width:500px;margin:0 auto;padding-bottom:60px}
.header{background:#111318;border-bottom:1px solid #1e2530;padding:12px 16px;position:sticky;top:0;z-index:100}
.logo{font-size:20px;font-weight:900;letter-spacing:-0.5px;margin-bottom:4px}
.logo span{color:#00d4aa}
.scan-time{font-size:10px;color:#5a6478;margin-bottom:8px}
.btn-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.btn{border:none;border-radius:8px;padding:9px;font-size:12px;font-weight:700;cursor:pointer;width:100%}
.btn-primary{background:#00d4aa;color:#000}
.btn-secondary{background:#1e2530;color:#e8eaf0}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid #1e2530}
.stat{background:#111318;padding:9px 4px;text-align:center;border-right:1px solid #1e2530}
.stat:last-child{border-right:none}
.stat-val{font-size:20px;font-weight:700}
.stat-label{font-size:9px;color:#5a6478;text-transform:uppercase;margin-top:1px}
.filter-row{display:flex;gap:6px;padding:8px 12px;background:#111318;border-bottom:1px solid #1e2530;overflow-x:auto;-webkit-overflow-scrolling:touch}
.fb{border:1px solid #1e2530;border-radius:16px;padding:4px 12px;font-size:11px;font-weight:600;cursor:pointer;white-space:nowrap;background:transparent;color:#5a6478}
.fb.active{background:#00d4aa;color:#000;border-color:#00d4aa}
.sec{font-size:10px;color:#5a6478;text-transform:uppercase;letter-spacing:1px;padding:10px 14px 4px;font-weight:700}
.card{background:#111318;border-bottom:1px solid #1e2530;padding:14px}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}
.ticker{font-size:16px;font-weight:700}
.tsub{font-size:11px;color:#5a6478;margin-top:1px}
.badge{padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
.pr-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.price{font-size:20px;font-weight:700}
.up{color:#00d4aa}.dn{color:#ff4757}.am{color:#f7b731}
.checks{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-bottom:10px}
.ck{border-radius:7px;padding:7px 4px;text-align:center}
.ck-icon{font-size:15px;margin-bottom:2px}
.ck-label{font-size:9px;line-height:1.2}
.box{border-radius:8px;padding:10px;margin-bottom:8px}
.row{display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.05)}
.row:last-child{border-bottom:none}
.rl{color:#5a6478}
.hint{font-size:11px;border-radius:7px;padding:8px 10px;margin-bottom:8px;line-height:1.5}
.future-box{background:#111318;border:1px solid #1e2530;border-radius:8px;padding:10px;margin-bottom:8px}
.future-title{font-size:10px;color:#5a6478;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.future-row{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.04)}
.future-row:last-child{border-bottom:none}
.when-item{font-size:11px;color:#5a6478;padding:3px 0;display:flex;gap:6px}
.empty{text-align:center;padding:60px 20px;color:#5a6478}
.footer{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:500px;background:#111318;border-top:1px solid #1e2530;padding:8px 16px;font-size:10px;color:#5a6478;text-align:center}
</style>
</head>
<body>
<div class="header">
  <div class="logo">TRADE<span>SCAN</span></div>
  <div class="scan-time">{{ scan_time }}</div>
  <div class="btn-row">
    <form method="post" action="/scan" style="margin:0">
      <button class="btn btn-primary" type="submit">▶ Vollscan ({{ total_tickers }})</button>
    </form>
    <form method="post" action="/scan-wl" style="margin:0">
      <button class="btn btn-secondary" type="submit">◎ Watchlist (10)</button>
    </form>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="stat-val up">{{ kaufen }}</div><div class="stat-label">Kaufen</div></div>
  <div class="stat"><div class="stat-val am">{{ fast }}</div><div class="stat-label">Fast</div></div>
  <div class="stat"><div class="stat-val dn">{{ verkaufen }}</div><div class="stat-label">Verkauf</div></div>
  <div class="stat"><div class="stat-val">{{ total }}</div><div class="stat-label">Gesamt</div></div>
</div>

<div class="filter-row">
  <button class="fb {% if f=='all' %}active{% endif %}" onclick="location.href='/?f=all'">Alle</button>
  <button class="fb {% if f=='kaufen' %}active{% endif %}" onclick="location.href='/?f=kaufen'">Kaufen</button>
  <button class="fb {% if f=='fast' %}active{% endif %}" onclick="location.href='/?f=fast'">Fast</button>
  <button class="fb {% if f=='beobachten' %}active{% endif %}" onclick="location.href='/?f=beobachten'">Watch</button>
  <button class="fb {% if f=='dax' %}active{% endif %}" onclick="location.href='/?f=dax'">DAX</button>
  <button class="fb {% if f=='us' %}active{% endif %}" onclick="location.href='/?f=us'">US</button>
</div>

{% if not data %}
<div class="empty">
  <div style="font-size:40px;margin-bottom:12px">📊</div>
  <div style="font-size:15px;margin-bottom:6px">Noch keine Daten</div>
  <div style="font-size:12px">Tippe auf Vollscan oder Watchlist</div>
</div>
{% else %}

{% for sec_name, sec_list in groups %}
{% if sec_list %}
<div class="sec">{{ sec_name }}</div>
{% for r in sec_list %}
<div class="card">

  <div class="card-top">
    <div>
      <div class="ticker">{{ r.ticker.replace('.DE','').replace('.PA','').replace('.AS','') }}</div>
      <div class="tsub">{{ r.name }} · {{ r.market }}</div>
    </div>
    <span class="badge" style="background:{{ r.color }}22;color:{{ r.color }};border:1px solid {{ r.color }}44">
      {{ r.label }}
    </span>
  </div>

  <div class="pr-row">
    <span class="price">{{ "%.2f"|format(r.price) }}</span>
    <span class="{{ 'up' if r.change >= 0 else 'dn' }}">{{ "%+.2f"|format(r.change) }}%</span>
  </div>

  <div class="checks">
    <div class="ck" style="background:{{ '#00d4aa22' if r.cond_bb else '#1e2530' }}">
      <div class="ck-icon" style="color:{{ '#00d4aa' if r.cond_bb else '#5a6478' }}">{{ '✓' if r.cond_bb else '✗' }}</div>
      <div class="ck-label" style="color:{{ '#00d4aa' if r.cond_bb else '#5a6478' }}">BB-Umkehr</div>
    </div>
    <div class="ck" style="background:{{ '#00d4aa22' if r.cond_rsi else '#1e2530' }}">
      <div class="ck-icon" style="color:{{ '#00d4aa' if r.cond_rsi else '#5a6478' }}">{{ '✓' if r.cond_rsi else '✗' }}</div>
      <div class="ck-label" style="color:{{ '#00d4aa' if r.cond_rsi else '#5a6478' }}">RSI {{ r.rsi }}</div>
    </div>
    <div class="ck" style="background:{{ '#00d4aa22' if r.cond_trend else '#1e2530' }}">
      <div class="ck-icon" style="color:{{ '#00d4aa' if r.cond_trend else '#5a6478' }}">{{ '✓' if r.cond_trend else '✗' }}</div>
      <div class="ck-label" style="color:{{ '#00d4aa' if r.cond_trend else '#5a6478' }}">Trend {{ '↑' if r.cond_trend else '↓' }}</div>
    </div>
  </div>

  {% if r.signal == 'KAUFEN' %}
  <div class="hint" style="background:#00d4aa11;border:1px solid #00d4aa33;color:#00d4aa">
    Alle 3 Bedingungen erfüllt — heute kaufen!
  </div>
  <div class="box" style="background:#00d4aa0a;border:1px solid #00d4aa22">
    <div class="row"><span class="rl">Kaufen bei</span><span style="font-weight:700">{{ "%.2f"|format(r.price) }}</span></div>
    <div class="row"><span class="rl">Stop-Loss (−8%)</span><span class="dn">{{ "%.2f"|format(r.stop_loss) }}</span></div>
    <div class="row"><span class="rl">Ziel 1 — MA20</span><span class="up">{{ "%.2f"|format(r.target1) }} ({{ "%+.1f"|format(r.potential1) }}%)</span></div>
    <div class="row"><span class="rl">Ziel 2 — ob. BB</span><span class="up">{{ "%.2f"|format(r.target2) }} ({{ "%+.1f"|format(r.potential2) }}%)</span></div>
    <div class="row"><span class="rl">Haltedauer</span><span>2–6 Wochen</span></div>
    <div class="row"><span class="rl">Trend (MA200)</span><span class="{{ 'up' if r.price > r.ma200 else 'dn' }}">{{ '↑ Aufwärts' if r.price > r.ma200 else '↓ Abwärts' }}</span></div>
  </div>

  {% elif r.signal == 'VERKAUFEN' %}
  <div class="hint" style="background:#ff475711;border:1px solid #ff475733;color:#ff4757">
    RSI überkauft + obere BB erreicht — Position jetzt schliessen und Gewinn sichern!
  </div>

  {% else %}
  {% if r.entry_when %}
  <div class="hint" style="background:#f7b73111;border:1px solid #f7b73133;color:#f7b731">
    {{ r.score }}/3 Bedingungen erfüllt — noch nicht kaufen.
  </div>
  {% endif %}

  <div class="future-box">
    <div class="future-title">Wo wäre der Einstieg wenn Signal kommt?</div>
    <div class="future-row"><span class="rl">Möglicher Einstieg</span><span style="color:#4a9eff">ca. {{ "%.2f"|format(r.future_entry) }}</span></div>
    <div class="future-row"><span class="rl">Stop-Loss dann (−8%)</span><span class="dn">ca. {{ "%.2f"|format(r.future_entry * 0.92) | round(2) }}</span></div>
    <div class="future-row"><span class="rl">Ziel 1 — MA20</span><span class="up">{{ "%.2f"|format(r.target1) }} ({{ "%+.1f"|format((r.target1 - r.future_entry) / r.future_entry * 100) }}%)</span></div>
    <div class="future-row"><span class="rl">Ziel 2 — ob. BB</span><span class="up">{{ "%.2f"|format(r.target2) }} ({{ "%+.1f"|format((r.target2 - r.future_entry) / r.future_entry * 100) }}%)</span></div>
    <div style="margin-top:8px;border-top:1px solid #1e2530;padding-top:8px">
      <div class="future-title" style="margin-bottom:4px">Was muss noch passieren?</div>
      {% for w in r.entry_when %}
      <div class="when-item"><span style="color:#4a9eff">→</span><span>{{ w }}</span></div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

</div>
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

<div class="footer">TradeScan · Range-Reversion · 2–6 Wochen · Kein Anlageberatung</div>
</body>
</html>"""

@app.route("/")
def index():
    data = CACHE["data"]
    f    = request.args.get("f", "all")
    now  = CACHE["time"]

    if f == "kaufen":    show = [r for r in data if r["signal"] == "KAUFEN"]
    elif f == "fast":    show = [r for r in data if r["signal"] == "FAST"]
    elif f == "beobachten": show = [r for r in data if r["signal"] == "BEOBACHTEN"]
    elif f == "dax":     show = [r for r in data if r["market"] == "DAX"]
    elif f == "us":      show = [r for r in data if r["market"] == "US"]
    else:                show = data

    groups = [
        ("Jetzt kaufen — alle 3 Bedingungen erfüllt", [r for r in show if r["signal"]=="KAUFEN"]),
        ("Morgen prüfen — 2/3 Bedingungen erfüllt",   [r for r in show if r["signal"]=="FAST"]),
        ("Beobachten — Signal baut sich auf",          [r for r in show if r["signal"]=="BEOBACHTEN"]),
        ("Jetzt verkaufen — Position schliessen",      [r for r in show if r["signal"]=="VERKAUFEN"]),
        ("Abwarten — noch kein Signal",                [r for r in show if r["signal"]=="NEUTRAL"]),
    ]

    return render_template_string(TEMPLATE,
        data=show, groups=groups,
        kaufen=len([r for r in data if r["signal"]=="KAUFEN"]),
        fast=len([r for r in data if r["signal"]=="FAST"]),
        verkaufen=len([r for r in data if r["signal"]=="VERKAUFEN"]),
        total=len(data),
        total_tickers=len(TICKERS),
        scan_time=now.strftime("Stand: %d.%m.%Y %H:%M Uhr") if now else "Noch kein Scan",
        f=f,
    )

@app.route("/scan", methods=["POST"])
def scan_all():
    import threading
    threading.Thread(target=do_scan, args=(TICKERS,), daemon=True).start()
    time.sleep(2)
    return redirect("/")

@app.route("/scan-wl", methods=["POST"])
def scan_wl():
    do_scan(WATCHLIST)
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  TradeScan startet auf http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
