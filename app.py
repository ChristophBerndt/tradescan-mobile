"""
TradeScan Mobile - Christoph Range-Reversion Strategie
Neues Design: ING DiBa inspiriert, 110 globale Aktien
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

# ── 110 GLOBALE AKTIEN ─────────────────────────────────────────────────────
TICKERS = [
    # 🇩🇪 DAX (20)
    ("BAYN.DE",  "Bayer AG",           "DAX"),
    ("VNA.DE",   "Vonovia",            "DAX"),
    ("DTE.DE",   "Dt. Telekom",        "DAX"),
    ("EOAN.DE",  "E.ON SE",            "DAX"),
    ("RWE.DE",   "RWE AG",             "DAX"),
    ("HEN3.DE",  "Henkel",             "DAX"),
    ("MUV2.DE",  "Munich Re",          "DAX"),
    ("ALV.DE",   "Allianz SE",         "DAX"),
    ("DBK.DE",   "Deutsche Bank",      "DAX"),
    ("CBK.DE",   "Commerzbank",        "DAX"),
    ("BAS.DE",   "BASF SE",            "DAX"),
    ("BMW.DE",   "BMW AG",             "DAX"),
    ("MBG.DE",   "Mercedes-Benz",      "DAX"),
    ("LHA.DE",   "Lufthansa",          "DAX"),
    ("SIE.DE",   "Siemens AG",         "DAX"),
    ("ADS.DE",   "Adidas",             "DAX"),
    ("SHL.DE",   "Siemens Health.",    "DAX"),
    ("DHER.DE",  "Delivery Hero",      "DAX"),
    ("ZAL.DE",   "Zalando",            "DAX"),
    ("CON.DE",   "Covestro",           "DAX"),
    # 🇬🇧 UK FTSE (14)
    ("SHEL",     "Shell plc",          "UK"),
    ("BP",       "BP plc",             "UK"),
    ("GSK",      "GSK plc",            "UK"),
    ("AZN",      "AstraZeneca",        "UK"),
    ("UL",       "Unilever",           "UK"),
    ("HSBC",     "HSBC Holdings",      "UK"),
    ("LYG",      "Lloyds Banking",     "UK"),
    ("BCS",      "Barclays",           "UK"),
    ("VOD",      "Vodafone",           "UK"),
    ("BT",       "BT Group",           "UK"),
    ("DEO",      "Diageo",             "UK"),
    ("BTI",      "Brit. Am. Tobacco",  "UK"),
    ("RBGLY",    "Reckitt",            "UK"),
    ("IMBBY",    "Imperial Brands",    "UK"),
    # 🇪🇺 Europa (16)
    ("SAN.PA",   "Sanofi",             "EU"),
    ("TEF",      "Telefónica",         "EU"),
    ("IBE.MC",   "Iberdrola",          "EU"),
    ("ENEL.MI",  "Enel SpA",           "EU"),
    ("ENI",      "ENI SpA",            "EU"),
    ("UNCFF",    "UniCredit",          "EU"),
    ("BNPQF",    "BNP Paribas",        "EU"),
    ("TTE",      "TotalEnergies",      "EU"),
    ("BUD",      "AB InBev",           "EU"),
    ("PHG",      "Philips",            "EU"),
    ("AFLYY",    "Air France-KLM",     "EU"),
    ("ICAGY",    "IAG (BA+Iberia)",    "EU"),
    ("LRLCY",    "L'Oreal",            "EU"),
    ("SCGLY",    "Societe Generale",   "EU"),
    ("REPYY",    "Repsol",             "EU"),
    ("NVO",      "Novo Nordisk",       "EU"),
    # 🇺🇸 USA S&P 500 (30)
    ("KO",       "Coca-Cola",          "US"),
    ("PEP",      "PepsiCo",            "US"),
    ("PG",       "Procter & Gamble",   "US"),
    ("KHC",      "Kraft Heinz",        "US"),
    ("MDLZ",     "Mondelez",           "US"),
    ("KDP",      "Keurig Dr Pepper",   "US"),
    ("GIS",      "General Mills",      "US"),
    ("CPB",      "Campbell Soup",      "US"),
    ("CL",       "Colgate-Palmolive",  "US"),
    ("JNJ",      "Johnson & Johnson",  "US"),
    ("PFE",      "Pfizer",             "US"),
    ("MRK",      "Merck & Co.",        "US"),
    ("BMY",      "Bristol-Myers",      "US"),
    ("ABBV",     "AbbVie",             "US"),
    ("CVS",      "CVS Health",         "US"),
    ("T",        "AT&T",               "US"),
    ("VZ",       "Verizon",            "US"),
    ("MO",       "Altria Group",       "US"),
    ("IBM",      "IBM",                "US"),
    ("INTC",     "Intel",              "US"),
    ("CVX",      "Chevron",            "US"),
    ("XOM",      "ExxonMobil",         "US"),
    ("AAL",      "American Airlines",  "US"),
    ("DAL",      "Delta Air Lines",    "US"),
    ("UAL",      "United Airlines",    "US"),
    ("LUV",      "Southwest Airlines", "US"),
    ("ALK",      "Alaska Air Group",   "US"),
    ("JBLU",     "JetBlue Airways",    "US"),
    ("WBA",      "Walgreens Boots",    "US"),
    ("VFC",      "VF Corporation",     "US"),
    # 🇯🇵 Japan ADR (12)
    ("JAPSY",    "Japan Airlines",     "Japan"),
    ("ALNPY",    "ANA Holdings",       "Japan"),
    ("NTTYY",    "NTT Japan",          "Japan"),
    ("KDDIY",    "KDDI Corp.",         "Japan"),
    ("SFTBY",    "SoftBank Group",     "Japan"),
    ("TOYOF",    "Toyota Motor",       "Japan"),
    ("HNDAF",    "Honda Motor",        "Japan"),
    ("SONY",     "Sony Group",         "Japan"),
    ("MUFG",     "Mitsubishi UFJ",     "Japan"),
    ("SMFNF",    "Sumitomo Mitsui",    "Japan"),
    ("TKPHF",    "Takeda Pharma",      "Japan"),
    ("CKHUY",    "CK Hutchison",       "Japan"),
    # 🌏 Asien-Pazifik ADR (10)
    ("SINGY",    "Singapore Airlines", "Asien"),
    ("RYAAY",    "Ryanair Holdings",   "Asien"),
    ("BHP",      "BHP Group",          "Asien"),
    ("RIO",      "Rio Tinto",          "Asien"),
    ("TELNY",    "Telstra Group",      "Asien"),
    ("WBK",      "Westpac Banking",    "Asien"),
    ("CPCAY",    "Cathay Pacific",     "Asien"),
    ("KEP",      "Korean Air Lines",   "Asien"),
    ("LFC",      "China Life Ins.",    "Asien"),
    ("LNVGY",    "Lenovo Group",       "Asien"),
    # 🇨🇦 Kanada & Latam (8)
    ("CNQ",      "Canadian Nat. Res.", "Kanada"),
    ("SU",       "Suncor Energy",      "Kanada"),
    ("BCE",      "BCE Inc. (Bell)",    "Kanada"),
    ("TU",       "Telus Corp.",        "Kanada"),
    ("ENB",      "Enbridge Inc.",      "Kanada"),
    ("ACDVF",    "Air Canada",         "Kanada"),
    ("LTM",      "LATAM Airlines",     "Kanada"),
    ("VALE",     "Vale SA",            "Kanada"),
]

WATCHLIST = [
    ("JAPSY",    "Japan Airlines",     "Japan"),
    ("ALNPY",    "ANA Holdings",       "Japan"),
    ("SINGY",    "Singapore Airlines", "Asien"),
    ("AAL",      "American Airlines",  "US"),
    ("DAL",      "Delta Air Lines",    "US"),
    ("BAYN.DE",  "Bayer AG",           "DAX"),
    ("VNA.DE",   "Vonovia",            "DAX"),
    ("LHA.DE",   "Lufthansa",          "DAX"),
    ("KO",       "Coca-Cola",          "US"),
    ("PFE",      "Pfizer",             "US"),
    ("VOD",      "Vodafone",           "UK"),
    ("DTE.DE",   "Dt. Telekom",        "DAX"),
    ("T",        "AT&T",               "US"),
    ("BCE",      "BCE Inc. (Bell)",    "Kanada"),
    ("EOAN.DE",  "E.ON SE",            "DAX"),
]

REGION_FLAG = {
    "DAX": "🇩🇪", "UK": "🇬🇧", "US": "🇺🇸",
    "EU": "🇪🇺", "Japan": "🇯🇵", "Asien": "🌏", "Kanada": "🇨🇦"
}

# ── ANALYSE ────────────────────────────────────────────────────────────────
def analyze(ticker, name, market):
    try:
        time.sleep(1.0)
        df = yf.download(ticker, period="300d", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 60:
            return None

        close  = df["Close"].squeeze()
        high   = df["High"].squeeze()
        low    = df["Low"].squeeze()

        bb     = ta.volatility.BollingerBands(close=close, window=20, window_dev=2.0)
        bb_lo  = bb.bollinger_lband()
        bb_hi  = bb.bollinger_hband()
        bb_mi  = bb.bollinger_mavg()
        bb_pct = bb.bollinger_pband()
        rsi    = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        ma200  = close.rolling(200).mean()
        atr_i  = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14)
        atr_val = float(atr_i.average_true_range().iloc[-1])

        price     = float(close.iloc[-1])
        prev      = float(close.iloc[-2])
        chg       = round((price - prev) / prev * 100, 2)
        rsi_now   = round(float(rsi.iloc[-1]), 1)
        bb_lo_now = float(bb_lo.iloc[-1])
        bb_hi_now = float(bb_hi.iloc[-1])
        bb_mi_now = float(bb_mi.iloc[-1])
        bb_p_now  = round(float(bb_pct.iloc[-1]) * 100, 1)
        ma200_now = float(ma200.iloc[-1])

        prev_below = float(close.iloc[-2]) < float(bb_lo.iloc[-2])
        now_above  = price > bb_lo_now
        cond_bb    = prev_below and now_above
        cond_rsi   = rsi_now < 35
        cond_trend = price > ma200_now
        score      = sum([cond_bb, cond_rsi, cond_trend])
        sell_sig   = rsi_now > 65 and bb_p_now > 85

        stop_fix = round(price * 0.92, 2)
        stop_atr = round(price - (2 * atr_val), 2)
        stop_atr_pct = round((price - stop_atr) / price * 100, 1)
        target1  = round(bb_mi_now, 2)
        target2  = round(bb_hi_now, 2)
        pot1     = round((target1 - price) / price * 100, 1)
        pot2     = round((target2 - price) / price * 100, 1)
        fut_entry = round(bb_lo_now * 0.99, 2)
        fut_stop  = round(fut_entry * 0.92, 2)

        missing = []
        if not cond_bb:
            missing.append(f"BB-Umkehr (unter {round(bb_lo_now,2)} und Erholung)")
        if not cond_rsi:
            missing.append(f"RSI unter 35 (aktuell: {rsi_now})")
        if not cond_trend:
            missing.append(f"Preis über MA200 ({round(ma200_now,2)})")

        if score == 3:
            signal = "KAUFEN"
        elif score == 2:
            signal = "FAST"
        elif sell_sig:
            signal = "VERKAUFEN"
        elif score == 1 and cond_bb:
            signal = "BEOBACHTEN"
        else:
            signal = "NEUTRAL"

        high52 = float(close.rolling(min(252,len(close))).max().iloc[-1])
        low52  = float(close.rolling(min(252,len(close))).min().iloc[-1])
        pos52  = round((price - low52) / (high52 - low52) * 100, 1) if high52 != low52 else 50

        # Währung erkennen
        currency = "€" if market in ("DAX","EU") and not ticker.endswith(".L") else "$"
        price_fmt = f"{currency}{price:,.2f}" if currency == "$" else f"{price:,.2f} {currency}"

        return {
            "ticker": ticker, "name": name, "market": market,
            "price": round(price, 2), "price_fmt": price_fmt,
            "change": chg, "rsi": rsi_now,
            "bb_lo": round(bb_lo_now,2), "bb_hi": round(bb_hi_now,2),
            "bb_mid": round(bb_mi_now,2), "bb_pct": bb_p_now,
            "ma200": round(ma200_now,2), "pos52": pos52,
            "atr": round(atr_val,2), "atr_pct": round(atr_val/price*100,1),
            "signal": signal, "score": score,
            "stop_fix": stop_fix, "stop_atr": stop_atr,
            "stop_atr_pct": stop_atr_pct,
            "target1": target1, "target2": target2,
            "pot1": pot1, "pot2": pot2,
            "fut_entry": fut_entry, "fut_stop": fut_stop,
            "missing": missing,
            "cond_bb": cond_bb, "cond_rsi": cond_rsi, "cond_trend": cond_trend,
            "currency": currency,
        }
    except Exception as e:
        print(f"  Fehler {ticker}: {e}")
        return None


CACHE = {"data": [], "time": None, "scanning": False}
ORDER = {"KAUFEN":0, "FAST":1, "BEOBACHTEN":2, "VERKAUFEN":3, "NEUTRAL":4}


def do_scan(pairs):
    results = []
    for ticker, name, market in pairs:
        print(f"  {ticker}...", flush=True)
        r = analyze(ticker, name, market)
        if r:
            results.append(r)
    results.sort(key=lambda x: (ORDER.get(x["signal"],9), -x["score"]))
    CACHE["data"]     = results
    CACHE["time"]     = datetime.datetime.now()
    CACHE["scanning"] = False
    print("Scan abgeschlossen.", flush=True)


# ── TEMPLATE ───────────────────────────────────────────────────────────────
TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<title>TradeScan</title>
{% if scanning %}<meta http-equiv="refresh" content="30">{% endif %}
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f2f2f7;color:#1a1a1a;max-width:480px;margin:0 auto;min-height:100vh}

/* HEADER */
.hd{background:#fff;padding:14px 16px 12px;border-bottom:1px solid #f0f0f0;position:sticky;top:0;z-index:100}
.hd-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.logo-t{font-size:20px;font-weight:700;color:#1a1a1a;letter-spacing:-0.5px}
.logo-s{font-size:20px;font-weight:700;color:#1a73e8;letter-spacing:-0.5px}
.hd-date{font-size:11px;color:#bbb}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.b1{background:#1a73e8;color:#fff;border:none;border-radius:10px;padding:12px;font-size:12px;font-weight:700;cursor:pointer;letter-spacing:0.2px}
.b2{background:#fff;color:#1a1a1a;border:1.5px solid #e0e0e0;border-radius:10px;padding:12px;font-size:12px;font-weight:600;cursor:pointer}
.b1:active,.b2:active{opacity:0.8}

/* SCAN BANNER */
.scan-banner{background:#FFF8E8;border-bottom:1px solid #FFE082;padding:10px 16px;font-size:12px;font-weight:600;color:#F9A825;text-align:center}

/* SEARCH */
.srch{padding:10px 16px;background:#fff;border-bottom:1px solid #f0f0f0}
.srch-box{display:flex;align-items:center;gap:8px;background:#f5f5f5;border-radius:10px;padding:8px 12px}
.srch-box input{border:none;background:transparent;font-size:14px;color:#1a1a1a;outline:none;width:100%;font-family:inherit}
.srch-box input::placeholder{color:#bbb}
.sr-drop{background:#fff;border:0.5px solid #e0e0e0;border-radius:12px;margin-top:6px;overflow:hidden;display:none;box-shadow:0 4px 16px rgba(0,0,0,0.08)}
.sri{padding:12px 14px;border-bottom:1px solid #f5f5f5;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.sri:last-child{border-bottom:none}
.sri:active{background:#f9f9f9}
.sri-t{font-size:13px;font-weight:700;color:#1a1a1a}
.sri-n{font-size:11px;color:#aaa;margin-top:1px}

/* STATS */
.stats{display:grid;grid-template-columns:repeat(4,1fr);background:#fff;border-bottom:1px solid #f0f0f0}
.st{padding:12px 4px;text-align:center;cursor:pointer;border-right:1px solid #f5f5f5}
.st:last-child{border-right:none}
.st:active{background:#f9f9f9}
.st-v{font-size:20px;font-weight:700}
.st-l{font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:0.4px;margin-top:2px}

/* REGION CHIPS */
.chips-wrap{padding:8px 12px;background:#fff;border-bottom:1px solid #f0f0f0;overflow-x:auto;display:flex;gap:6px;-webkit-overflow-scrolling:touch}
.chips-wrap::-webkit-scrollbar{display:none}
.chip{border:1.5px solid #e8e8e8;border-radius:20px;padding:5px 12px;font-size:11px;font-weight:600;color:#888;white-space:nowrap;background:#fff;cursor:pointer;flex-shrink:0;transition:all 0.15s}
.chip.on{color:#fff!important;border-color:transparent!important;background:#1a73e8!important}

/* SECTION HEADER */
.sh{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;background:#f8f8f8;border-bottom:1px solid #f0f0f0}
.sh-t{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.6px}
.sh-a{font-size:12px;font-weight:600;color:#1a73e8;cursor:pointer}

/* LIST ROW */
.row{display:flex;justify-content:space-between;align-items:center;padding:13px 16px;border-bottom:1px solid #f5f5f5;background:#fff;cursor:pointer;text-decoration:none;color:inherit}
.row:active{background:#f9f9f9}
.row-l{display:flex;align-items:center;gap:10px}
.dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.tk{font-size:14px;font-weight:700;color:#1a1a1a}
.nm{font-size:11px;color:#aaa;margin-top:1px}
.row-r{display:flex;align-items:center;gap:8px}
.pr{font-size:13px;font-weight:600;color:#1a1a1a;text-align:right}
.ch{font-size:11px;text-align:right;margin-top:1px}
.bdg{padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;white-space:nowrap}
.arr{color:#ddd;font-size:14px;margin-left:2px}

/* VIEW ALL BTN */
.va-btn{margin:12px 16px 16px;border:1.5px solid #1a73e8;border-radius:12px;padding:12px;text-align:center;font-size:13px;font-weight:700;color:#1a73e8;cursor:pointer;background:#fff}
.va-btn:active{background:#f0f4ff}

/* BACK NAV */
.nav{display:flex;align-items:center;gap:12px;padding:12px 16px;background:#fff;border-bottom:1px solid #f0f0f0;position:sticky;top:0;z-index:100}
.nav-back{background:#f5f5f5;border:none;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;color:#1a1a1a}
.nav-title{font-size:15px;font-weight:700;color:#1a1a1a}
.nav-sub{font-size:11px;color:#aaa;margin-top:1px}

/* ALL SECTION HEADER */
.ash{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;background:#f8f8f8;border-bottom:1px solid #f0f0f0}
.ash-t{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.6px}
.ash-c{font-size:12px;font-weight:700;color:#1a73e8}

/* DETAIL */
.det-hero{padding:18px 16px;background:#fff;border-bottom:1px solid #f0f0f0}
.det-p{font-size:30px;font-weight:700;color:#1a1a1a}
.det-chg{font-size:14px;margin-top:3px}
.det-badge{display:inline-block;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:700;margin-top:10px}
.cks{display:flex;gap:6px;margin-top:12px}
.ck{border-radius:8px;padding:8px 10px;text-align:center;flex:1}
.ck-i{font-size:15px}
.ck-l{font-size:9px;margin-top:3px}
.det-sec{padding:14px 16px;background:#fff;border-bottom:1px solid #f0f0f0}
.dst{font-size:10px;font-weight:700;color:#aaa;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:10px}
.dr{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f8f8f8;font-size:13px}
.dr:last-child{border-bottom:none}
.dl{color:#888}.dv{font-weight:600;color:#1a1a1a}
.dg{font-weight:600;color:#00A65A}.dr2{font-weight:600;color:#E8333C}
.fb{background:#EEF3FF;border-radius:10px;padding:12px;margin-top:6px}
.fr{display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(44,94,232,0.08)}
.fr:last-child{border-bottom:none}
.fl{color:#4A6FE3}.fv{font-weight:600;color:#1a1a1a}
.hint{font-size:12px;color:#4A6FE3;margin-top:8px;line-height:1.5}
.sell-box{background:#FFF0F0;border-radius:10px;padding:12px;margin-top:6px}
.sb-row{display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(232,51,60,0.08)}
.sb-row:last-child{border-bottom:none}
.sl{color:#E8333C}.sv{font-weight:600;color:#1a1a1a}

/* EMPTY STATE */
.empty{text-align:center;padding:48px 24px;color:#aaa}
.empty-i{font-size:48px;margin-bottom:12px}
.empty-t{font-size:16px;font-weight:600;color:#888;margin-bottom:6px}
.empty-s{font-size:13px;line-height:1.6}
</style>
</head>
<body>

<!-- ══════════ HOME VIEW ══════════ -->
<div id="vHome">
  <div class="hd">
    <div class="hd-top">
      <div><span class="logo-t">TRADE</span><span class="logo-s">SCAN</span></div>
      <div class="hd-date">{{ scan_time }}</div>
    </div>
    <div class="btns">
      <form method="post" action="/scan" style="margin:0;flex:1">
        <button class="b1" type="submit" style="width:100%">▶ Vollscan ({{ total_tickers }})</button>
      </form>
      <form method="post" action="/scan-wl" style="margin:0;flex:1">
        <button class="b2" type="submit" style="width:100%">◎ Watchlist ({{ wl_count }})</button>
      </form>
    </div>
  </div>

  {% if scanning %}
  <div class="scan-banner">⏳ Scan läuft... Seite aktualisiert sich automatisch</div>
  {% endif %}

  <div class="srch">
    <div class="srch-box">
      <span style="color:#ccc;font-size:14px">⌕</span>
      <input type="text" id="si" placeholder="Aktie suchen... z.B. BAYN, Japan, Vodafone" oninput="doSearch(this.value)" autocomplete="off">
    </div>
    <div class="sr-drop" id="sr"></div>
  </div>

  <div class="stats">
    <div class="st" onclick="openAll('KAUFEN')">
      <div class="st-v" style="color:#00A65A">{{ kaufen }}</div>
      <div class="st-l">Kaufen</div>
    </div>
    <div class="st" onclick="openAll('FAST')">
      <div class="st-v" style="color:#FF6200">{{ fast }}</div>
      <div class="st-l">Fast</div>
    </div>
    <div class="st" onclick="openAll('VERKAUFEN')">
      <div class="st-v" style="color:#E8333C">{{ verkaufen }}</div>
      <div class="st-l">Verkaufen</div>
    </div>
    <div class="st" onclick="openAll('ALLE')">
      <div class="st-v" style="color:#1a73e8">{{ total }}</div>
      <div class="st-l">Alle →</div>
    </div>
  </div>

  <div class="chips-wrap" id="regionChips">
    <div class="chip on" onclick="filterRegion('alle',this)">Alle</div>
    <div class="chip" onclick="filterRegion('DAX',this)">🇩🇪 DAX</div>
    <div class="chip" onclick="filterRegion('UK',this)">🇬🇧 UK</div>
    <div class="chip" onclick="filterRegion('US',this)">🇺🇸 US</div>
    <div class="chip" onclick="filterRegion('EU',this)">🇪🇺 EU</div>
    <div class="chip" onclick="filterRegion('Japan',this)">🇯🇵 Japan</div>
    <div class="chip" onclick="filterRegion('Asien',this)">🌏 Asien</div>
    <div class="chip" onclick="filterRegion('Kanada',this)">🇨🇦 Kanada</div>
  </div>

  {% if not data %}
  <div class="empty">
    <div class="empty-i">📊</div>
    <div class="empty-t">Noch keine Daten</div>
    <div class="empty-s">Tippe auf Vollscan oder Watchlist<br>um die Analyse zu starten.</div>
  </div>
  {% else %}
  <div id="homeList">
    {% for sig, sig_label, sig_dot in [
        ('KAUFEN','✓ Jetzt kaufen','#00A65A'),
        ('FAST','~ Morgen prüfen','#FF6200'),
        ('VERKAUFEN','↓ Jetzt verkaufen','#E8333C')
    ] %}
    {% set group = data | selectattr('signal','equalto',sig) | list %}
    {% if group %}
    {% set top3 = group[:3] %}
    {% set total_g = group | length %}
    <div class="sh" id="sh-{{ sig }}">
      <span class="sh-t">{{ sig_label }}</span>
      <span class="sh-a" onclick="openAll('{{ sig }}')">Alle {{ total_g }} →</span>
    </div>
    {% for r in top3 %}
    <div class="row" onclick="openDetail('{{ r.ticker }}')">
      <div class="row-l">
        <div class="dot" style="background:{{ sig_dot }}"></div>
        <div>
          <div class="tk">{{ r.ticker }}</div>
          <div class="nm">{{ r.name }} · {{ {'DAX':'🇩🇪','UK':'🇬🇧','US':'🇺🇸','EU':'🇪🇺','Japan':'🇯🇵','Asien':'🌏','Kanada':'🇨🇦'}.get(r.market,'') }} {{ r.market }}</div>
        </div>
      </div>
      <div class="row-r">
        <div>
          <div class="pr">{{ r.price_fmt }}</div>
          <div class="ch" style="color:{{'#00A65A' if r.change>=0 else '#E8333C'}}">{{ '+' if r.change>=0 else '' }}{{ r.change }}%</div>
        </div>
        {% if sig == 'KAUFEN' %}<span class="bdg" style="background:#E8F8F1;color:#00763D">Kaufen</span>
        {% elif sig == 'FAST' %}<span class="bdg" style="background:#FFF3E8;color:#CC4E00">Fast</span>
        {% else %}<span class="bdg" style="background:#FFF0F0;color:#E8333C">Verkaufen</span>{% endif %}
        <span class="arr">›</span>
      </div>
    </div>
    {% endfor %}
    {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  {% if data %}
  <div class="va-btn" onclick="openAll('ALLE')">Alle {{ total }} Aktien anzeigen →</div>
  {% endif %}
</div>

<!-- ══════════ ALL VIEW ══════════ -->
<div id="vAll" style="display:none">
  <div class="nav">
    <button class="nav-back" onclick="show('vHome')">‹ Zurück</button>
    <div>
      <div class="nav-title" id="allTitle">Alle Aktien</div>
      <div class="nav-sub" id="allSub"></div>
    </div>
  </div>
  <div id="allList"></div>
</div>

<!-- ══════════ DETAIL VIEW ══════════ -->
<div id="vDetail" style="display:none">
  <div class="nav">
    <button class="nav-back" id="detBack" onclick="show('vHome')">‹ Zurück</button>
    <div>
      <div class="nav-title" id="dTicker"></div>
      <div class="nav-sub" id="dName"></div>
    </div>
  </div>
  <div id="dContent"></div>
</div>

<script>
// ── DATA aus Flask ──────────────────────────────────────────────────────────
const ALL_DATA = {{ data_json }};
const FLAGS = {DAX:'🇩🇪',UK:'🇬🇧',US:'🇺🇸',EU:'🇪🇺',Japan:'🇯🇵',Asien:'🌏',Kanada:'🇨🇦'};
const SIG_CFG = {
  KAUFEN:    {dot:'#00A65A', bg:'#E8F8F1', col:'#00763D', lbl:'Kaufen'},
  FAST:      {dot:'#FF6200', bg:'#FFF3E8', col:'#CC4E00', lbl:'Fast'},
  BEOBACHTEN:{dot:'#4a90d9', bg:'#EEF5FF', col:'#1a5fb4', lbl:'Watch'},
  VERKAUFEN: {dot:'#E8333C', bg:'#FFF0F0', col:'#E8333C', lbl:'Verkaufen'},
  NEUTRAL:   {dot:'#ccc',    bg:'#F5F5F5', col:'#888',    lbl:'Abwarten'}
};
const SEC_NAMES = {
  KAUFEN:'✓ Jetzt kaufen', FAST:'~ Morgen prüfen',
  BEOBACHTEN:'◎ Beobachten', VERKAUFEN:'↓ Jetzt verkaufen', NEUTRAL:'◎ Abwarten'
};
let activeRegion = 'alle';

// ── VIEWS ───────────────────────────────────────────────────────────────────
function show(id) {
  ['vHome','vAll','vDetail'].forEach(v => {
    document.getElementById(v).style.display = v===id ? 'block' : 'none';
  });
  window.scrollTo(0,0);
}

// ── ALL VIEW ─────────────────────────────────────────────────────────────────
function openAll(filter) {
  show('vAll');
  const titles = {ALLE:'Alle Aktien',KAUFEN:'Kaufsignale',FAST:'Morgen prüfen',VERKAUFEN:'Verkaufssignale'};
  document.getElementById('allTitle').textContent = titles[filter] || filter;
  let data = filter==='ALLE' ? ALL_DATA : ALL_DATA.filter(s=>s.signal===filter);
  document.getElementById('allSub').textContent = data.length + ' Werte';

  const groups = {KAUFEN:[],FAST:[],BEOBACHTEN:[],VERKAUFEN:[],NEUTRAL:[]};
  data.forEach(s=>(groups[s.signal]||groups.NEUTRAL).push(s));

  let html = '';
  for(const key of ['KAUFEN','FAST','BEOBACHTEN','VERKAUFEN','NEUTRAL']) {
    if(!groups[key].length) continue;
    html += `<div class="ash"><span class="ash-t">${SEC_NAMES[key]}</span><span class="ash-c">${groups[key].length}</span></div>`;
    groups[key].forEach(s => { html += rowHTML(s); });
  }
  if(!html) html='<div class="empty"><div class="empty-i">🔍</div><div class="empty-t">Keine Daten</div><div class="empty-s">Bitte zuerst einen Scan starten.</div></div>';
  document.getElementById('allList').innerHTML = html;
}

function rowHTML(s) {
  const c = SIG_CFG[s.signal] || SIG_CFG.NEUTRAL;
  const chgCol = s.change >= 0 ? '#00A65A' : '#E8333C';
  const chgStr = (s.change >= 0 ? '+' : '') + s.change + '%';
  return `<div class="row" onclick="openDetail('${s.ticker}')">
    <div class="row-l">
      <div class="dot" style="background:${c.dot}"></div>
      <div><div class="tk">${s.ticker}</div><div class="nm">${s.name} · ${FLAGS[s.market]||''} ${s.market}</div></div>
    </div>
    <div class="row-r">
      <div><div class="pr">${s.price_fmt}</div><div class="ch" style="color:${chgCol}">${chgStr}</div></div>
      <span class="bdg" style="background:${c.bg};color:${c.col}">${c.lbl}</span>
      <span class="arr">›</span>
    </div>
  </div>`;
}

// ── REGION FILTER ─────────────────────────────────────────────────────────────
function filterRegion(region, el) {
  activeRegion = region;
  document.querySelectorAll('#regionChips .chip').forEach(c=>c.classList.remove('on'));
  el.classList.add('on');
  rebuildHome();
}

function rebuildHome() {
  const list = document.getElementById('homeList');
  if(!list) return;
  let data = activeRegion==='alle' ? ALL_DATA : ALL_DATA.filter(s=>s.market===activeRegion);

  let html = '';
  const sigs = [
    ['KAUFEN','✓ Jetzt kaufen','#00A65A'],
    ['FAST','~ Morgen prüfen','#FF6200'],
    ['VERKAUFEN','↓ Jetzt verkaufen','#E8333C']
  ];
  for(const [sig, lbl, dot] of sigs) {
    const group = data.filter(s=>s.signal===sig);
    if(!group.length) continue;
    const top3 = group.slice(0,3);
    const c = SIG_CFG[sig];
    html += `<div class="sh"><span class="sh-t">${lbl}</span><span class="sh-a" onclick="openAll('${sig}')">Alle ${group.length} →</span></div>`;
    top3.forEach(s=>{
      const chgCol = s.change>=0?'#00A65A':'#E8333C';
      html += `<div class="row" onclick="openDetail('${s.ticker}')">
        <div class="row-l"><div class="dot" style="background:${dot}"></div>
          <div><div class="tk">${s.ticker}</div><div class="nm">${s.name} · ${FLAGS[s.market]||''} ${s.market}</div></div>
        </div>
        <div class="row-r">
          <div><div class="pr">${s.price_fmt}</div><div class="ch" style="color:${chgCol}">${(s.change>=0?'+':'')+s.change}%</div></div>
          <span class="bdg" style="background:${c.bg};color:${c.col}">${c.lbl}</span>
          <span class="arr">›</span>
        </div>
      </div>`;
    });
  }
  if(!html) html='<div class="empty"><div class="empty-i">🔍</div><div class="empty-t">Keine Signale</div><div class="empty-s">Für diese Region wurden keine Signale gefunden.</div></div>';
  list.innerHTML = html;
}

// ── DETAIL VIEW ───────────────────────────────────────────────────────────────
let _prevView = 'vHome';
function openDetail(ticker) {
  const s = ALL_DATA.find(x=>x.ticker===ticker);
  if(!s) return;

  // remember where we came from
  if(document.getElementById('vAll').style.display !== 'none') _prevView = 'vAll';
  else _prevView = 'vHome';
  document.getElementById('detBack').onclick = ()=>show(_prevView);

  show('vDetail');
  document.getElementById('dTicker').textContent = s.ticker;
  document.getElementById('dName').textContent = s.name + ' · ' + (FLAGS[s.market]||'') + ' ' + s.market;

  const c = SIG_CFG[s.signal] || SIG_CFG.NEUTRAL;
  const chgCol = s.change>=0?'#00A65A':'#E8333C';
  const chgStr = (s.change>=0?'+':'')+s.change+'%';

  const ckBB  = s.cond_bb    ? `<div class="ck" style="background:#E8F8F1"><div class="ck-i">✓</div><div class="ck-l" style="color:#00763D">BB-Umkehr</div></div>`
                             : `<div class="ck" style="background:#F5F5F5"><div class="ck-i" style="color:#ccc">✗</div><div class="ck-l" style="color:#bbb">BB-Umkehr</div></div>`;
  const ckRSI = s.cond_rsi   ? `<div class="ck" style="background:#E8F8F1"><div class="ck-i">✓</div><div class="ck-l" style="color:#00763D">RSI ${s.rsi}</div></div>`
                             : `<div class="ck" style="background:#F5F5F5"><div class="ck-i" style="color:#ccc">✗</div><div class="ck-l" style="color:#bbb">RSI ${s.rsi}</div></div>`;
  const ckTrend = s.cond_trend ? `<div class="ck" style="background:#E8F8F1"><div class="ck-i">✓</div><div class="ck-l" style="color:#00763D">Trend ↑</div></div>`
                              : `<div class="ck" style="background:#F5F5F5"><div class="ck-i" style="color:#ccc">✗</div><div class="ck-l" style="color:#bbb">Trend ↑</div></div>`;

  let actionHTML = '';
  if(s.signal === 'KAUFEN') {
    actionHTML = `<div class="det-sec">
      <div class="dst">Trade-Details</div>
      <div class="dr"><span class="dl">Kaufen bei</span><span class="dv">${s.price_fmt}</span></div>
      <div class="dr"><span class="dl">Stop-Loss (8% fix)</span><span class="dr2">${s.stop_fix} (−8%)</span></div>
      <div class="dr"><span class="dl">Stop-Loss (ATR 2×)</span><span class="dr2">${s.stop_atr} (−${s.stop_atr_pct}%)</span></div>
      <div class="dr"><span class="dl">Ziel 1 — MA20</span><span class="dg">${s.target1} (+${s.pot1}%)</span></div>
      <div class="dr"><span class="dl">Ziel 2 — ob. BB</span><span class="dg">${s.target2} (+${s.pot2}%)</span></div>
      <div class="dr"><span class="dl">Haltedauer</span><span class="dv">2–6 Wochen</span></div>
      <div class="dr"><span class="dl">Max. Position</span><span class="dv">10% des Kapitals</span></div>
    </div>
    <div class="det-sec">
      <div class="dst">Technische Werte</div>
      <div class="dr"><span class="dl">RSI (14)</span><span class="dg">${s.rsi} — überverkauft</span></div>
      <div class="dr"><span class="dl">BB Position</span><span class="dv">${s.bb_pct}%</span></div>
      <div class="dr"><span class="dl">MA200</span><span class="dv">${s.ma200}</span></div>
      <div class="dr"><span class="dl">52W-Position</span><span class="dv">${s.pos52}%</span></div>
      <div class="dr"><span class="dl">ATR (14)</span><span class="dv">${s.atr} (${s.atr_pct}%)</span></div>
    </div>`;
  } else if(s.signal === 'FAST') {
    const missing = s.missing.map(m=>`<div class="hint">→ ${m}</div>`).join('');
    actionHTML = `<div class="det-sec">
      <div class="dst">Zukünftiger Einstieg</div>
      <div class="fb">
        <div class="fr"><span class="fl">Möglicher Einstieg</span><span class="fv">${s.fut_entry}</span></div>
        <div class="fr"><span class="fl">Stop-Loss dann</span><span class="fv" style="color:#E8333C">${s.fut_stop} (−8%)</span></div>
        <div class="fr"><span class="fl">Ziel 1 — MA20</span><span class="fv" style="color:#00A65A">${s.target1} (+${s.pot1}%)</span></div>
        <div class="fr"><span class="fl">Ziel 2 — ob. BB</span><span class="fv" style="color:#00A65A">${s.target2} (+${s.pot2}%)</span></div>
      </div>
      <div style="margin-top:10px"><div style="font-size:10px;font-weight:700;color:#aaa;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px">Was muss noch passieren?</div>${missing}</div>
    </div>
    <div class="det-sec">
      <div class="dst">Technische Werte</div>
      <div class="dr"><span class="dl">RSI (14)</span><span class="dv">${s.rsi}</span></div>
      <div class="dr"><span class="dl">MA200</span><span class="dv">${s.ma200}</span></div>
      <div class="dr"><span class="dl">ATR (14)</span><span class="dv">${s.atr} (${s.atr_pct}%)</span></div>
    </div>`;
  } else if(s.signal === 'VERKAUFEN') {
    actionHTML = `<div class="det-sec">
      <div class="dst">Verkauf-Signal</div>
      <div class="sell-box">
        <div class="sb-row"><span class="sl">RSI (überkauft)</span><span class="sv">${s.rsi}</span></div>
        <div class="sb-row"><span class="sl">BB-Position</span><span class="sv">${s.bb_pct}%</span></div>
        <div class="sb-row"><span class="sl">Empfehlung</span><span class="sv">Position jetzt schliessen</span></div>
      </div>
      <div class="hint" style="margin-top:10px;color:#E8333C">⚠ Ziel erreicht — Gewinn sichern!</div>
    </div>`;
  } else {
    const missing = s.missing.map(m=>`<div class="hint">→ ${m}</div>`).join('');
    actionHTML = `<div class="det-sec">
      <div class="dst">Zukünftiger Einstieg</div>
      <div class="fb">
        <div class="fr"><span class="fl">Möglicher Einstieg</span><span class="fv">${s.fut_entry}</span></div>
        <div class="fr"><span class="fl">Stop-Loss dann</span><span class="fv" style="color:#E8333C">${s.fut_stop}</span></div>
        <div class="fr"><span class="fl">Ziel 1 — MA20</span><span class="fv" style="color:#00A65A">${s.target1}</span></div>
      </div>
      <div style="margin-top:10px"><div style="font-size:10px;font-weight:700;color:#aaa;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px">Was muss noch passieren?</div>${missing}</div>
    </div>`;
  }

  document.getElementById('dContent').innerHTML = `
    <div class="det-hero">
      <div class="det-p">${s.price_fmt}</div>
      <div class="det-chg" style="color:${chgCol}">${chgStr} heute</div>
      <span class="det-badge" style="background:${c.bg};color:${c.col}">${c.lbl}</span>
      <div class="cks">${ckBB}${ckRSI}${ckTrend}</div>
    </div>
    ${actionHTML}`;
}

// ── SUCHE ────────────────────────────────────────────────────────────────────
function doSearch(v) {
  const r = document.getElementById('sr');
  if(!v || v.length < 2) { r.style.display='none'; return; }
  const m = ALL_DATA.filter(s =>
    s.ticker.toLowerCase().includes(v.toLowerCase()) ||
    s.name.toLowerCase().includes(v.toLowerCase()) ||
    s.market.toLowerCase().includes(v.toLowerCase())
  ).slice(0,6);
  if(!m.length) { r.style.display='none'; return; }
  r.innerHTML = m.map(s => {
    const c = SIG_CFG[s.signal]||SIG_CFG.NEUTRAL;
    return `<div class="sri" onclick="document.getElementById('si').value='';document.getElementById('sr').style.display='none';openDetail('${s.ticker}')">
      <div><div class="sri-t">${s.ticker}</div><div class="sri-n">${s.name} · ${FLAGS[s.market]||''} ${s.market}</div></div>
      <span class="bdg" style="background:${c.bg};color:${c.col}">${c.lbl}</span>
    </div>`;
  }).join('');
  r.style.display = 'block';
}

// Suche schliessen bei Klick außerhalb
document.addEventListener('click', e => {
  if(!e.target.closest('.srch')) document.getElementById('sr').style.display='none';
});
</script>
</body>
</html>"""


# ── ROUTES ─────────────────────────────────────────────────────────────────
import json

@app.route("/")
def index():
    import json as _json
    data = CACHE["data"]
    scanning = CACHE.get("scanning", False)
    now = CACHE["time"]

    kaufen    = len([r for r in data if r["signal"] == "KAUFEN"])
    fast      = len([r for r in data if r["signal"] == "FAST"])
    verkaufen = len([r for r in data if r["signal"] == "VERKAUFEN"])
    total     = len(data)

    # JSON für JS
    data_json = _json.dumps(data, ensure_ascii=False)

    return render_template_string(
        TEMPLATE,
        data=data,
        data_json=data_json,
        kaufen=kaufen,
        fast=fast,
        verkaufen=verkaufen,
        total=total,
        total_tickers=len(TICKERS),
        wl_count=len(WATCHLIST),
        scan_time=now.strftime("Stand: %d.%m.%Y %H:%M Uhr") if now else "Noch kein Scan",
        scanning=scanning,
    )


@app.route("/scan", methods=["POST"])
def scan_all():
    import threading
    if not CACHE.get("scanning"):
        CACHE["scanning"] = True
        threading.Thread(target=do_scan, args=(TICKERS,), daemon=True).start()
    return redirect("/?scanning=1")


@app.route("/scan-wl", methods=["POST"])
def scan_wl():
    import threading
    if not CACHE.get("scanning"):
        CACHE["scanning"] = True
        threading.Thread(target=do_scan, args=(WATCHLIST,), daemon=True).start()
    return redirect("/?scanning=1")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
