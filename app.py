"""
TradeScan - Christoph Range-Reversion Strategie
Datenquelle: Yahoo Finance (funktioniert auf Hetzner!)
"""
import datetime, time, os, threading
import pandas as pd
import yfinance as yf
import ta
from flask import Flask, render_template_string, redirect
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

app = Flask(__name__)

TICKERS = [
    ("BAYN.DE","Bayer AG","DAX"),("VNA.DE","Vonovia","DAX"),
    ("DTE.DE","Dt. Telekom","DAX"),("EOAN.DE","E.ON SE","DAX"),
    ("RWE.DE","RWE AG","DAX"),("HEN3.DE","Henkel","DAX"),
    ("MUV2.DE","Munich Re","DAX"),("ALV.DE","Allianz SE","DAX"),
    ("DBK.DE","Deutsche Bank","DAX"),("CBK.DE","Commerzbank","DAX"),
    ("BAS.DE","BASF SE","DAX"),("BMW.DE","BMW AG","DAX"),
    ("MBG.DE","Mercedes-Benz","DAX"),("LHA.DE","Lufthansa","DAX"),
    ("SIE.DE","Siemens AG","DAX"),("ADS.DE","Adidas","DAX"),
    ("SHL.DE","Siemens Health.","DAX"),("DHER.DE","Delivery Hero","DAX"),
    ("ZAL.DE","Zalando","DAX"),("CON.DE","Covestro","DAX"),
    ("SHEL","Shell plc","UK"),("BP","BP plc","UK"),
    ("GSK","GSK plc","UK"),("AZN","AstraZeneca","UK"),
    ("UL","Unilever","UK"),("HSBC","HSBC Holdings","UK"),
    ("LYG","Lloyds Banking","UK"),("BCS","Barclays","UK"),
    ("VOD","Vodafone","UK"),("DEO","Diageo","UK"),
    ("BTI","Brit. Am. Tobacco","UK"),("RBGLY","Reckitt","UK"),
    ("IMBBY","Imperial Brands","UK"),
    ("SAN","Sanofi","EU"),("TEF","Telefonica","EU"),
    ("ENI","ENI SpA","EU"),("BNPQF","BNP Paribas","EU"),
    ("TTE","TotalEnergies","EU"),("BUD","AB InBev","EU"),
    ("PHG","Philips","EU"),("ICAGY","IAG","EU"),
    ("LRLCY","L'Oreal","EU"),("NVO","Novo Nordisk","EU"),
    ("KO","Coca-Cola","US"),("PEP","PepsiCo","US"),
    ("PG","Procter & Gamble","US"),("KHC","Kraft Heinz","US"),
    ("MDLZ","Mondelez","US"),("KDP","Keurig Dr Pepper","US"),
    ("GIS","General Mills","US"),("CPB","Campbell Soup","US"),
    ("CL","Colgate-Palmolive","US"),("JNJ","Johnson & Johnson","US"),
    ("PFE","Pfizer","US"),("MRK","Merck & Co.","US"),
    ("BMY","Bristol-Myers","US"),("ABBV","AbbVie","US"),
    ("CVS","CVS Health","US"),("T","AT&T","US"),
    ("VZ","Verizon","US"),("MO","Altria Group","US"),
    ("IBM","IBM","US"),("INTC","Intel","US"),
    ("CVX","Chevron","US"),("XOM","ExxonMobil","US"),
    ("AAL","American Airlines","US"),("DAL","Delta Air Lines","US"),
    ("UAL","United Airlines","US"),("LUV","Southwest Airlines","US"),
    ("ALK","Alaska Air Group","US"),("JBLU","JetBlue Airways","US"),
    ("WBA","Walgreens Boots","US"),("VFC","VF Corporation","US"),
    ("JAPSY","Japan Airlines","Japan"),("ALNPY","ANA Holdings","Japan"),
    ("NTTYY","NTT Japan","Japan"),("KDDIY","KDDI Corp.","Japan"),
    ("SFTBY","SoftBank Group","Japan"),("TOYOF","Toyota Motor","Japan"),
    ("HNDAF","Honda Motor","Japan"),("SONY","Sony Group","Japan"),
    ("MUFG","Mitsubishi UFJ","Japan"),("TKPHF","Takeda Pharma","Japan"),
    ("SINGY","Singapore Airlines","Asien"),("RYAAY","Ryanair","Asien"),
    ("BHP","BHP Group","Asien"),("RIO","Rio Tinto","Asien"),
    ("CPCAY","Cathay Pacific","Asien"),("KEP","Korean Air","Asien"),
    ("LFC","China Life Ins.","Asien"),("LNVGY","Lenovo Group","Asien"),
    ("CNQ","Canadian Nat. Res.","Kanada"),("SU","Suncor Energy","Kanada"),
    ("BCE","BCE Inc.","Kanada"),("TU","Telus Corp.","Kanada"),
    ("ENB","Enbridge Inc.","Kanada"),("LTM","LATAM Airlines","Kanada"),
    ("VALE","Vale SA","Kanada"),
]

WATCHLIST = [
    ("JAPSY","Japan Airlines","Japan"),("ALNPY","ANA Holdings","Japan"),
    ("SINGY","Singapore Airlines","Asien"),("AAL","American Airlines","US"),
    ("DAL","Delta Air Lines","US"),("KO","Coca-Cola","US"),
    ("PFE","Pfizer","US"),("T","AT&T","US"),("VZ","Verizon","US"),
    ("VOD","Vodafone","UK"),("GSK","GSK plc","UK"),("BP","BP plc","UK"),
    ("BCE","BCE Inc.","Kanada"),("SAN","Sanofi","EU"),("TTE","TotalEnergies","EU"),
]

def fetch_yf(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 60:
            return ticker, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open","High","Low","Close"]].dropna()
        return ticker, df
    except Exception as e:
        print(f"  YF Fehler {ticker}: {e}", flush=True)
        return ticker, None

def fetch_all(pairs):
    results = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_yf, p[0]): p for p in pairs}
        for f in as_completed(futures):
            ticker, df = f.result()
            if df is not None:
                results[ticker] = df
                print(f"  OK: {ticker}", flush=True)
            else:
                print(f"  Keine Daten: {ticker}", flush=True)
    return results

def analyze(ticker, name, market, df):
    try:
        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()
        if len(close) < 60: return None

        bb     = ta.volatility.BollingerBands(close=close, window=20, window_dev=2.0)
        rsi    = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        ma200  = close.rolling(200).mean()
        atr_i  = ta.volatility.AverageTrueRange(high=high,low=low,close=close,window=14)
        atr_val= float(atr_i.average_true_range().iloc[-1])

        price     = float(close.iloc[-1])
        prev      = float(close.iloc[-2])
        chg       = round((price-prev)/prev*100,2)
        rsi_now   = round(float(rsi.iloc[-1]),1)
        bb_lo_now = float(bb.bollinger_lband().iloc[-1])
        bb_hi_now = float(bb.bollinger_hband().iloc[-1])
        bb_mi_now = float(bb.bollinger_mavg().iloc[-1])
        bb_p_now  = round(float(bb.bollinger_pband().iloc[-1])*100,1)
        ma200_now = float(ma200.iloc[-1])

        cond_bb    = float(close.iloc[-2]) < float(bb.bollinger_lband().iloc[-2]) and price > bb_lo_now
        cond_rsi   = rsi_now < 35
        cond_trend = price > ma200_now
        score      = sum([cond_bb, cond_rsi, cond_trend])
        sell_sig   = rsi_now > 65 and bb_p_now > 85

        stop_fix     = round(price*0.92,2)
        stop_atr     = round(price-(2*atr_val),2)
        stop_atr_pct = round((price-stop_atr)/price*100,1)
        target1      = round(bb_mi_now,2)
        target2      = round(bb_hi_now,2)
        pot1         = round((target1-price)/price*100,1)
        pot2         = round((target2-price)/price*100,1)

        missing = []
        if not cond_bb:    missing.append(f"BB-Umkehr (aktuell: {round(bb_lo_now,2)})")
        if not cond_rsi:   missing.append(f"RSI unter 35 (aktuell: {rsi_now})")
        if not cond_trend: missing.append(f"Preis ueber MA200 ({round(ma200_now,2)})")

        if score==3:             signal="KAUFEN"
        elif score==2:           signal="FAST"
        elif sell_sig:           signal="VERKAUFEN"
        elif score==1 and cond_bb: signal="BEOBACHTEN"
        else:                    signal="NEUTRAL"

        high52 = float(close.rolling(min(252,len(close))).max().iloc[-1])
        low52  = float(close.rolling(min(252,len(close))).min().iloc[-1])
        pos52  = round((price-low52)/(high52-low52)*100,1) if high52!=low52 else 50

        if market=="DAX":      price_fmt=f"{price:,.2f} EUR"
        elif market=="UK":     price_fmt=f"{price:,.2f} GBP"
        else:                  price_fmt=f"${price:,.2f}"

        return {
            "ticker":ticker,"name":name,"market":market,
            "price":round(price,2),"price_fmt":price_fmt,
            "change":chg,"rsi":rsi_now,
            "bb_lo":round(bb_lo_now,2),"bb_hi":round(bb_hi_now,2),
            "bb_mid":round(bb_mi_now,2),"bb_pct":bb_p_now,
            "ma200":round(ma200_now,2),"pos52":pos52,
            "atr":round(atr_val,2),"atr_pct":round(atr_val/price*100,1),
            "signal":signal,"score":score,
            "stop_fix":stop_fix,"stop_atr":stop_atr,"stop_atr_pct":stop_atr_pct,
            "target1":target1,"target2":target2,"pot1":pot1,"pot2":pot2,
            "fut_entry":round(bb_lo_now*0.99,2),"fut_stop":round(bb_lo_now*0.99*0.92,2),
            "missing":missing,
            "cond_bb":cond_bb,"cond_rsi":cond_rsi,"cond_trend":cond_trend,
        }
    except Exception as e:
        print(f"  Analyse-Fehler {ticker}: {e}", flush=True)
        return None

CACHE = {"data":[],"time":None,"scanning":False}
ORDER = {"KAUFEN":0,"FAST":1,"BEOBACHTEN":2,"VERKAUFEN":3,"NEUTRAL":4}

def do_scan(pairs):
    print(f"  Scan: {len(pairs)} Aktien via Yahoo Finance...", flush=True)
    all_data = fetch_all(pairs)
    results = []
    for ticker, name, market in pairs:
        df = all_data.get(ticker)
        if df is None: continue
        r = analyze(ticker, name, market, df)
        if r: results.append(r)
    results.sort(key=lambda x:(ORDER.get(x["signal"],9),-x["score"]))
    CACHE["data"]=results
    CACHE["time"]=datetime.datetime.now()
    CACHE["scanning"]=False
    print(f"Scan fertig: {len(results)} Aktien.", flush=True)

TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>TradeScan</title>
{% if scanning %}<meta http-equiv="refresh" content="15">{% endif %}
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f2f2f7;color:#1a1a1a;max-width:480px;margin:0 auto;min-height:100vh}
.hd{background:#fff;padding:14px 16px 12px;border-bottom:1px solid #f0f0f0;position:sticky;top:0;z-index:100}
.hd-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.logo-t{font-size:20px;font-weight:700;color:#1a1a1a}.logo-s{font-size:20px;font-weight:700;color:#1a73e8}
.hd-date{font-size:11px;color:#bbb}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.b1{background:#1a73e8;color:#fff;border:none;border-radius:10px;padding:12px;font-size:12px;font-weight:700;cursor:pointer;width:100%}
.b2{background:#fff;color:#1a1a1a;border:1.5px solid #e0e0e0;border-radius:10px;padding:12px;font-size:12px;font-weight:600;cursor:pointer;width:100%}
.scan-banner{background:#EEF8FF;border-bottom:1px solid #90CAF9;padding:10px 16px;font-size:12px;font-weight:600;color:#1565C0;text-align:center}
.srch{padding:10px 16px;background:#fff;border-bottom:1px solid #f0f0f0}
.srch-box{display:flex;align-items:center;gap:8px;background:#f5f5f5;border-radius:10px;padding:8px 12px}
.srch-box input{border:none;background:transparent;font-size:14px;color:#1a1a1a;outline:none;width:100%;font-family:inherit}
.srch-box input::placeholder{color:#bbb}
.sr-drop{background:#fff;border:0.5px solid #e0e0e0;border-radius:12px;margin-top:6px;overflow:hidden;display:none;box-shadow:0 4px 16px rgba(0,0,0,0.08)}
.sri{padding:12px 14px;border-bottom:1px solid #f5f5f5;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.sri:active{background:#f9f9f9}
.stats{display:grid;grid-template-columns:repeat(4,1fr);background:#fff;border-bottom:1px solid #f0f0f0}
.st{padding:12px 4px;text-align:center;cursor:pointer;border-right:1px solid #f5f5f5}
.st:last-child{border-right:none}.st:active{background:#f9f9f9}
.st-v{font-size:20px;font-weight:700}.st-l{font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:0.4px;margin-top:2px}
.chips-wrap{padding:8px 12px;background:#fff;border-bottom:1px solid #f0f0f0;overflow-x:auto;display:flex;gap:6px;-webkit-overflow-scrolling:touch}
.chips-wrap::-webkit-scrollbar{display:none}
.chip{border:1.5px solid #e8e8e8;border-radius:20px;padding:5px 12px;font-size:11px;font-weight:600;color:#888;white-space:nowrap;background:#fff;cursor:pointer;flex-shrink:0}
.chip.on{color:#fff!important;border-color:transparent!important;background:#1a73e8!important}
.sh{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;background:#f8f8f8;border-bottom:1px solid #f0f0f0}
.sh-t{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.6px}
.sh-a{font-size:12px;font-weight:600;color:#1a73e8;cursor:pointer}
.row{display:flex;justify-content:space-between;align-items:center;padding:13px 16px;border-bottom:1px solid #f5f5f5;background:#fff;cursor:pointer}
.row:active{background:#f9f9f9}
.row-l{display:flex;align-items:center;gap:10px}
.dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.tk{font-size:14px;font-weight:700}.nm{font-size:11px;color:#aaa;margin-top:1px}
.row-r{display:flex;align-items:center;gap:8px}
.pr{font-size:13px;font-weight:600;text-align:right}.ch{font-size:11px;text-align:right;margin-top:1px}
.bdg{padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;white-space:nowrap}
.arr{color:#ddd;font-size:14px;margin-left:2px}
.va-btn{margin:12px 16px 16px;border:1.5px solid #1a73e8;border-radius:12px;padding:12px;text-align:center;font-size:13px;font-weight:700;color:#1a73e8;cursor:pointer;background:#fff}
.nav{display:flex;align-items:center;gap:12px;padding:12px 16px;background:#fff;border-bottom:1px solid #f0f0f0;position:sticky;top:0;z-index:100}
.nav-back{background:#f5f5f5;border:none;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer}
.nav-title{font-size:15px;font-weight:700}.nav-sub{font-size:11px;color:#aaa;margin-top:1px}
.ash{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;background:#f8f8f8;border-bottom:1px solid #f0f0f0}
.ash-t{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.6px}
.ash-c{font-size:12px;font-weight:700;color:#1a73e8}
.det-hero{padding:18px 16px;background:#fff;border-bottom:1px solid #f0f0f0}
.det-p{font-size:30px;font-weight:700}.det-chg{font-size:14px;margin-top:3px}
.det-badge{display:inline-block;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:700;margin-top:10px}
.cks{display:flex;gap:6px;margin-top:12px}
.ck{border-radius:8px;padding:8px 10px;text-align:center;flex:1}
.ck-i{font-size:15px}.ck-l{font-size:9px;margin-top:3px}
.det-sec{padding:14px 16px;background:#fff;border-bottom:1px solid #f0f0f0}
.dst{font-size:10px;font-weight:700;color:#aaa;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:10px}
.dr{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f8f8f8;font-size:13px}
.dr:last-child{border-bottom:none}
.dl{color:#888}.dv{font-weight:600}.dg{font-weight:600;color:#00A65A}.dr2{font-weight:600;color:#E8333C}
.fb{background:#EEF3FF;border-radius:10px;padding:12px;margin-top:6px}
.fr{display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(44,94,232,0.08)}
.fr:last-child{border-bottom:none}
.fl{color:#4A6FE3}.fv{font-weight:600}
.hint{font-size:12px;color:#4A6FE3;margin-top:8px;line-height:1.5}
.sell-box{background:#FFF0F0;border-radius:10px;padding:12px;margin-top:6px}
.sb-row{display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(232,51,60,0.08)}
.sb-row:last-child{border-bottom:none}
.sl{color:#E8333C}.sv{font-weight:600}
.empty{text-align:center;padding:48px 24px;color:#aaa}
.empty-i{font-size:48px;margin-bottom:12px}
.empty-t{font-size:16px;font-weight:600;color:#888;margin-bottom:6px}
.empty-s{font-size:13px;line-height:1.7}
</style>
</head>
<body>
<div id="vHome">
  <div class="hd">
    <div class="hd-top">
      <div><span class="logo-t">TRADE</span><span class="logo-s">SCAN</span></div>
      <div class="hd-date">{{ scan_time }}</div>
    </div>
    <div class="btns">
      <form method="post" action="/scan" style="margin:0"><button class="b1" type="submit">&#9654; Vollscan ({{ total_tickers }})</button></form>
      <form method="post" action="/scan-wl" style="margin:0"><button class="b2" type="submit">&#9711; Watchlist ({{ wl_count }})</button></form>
    </div>
  </div>
  {% if scanning %}<div class="scan-banner">&#9889; Scan laeuft... Seite aktualisiert automatisch.</div>{% endif %}
  <div class="srch">
    <div class="srch-box">
      <span style="color:#ccc;font-size:14px">&#9906;</span>
      <input type="text" id="si" placeholder="Suchen... z.B. KO, Japan, Bayer" oninput="doSearch(this.value)" autocomplete="off">
    </div>
    <div class="sr-drop" id="sr"></div>
  </div>
  <div class="stats">
    <div class="st" onclick="openAll('KAUFEN')"><div class="st-v" style="color:#00A65A">{{ kaufen }}</div><div class="st-l">Kaufen</div></div>
    <div class="st" onclick="openAll('FAST')"><div class="st-v" style="color:#FF6200">{{ fast }}</div><div class="st-l">Fast</div></div>
    <div class="st" onclick="openAll('VERKAUFEN')"><div class="st-v" style="color:#E8333C">{{ verkaufen }}</div><div class="st-l">Verkaufen</div></div>
    <div class="st" onclick="openAll('ALLE')"><div class="st-v" style="color:#1a73e8">{{ total }}</div><div class="st-l">Alle &rarr;</div></div>
  </div>
  <div class="chips-wrap" id="regionChips">
    <div class="chip on" onclick="setChip(this);filterRegion('alle')">Alle</div>
    <div class="chip" onclick="setChip(this);filterRegion('DAX')">&#127465;&#127466; DAX</div>
    <div class="chip" onclick="setChip(this);filterRegion('UK')">&#127468;&#127463; UK</div>
    <div class="chip" onclick="setChip(this);filterRegion('US')">&#127482;&#127480; US</div>
    <div class="chip" onclick="setChip(this);filterRegion('EU')">&#127466;&#127482; EU</div>
    <div class="chip" onclick="setChip(this);filterRegion('Japan')">&#127471;&#127477; Japan</div>
    <div class="chip" onclick="setChip(this);filterRegion('Asien')">Asien</div>
    <div class="chip" onclick="setChip(this);filterRegion('Kanada')">&#127464;&#127462; Kanada</div>
  </div>
  {% if not data %}
  <div class="empty">
    <div class="empty-i">&#128202;</div>
    <div class="empty-t">Noch keine Daten</div>
    <div class="empty-s">Tippe auf Watchlist fuer einen schnellen Scan<br>(ca. 30 Sekunden fuer 15 Aktien)</div>
  </div>
  {% else %}
  <div id="homeList">
    {% for sig,lbl,dot in [('KAUFEN','Jetzt kaufen','#00A65A'),('FAST','Morgen pruefen','#FF6200'),('VERKAUFEN','Jetzt verkaufen','#E8333C')] %}
    {% set grp = data|selectattr('signal','equalto',sig)|list %}
    {% if grp %}
    <div class="sh"><span class="sh-t">{{ lbl }}</span><span class="sh-a" onclick="openAll('{{ sig }}')">Alle {{ grp|length }} &rarr;</span></div>
    {% for r in grp[:3] %}
    <div class="row" onclick="openDetail('{{ r.ticker }}')">
      <div class="row-l"><div class="dot" style="background:{{ dot }}"></div>
      <div><div class="tk">{{ r.ticker }}</div><div class="nm">{{ r.name }} &middot; {{ r.market }}</div></div></div>
      <div class="row-r">
      <div><div class="pr">{{ r.price_fmt }}</div>
      <div class="ch" style="color:{{'#00A65A' if r.change>=0 else '#E8333C'}}">{{ '+' if r.change>=0 else '' }}{{ r.change }}%</div></div>
      {% if sig=='KAUFEN' %}<span class="bdg" style="background:#E8F8F1;color:#00763D">Kaufen</span>
      {% elif sig=='FAST' %}<span class="bdg" style="background:#FFF3E8;color:#CC4E00">Fast</span>
      {% else %}<span class="bdg" style="background:#FFF0F0;color:#E8333C">Verkaufen</span>{% endif %}
      <span class="arr">&rsaquo;</span></div></div>
    {% endfor %}
    {% endif %}
    {% endfor %}
  </div>
  {% endif %}
  {% if data %}<div class="va-btn" onclick="openAll('ALLE')">Alle {{ total }} Aktien &rarr;</div>{% endif %}
</div>

<div id="vAll" style="display:none">
  <div class="nav">
    <button class="nav-back" onclick="show('vHome')">&#8249; Zurueck</button>
    <div><div class="nav-title" id="allTitle">Alle Aktien</div><div class="nav-sub" id="allSub"></div></div>
  </div>
  <div id="allList"></div>
</div>

<div id="vDetail" style="display:none">
  <div class="nav">
    <button class="nav-back" id="detBack">&#8249; Zurueck</button>
    <div><div class="nav-title" id="dTicker"></div><div class="nav-sub" id="dName"></div></div>
  </div>
  <div id="dContent"></div>
</div>

<script>
const ALL_DATA={{ data_json }};
const SIG={
  KAUFEN:{dot:'#00A65A',bg:'#E8F8F1',col:'#00763D',lbl:'Kaufen'},
  FAST:{dot:'#FF6200',bg:'#FFF3E8',col:'#CC4E00',lbl:'Fast'},
  BEOBACHTEN:{dot:'#4a90d9',bg:'#EEF5FF',col:'#1a5fb4',lbl:'Watch'},
  VERKAUFEN:{dot:'#E8333C',bg:'#FFF0F0',col:'#E8333C',lbl:'Verkaufen'},
  NEUTRAL:{dot:'#ccc',bg:'#F5F5F5',col:'#888',lbl:'Abwarten'}
};
const SEC={KAUFEN:'Jetzt kaufen',FAST:'Morgen pruefen',BEOBACHTEN:'Beobachten',VERKAUFEN:'Jetzt verkaufen',NEUTRAL:'Abwarten'};
let prevView='vHome';
function show(id){['vHome','vAll','vDetail'].forEach(v=>document.getElementById(v).style.display=v===id?'block':'none');window.scrollTo(0,0);}
function rowHTML(s){const c=SIG[s.signal]||SIG.NEUTRAL;const cc=s.change>=0?'#00A65A':'#E8333C';
  return `<div class="row" onclick="openDetail('${s.ticker}')">
  <div class="row-l"><div class="dot" style="background:${c.dot}"></div>
  <div><div class="tk">${s.ticker}</div><div class="nm">${s.name} &middot; ${s.market}</div></div></div>
  <div class="row-r"><div><div class="pr">${s.price_fmt}</div><div class="ch" style="color:${cc}">${(s.change>=0?'+':'')+s.change}%</div></div>
  <span class="bdg" style="background:${c.bg};color:${c.col}">${c.lbl}</span><span class="arr">&rsaquo;</span></div></div>`;}
function openAll(filter){
  show('vAll');prevView='vAll';
  const t={ALLE:'Alle Aktien',KAUFEN:'Kaufsignale',FAST:'Morgen pruefen',VERKAUFEN:'Verkaufssignale'};
  document.getElementById('allTitle').textContent=t[filter]||filter;
  let data=filter==='ALLE'?ALL_DATA:ALL_DATA.filter(s=>s.signal===filter);
  document.getElementById('allSub').textContent=data.length+' Werte';
  const g={KAUFEN:[],FAST:[],BEOBACHTEN:[],VERKAUFEN:[],NEUTRAL:[]};
  data.forEach(s=>(g[s.signal]||g.NEUTRAL).push(s));
  let html='';
  for(const k of ['KAUFEN','FAST','BEOBACHTEN','VERKAUFEN','NEUTRAL']){
    if(!g[k].length)continue;
    html+=`<div class="ash"><span class="ash-t">${SEC[k]}</span><span class="ash-c">${g[k].length}</span></div>`;
    g[k].forEach(s=>{html+=rowHTML(s);});
  }
  if(!html)html='<div class="empty"><div class="empty-i">&#128269;</div><div class="empty-t">Keine Daten</div></div>';
  document.getElementById('allList').innerHTML=html;
}
function filterRegion(r){
  let data=r==='alle'?ALL_DATA:ALL_DATA.filter(s=>s.market===r);
  const sigs=[['KAUFEN','Jetzt kaufen','#00A65A'],['FAST','Morgen pruefen','#FF6200'],['VERKAUFEN','Jetzt verkaufen','#E8333C']];
  let html='';
  for(const [sig,lbl,dot] of sigs){
    const grp=data.filter(s=>s.signal===sig);if(!grp.length)continue;
    const c=SIG[sig];
    html+=`<div class="sh"><span class="sh-t">${lbl}</span><span class="sh-a" onclick="openAll('${sig}')">Alle ${grp.length} &rarr;</span></div>`;
    grp.slice(0,3).forEach(s=>{const cc=s.change>=0?'#00A65A':'#E8333C';
      html+=`<div class="row" onclick="openDetail('${s.ticker}')">
      <div class="row-l"><div class="dot" style="background:${dot}"></div>
      <div><div class="tk">${s.ticker}</div><div class="nm">${s.name} &middot; ${s.market}</div></div></div>
      <div class="row-r"><div><div class="pr">${s.price_fmt}</div><div class="ch" style="color:${cc}">${(s.change>=0?'+':'')+s.change}%</div></div>
      <span class="bdg" style="background:${c.bg};color:${c.col}">${c.lbl}</span><span class="arr">&rsaquo;</span></div></div>`;});
  }
  if(!html)html='<div style="text-align:center;padding:24px;color:#aaa;font-size:13px">Keine Signale</div>';
  const list=document.getElementById('homeList');if(list)list.innerHTML=html;
}
function setChip(el){document.querySelectorAll('#regionChips .chip').forEach(c=>c.classList.remove('on'));el.classList.add('on');}
function openDetail(ticker){
  const s=ALL_DATA.find(x=>x.ticker===ticker);if(!s)return;
  document.getElementById('detBack').onclick=()=>show(prevView);
  show('vDetail');
  document.getElementById('dTicker').textContent=s.ticker;
  document.getElementById('dName').textContent=s.name+' - '+s.market;
  const c=SIG[s.signal]||SIG.NEUTRAL;
  const cc=s.change>=0?'#00A65A':'#E8333C';
  const ck=(ok,lbl)=>`<div class="ck" style="background:${ok?'#E8F8F1':'#F5F5F5'}">
    <div class="ck-i" style="color:${ok?'#00A65A':'#ccc'}">${ok?'&#10003;':'&#10007;'}</div>
    <div class="ck-l" style="color:${ok?'#00A65A':'#bbb'}">${lbl}</div></div>`;
  let action='';
  if(s.signal==='KAUFEN'){
    action=`<div class="det-sec"><div class="dst">Trade-Details</div>
    <div class="dr"><span class="dl">Kaufen bei</span><span class="dv">${s.price_fmt}</span></div>
    <div class="dr"><span class="dl">Stop-Loss (8%)</span><span class="dr2">${s.stop_fix} (-8%)</span></div>
    <div class="dr"><span class="dl">Stop-Loss (ATR 2x)</span><span class="dr2">${s.stop_atr} (-${s.stop_atr_pct}%)</span></div>
    <div class="dr"><span class="dl">Ziel 1 - MA20</span><span class="dg">${s.target1} (+${s.pot1}%)</span></div>
    <div class="dr"><span class="dl">Ziel 2 - ob. BB</span><span class="dg">${s.target2} (+${s.pot2}%)</span></div>
    <div class="dr"><span class="dl">Haltedauer</span><span class="dv">2-6 Wochen</span></div>
    <div class="dr"><span class="dl">Max. Position</span><span class="dv">10% des Kapitals</span></div></div>
    <div class="det-sec"><div class="dst">Indikatoren</div>
    <div class="dr"><span class="dl">RSI (14)</span><span class="dg">${s.rsi} - ueberverkauft</span></div>
    <div class="dr"><span class="dl">MA200</span><span class="dv">${s.ma200}</span></div>
    <div class="dr"><span class="dl">52W-Position</span><span class="dv">${s.pos52}%</span></div>
    <div class="dr"><span class="dl">ATR</span><span class="dv">${s.atr} (${s.atr_pct}%)</span></div></div>`;
  } else if(s.signal==='FAST'){
    const miss=s.missing.map(m=>`<div class="hint">&rarr; ${m}</div>`).join('');
    action=`<div class="det-sec"><div class="dst">Zukuenftiger Einstieg</div>
    <div class="fb">
    <div class="fr"><span class="fl">Moeglicher Einstieg</span><span class="fv">${s.fut_entry}</span></div>
    <div class="fr"><span class="fl">Stop-Loss dann</span><span class="fv" style="color:#E8333C">${s.fut_stop} (-8%)</span></div>
    <div class="fr"><span class="fl">Ziel 1 - MA20</span><span class="fv" style="color:#00A65A">${s.target1} (+${s.pot1}%)</span></div>
    <div class="fr"><span class="fl">Ziel 2 - ob. BB</span><span class="fv" style="color:#00A65A">${s.target2} (+${s.pot2}%)</span></div></div>
    <div style="margin-top:10px">${miss}</div></div>`;
  } else if(s.signal==='VERKAUFEN'){
    action=`<div class="det-sec"><div class="dst">Verkauf-Signal</div>
    <div class="sell-box">
    <div class="sb-row"><span class="sl">RSI (ueberkauft)</span><span class="sv">${s.rsi}</span></div>
    <div class="sb-row"><span class="sl">Empfehlung</span><span class="sv">Position schliessen!</span></div></div></div>`;
  } else {
    const miss=s.missing.map(m=>`<div class="hint">&rarr; ${m}</div>`).join('');
    action=`<div class="det-sec"><div class="dst">Naechster Einstieg</div>
    <div class="fb">
    <div class="fr"><span class="fl">Einstieg bei</span><span class="fv">${s.fut_entry}</span></div>
    <div class="fr"><span class="fl">Stop-Loss</span><span class="fv" style="color:#E8333C">${s.fut_stop}</span></div></div>
    <div style="margin-top:10px">${miss}</div></div>`;
  }
  document.getElementById('dContent').innerHTML=`
  <div class="det-hero">
    <div class="det-p">${s.price_fmt}</div>
    <div class="det-chg" style="color:${cc}">${(s.change>=0?'+':'')+s.change}% heute</div>
    <span class="det-badge" style="background:${c.bg};color:${c.col}">${c.lbl}</span>
    <div class="cks">${ck(s.cond_bb,'BB-Umkehr')}${ck(s.cond_rsi,'RSI '+s.rsi)}${ck(s.cond_trend,'Trend hoch')}</div>
  </div>${action}`;
}
function doSearch(v){
  const r=document.getElementById('sr');
  if(!v||v.length<2){r.style.display='none';return;}
  const m=ALL_DATA.filter(s=>s.ticker.toLowerCase().includes(v.toLowerCase())||s.name.toLowerCase().includes(v.toLowerCase())||s.market.toLowerCase().includes(v.toLowerCase())).slice(0,6);
  if(!m.length){r.style.display='none';return;}
  r.innerHTML=m.map(s=>{const c=SIG[s.signal]||SIG.NEUTRAL;
    return `<div class="sri" onclick="openDetail('${s.ticker}');document.getElementById('si').value='';document.getElementById('sr').style.display='none'">
    <div><div style="font-size:13px;font-weight:700">${s.ticker}</div><div style="font-size:11px;color:#aaa">${s.name} - ${s.market}</div></div>
    <span class="bdg" style="background:${c.bg};color:${c.col}">${c.lbl}</span></div>`;
  }).join('');
  r.style.display='block';
}
document.addEventListener('click',e=>{if(!e.target.closest('.srch'))document.getElementById('sr').style.display='none';});
</script>
</body>
</html>"""

@app.route("/")
def index():
    data=CACHE["data"]
    now=CACHE["time"]
    data_json=json.dumps(data,ensure_ascii=False)
    return render_template_string(TEMPLATE,
        data=data,data_json=data_json,
        kaufen=sum(1 for r in data if r["signal"]=="KAUFEN"),
        fast=sum(1 for r in data if r["signal"]=="FAST"),
        verkaufen=sum(1 for r in data if r["signal"]=="VERKAUFEN"),
        total=len(data),total_tickers=len(TICKERS),wl_count=len(WATCHLIST),
        scan_time=now.strftime("Stand: %d.%m.%Y %H:%M Uhr") if now else "Noch kein Scan",
        scanning=CACHE.get("scanning",False),
    )

@app.route("/scan",methods=["POST"])
def scan_all():
    if not CACHE.get("scanning"):
        CACHE["scanning"]=True
        threading.Thread(target=do_scan,args=(TICKERS,),daemon=True).start()
    return redirect("/?scanning=1")

@app.route("/scan-wl",methods=["POST"])
def scan_wl():
    if not CACHE.get("scanning"):
        CACHE["scanning"]=True
        threading.Thread(target=do_scan,args=(WATCHLIST,),daemon=True).start()
    return redirect("/?scanning=1")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    import pytz
    scheduler=BackgroundScheduler(timezone=pytz.timezone("Europe/Berlin"))
    scheduler.add_job(lambda:do_scan(TICKERS) if not CACHE.get("scanning") else None,"cron",hour=9,minute=0)
    scheduler.add_job(lambda:do_scan(TICKERS) if not CACHE.get("scanning") else None,"cron",hour=12,minute=30)
    scheduler.add_job(lambda:do_scan(TICKERS) if not CACHE.get("scanning") else None,"cron",hour=16,minute=30)
    scheduler.add_job(lambda:do_scan(TICKERS) if not CACHE.get("scanning") else None,"cron",hour=20,minute=0)
    scheduler.start()
    print("Scheduler: 09:00 | 12:30 | 16:30 | 20:00 Uhr",flush=True)
except Exception as e:
    print(f"Scheduler Fehler: {e}",flush=True)

if __name__=="__main__":
    port=int(os.environ.get("PORT",80))
    app.run(host="0.0.0.0",port=port,debug=False)
