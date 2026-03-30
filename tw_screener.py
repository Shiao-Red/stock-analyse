"""
台股巴菲特評分篩選器
每日自動抓取 TWSE 所有上市股票，依巴菲特8大標準評分並排名前100名
"""
import requests
import yfinance as yf
import pandas as pd
import json
import os
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "tw_top100.json")
CACHE_MAX_AGE_HOURS = 24
MAX_CANDIDATES = 50    # 雲端環境減少候選數量（原本200）
MAX_WORKERS = 3        # 雲端環境減少並行數（原本8）

_refresh_lock = threading.Lock()
_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "message": "閒置中",
    "started_at": None,
}


# ── Scoring logic (same weights as main app) ──────────────────────────

def safe_val(val, default=None):
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except Exception:
        pass
    return val


def score_stock(info: dict):
    """Return (total_score, breakdown_dict)"""
    breakdown = {}
    total = 0

    # 1. ROE (20 pts)
    roe = safe_val(info.get("returnOnEquity"))
    if roe is not None:
        rp = roe * 100
        pts = 20 if rp >= 15 else (14 if rp >= 10 else (7 if rp >= 5 else 0))
        breakdown["ROE"] = {"value": round(rp, 1), "score": pts, "max": 20,
                            "label": f"{round(rp,1)}%", "pass": rp >= 10}
        total += pts
    else:
        breakdown["ROE"] = {"value": None, "score": 0, "max": 20, "label": "N/A", "pass": False}

    # 2. Gross Margin (15 pts)
    gm = safe_val(info.get("grossMargins"))
    if gm is not None:
        gp = gm * 100
        pts = 15 if gp >= 50 else (11 if gp >= 40 else (6 if gp >= 25 else 0))
        breakdown["毛利率"] = {"value": round(gp, 1), "score": pts, "max": 15,
                               "label": f"{round(gp,1)}%", "pass": gp >= 40}
        total += pts
    else:
        breakdown["毛利率"] = {"value": None, "score": 0, "max": 15, "label": "N/A", "pass": False}

    # 3. Debt/Equity (15 pts)
    de = safe_val(info.get("debtToEquity"))
    if de is not None:
        pts = 15 if de <= 30 else (10 if de <= 80 else (5 if de <= 150 else 0))
        breakdown["負債股東權益比"] = {"value": round(de, 1), "score": pts, "max": 15,
                                      "label": f"{round(de,1)}%", "pass": de <= 80}
        total += pts
    else:
        breakdown["負債股東權益比"] = {"value": None, "score": 0, "max": 15, "label": "N/A", "pass": False}

    # 4. P/E (15 pts)
    pe = safe_val(info.get("trailingPE"))
    if pe is not None and pe > 0:
        pts = 15 if 10 <= pe <= 15 else (10 if pe <= 25 else (8 if pe < 10 else (4 if pe <= 35 else 0)))
        breakdown["本益比(P/E)"] = {"value": round(pe, 1), "score": pts, "max": 15,
                                    "label": f"{round(pe,1)}x", "pass": pe <= 25}
        total += pts
    else:
        breakdown["本益比(P/E)"] = {"value": None, "score": 0, "max": 15, "label": "N/A", "pass": False}

    # 5. Free Cash Flow (10 pts)
    fcf = safe_val(info.get("freeCashflow"))
    if fcf is not None:
        pts = 10 if fcf > 1e9 else (6 if fcf > 0 else 0)
        breakdown["自由現金流"] = {"value": round(fcf/1e9, 2), "score": pts, "max": 10,
                                   "label": f"${round(fcf/1e9,2)}B", "pass": fcf > 0}
        total += pts
    else:
        breakdown["自由現金流"] = {"value": None, "score": 0, "max": 10, "label": "N/A", "pass": False}

    # 6. Operating Margin (10 pts)
    om = safe_val(info.get("operatingMargins"))
    if om is not None:
        op = om * 100
        pts = 10 if op >= 20 else (7 if op >= 15 else (4 if op >= 8 else 0))
        breakdown["營業利益率"] = {"value": round(op, 1), "score": pts, "max": 10,
                                   "label": f"{round(op,1)}%", "pass": op >= 15}
        total += pts
    else:
        breakdown["營業利益率"] = {"value": None, "score": 0, "max": 10, "label": "N/A", "pass": False}

    # 7. Market Cap (5 pts)
    mc = safe_val(info.get("marketCap"))
    if mc is not None:
        pts = 5 if mc >= 1e11 else (3 if mc >= 1e9 else 0)
        breakdown["市值"] = {"value": round(mc/1e9, 1), "score": pts, "max": 5,
                             "label": f"${round(mc/1e9,1)}B", "pass": mc >= 1e9}
        total += pts
    else:
        breakdown["市值"] = {"value": None, "score": 0, "max": 5, "label": "N/A", "pass": False}

    # 8. Dividend Yield (10 pts)
    dy = safe_val(info.get("dividendYield"))
    if dy is not None and dy > 0:
        dp = dy * 100
        pts = 10 if dp >= 2 else (6 if dp >= 1 else 3)
        breakdown["股息殖利率"] = {"value": round(dp, 2), "score": pts, "max": 10,
                                   "label": f"{round(dp,2)}%", "pass": dp >= 1}
        total += pts
    else:
        breakdown["股息殖利率"] = {"value": 0, "score": 0, "max": 10, "label": "0%", "pass": False}

    return min(total, 100), breakdown


def grade_from_score(score):
    if score >= 80:
        return "A", "強力買進", "#00c853"
    elif score >= 65:
        return "B", "值得關注", "#64dd17"
    elif score >= 50:
        return "C", "謹慎評估", "#ffd600"
    elif score >= 35:
        return "D", "風險偏高", "#ff6d00"
    else:
        return "F", "不符標準", "#d50000"


def calculate_buffett_valuation(info: dict, current_price: float):
    """
    巴菲特式內在價值計算（台股版）
    混合方法：EPS × 品質調整P/E + 葛拉漢公式
    """
    eps = safe_val(info.get("trailingEps"))
    if not eps or eps <= 0:
        return None

    roe = safe_val(info.get("returnOnEquity"), 0) or 0
    growth = safe_val(info.get("earningsGrowth")) or safe_val(info.get("revenueGrowth")) or 0.05
    growth = max(min(float(growth), 0.25), -0.05)

    roe_pct = roe * 100
    if roe_pct >= 25:
        base_pe = 22
    elif roe_pct >= 20:
        base_pe = 20
    elif roe_pct >= 15:
        base_pe = 17
    elif roe_pct >= 10:
        base_pe = 15
    else:
        base_pe = 12

    growth_bonus = (growth * 100 - 5) * 0.5 if growth * 100 > 5 else 0
    fair_pe = max(8.0, min(30.0, base_pe + growth_bonus))

    fair_value_pe = eps * fair_pe
    g_pct = growth * 100
    risk_free = 4.5
    graham_value = eps * (8.5 + 2 * g_pct) * 4.4 / risk_free
    graham_value = max(graham_value, eps * 6)

    fair_value = fair_value_pe * 0.6 + graham_value * 0.4

    buy_strong  = round(fair_value * 0.70, 1)
    buy_zone    = round(fair_value * 0.85, 1)
    fair_value  = round(fair_value, 1)
    sell_zone   = round(fair_value * 1.20, 1)
    sell_strong = round(fair_value * 1.40, 1)

    signal, signal_color, price_to_fair = "無法判斷", "#94a3b8", None
    if current_price and current_price > 0:
        ratio = current_price / fair_value
        price_to_fair = round(ratio * 100, 1)
        if ratio < 0.70:
            signal, signal_color = "強力買入", "#00c853"
        elif ratio < 0.85:
            signal, signal_color = "買入區間", "#64dd17"
        elif ratio < 1.20:
            signal, signal_color = "合理持有", "#ffd600"
        elif ratio < 1.40:
            signal, signal_color = "考慮賣出", "#ff6d00"
        else:
            signal, signal_color = "強力賣出", "#d50000"

    return {
        "eps": round(eps, 2),
        "fair_pe": round(fair_pe, 1),
        "growth_rate": round(growth * 100, 1),
        "fair_value": fair_value,
        "buy_strong": buy_strong,
        "buy_zone": buy_zone,
        "sell_zone": sell_zone,
        "sell_strong": sell_strong,
        "price_to_fair": price_to_fair,
        "signal": signal,
        "signal_color": signal_color,
    }


# ── Data fetching ─────────────────────────────────────────────────────

def fetch_twse_base():
    """Fetch all TWSE listed stocks with trading value for pre-filtering."""
    stocks = {}
    try:
        r = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=20, headers={"User-Agent": "Mozilla/5.0"}
        )
        for item in r.json():
            code = item.get("Code", "")
            if len(code) == 4 and code.isdigit() and code[0] != "0":
                try:
                    tv = float(item.get("TradeValue", "0").replace(",", "") or 0)
                    price = float(item.get("ClosingPrice", "0").replace(",", "") or 0)
                except ValueError:
                    tv, price = 0, 0
                stocks[code] = {
                    "code": code,
                    "name": item.get("Name", code),
                    "trade_value": tv,
                    "close_price": price,
                }
    except Exception as e:
        print(f"[tw_screener] STOCK_DAY_ALL error: {e}")

    # Merge P/E, P/B, dividend yield from BWIBBU
    try:
        r2 = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
            timeout=20, headers={"User-Agent": "Mozilla/5.0"}
        )
        for item in r2.json():
            code = item.get("Code", "")
            if code in stocks:
                def _f(v):
                    try:
                        return float(v) if v else None
                    except Exception:
                        return None
                stocks[code]["twse_pe"] = _f(item.get("PEratio", ""))
                stocks[code]["twse_pb"] = _f(item.get("PBratio", ""))
                stocks[code]["twse_dy"] = _f(item.get("DividendYield", ""))
    except Exception as e:
        print(f"[tw_screener] BWIBBU_ALL error: {e}")

    return list(stocks.values())


def fetch_single_stock(stock: dict):
    """Fetch yfinance info and score one stock. Returns result dict or None."""
    ticker_sym = f"{stock['code']}.TW"
    try:
        t = yf.Ticker(ticker_sym)
        info = t.info
        price = safe_val(info.get("currentPrice")) or safe_val(info.get("regularMarketPrice"))
        if price is None:
            return None

        score, breakdown = score_stock(info)
        grade, grade_label, grade_color = grade_from_score(score)

        prev_close = safe_val(info.get("previousClose"))
        change_pct = None
        if price and prev_close:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        mc = safe_val(info.get("marketCap"))
        roe = safe_val(info.get("returnOnEquity"))
        pe = safe_val(info.get("trailingPE"))
        pb = safe_val(info.get("priceToBook"))
        gm = safe_val(info.get("grossMargins"))
        de = safe_val(info.get("debtToEquity"))

        # dividendYield: yfinance should return as decimal (0.03 = 3%).
        # For TW stocks, occasionally returns bad data; cap at 0.30 (30%) as sanity check.
        dy_raw = safe_val(info.get("dividendYield"))
        if dy_raw is not None and 0 < dy_raw <= 0.30:
            div_yield_pct = round(dy_raw * 100, 2)
        else:
            # Fallback to TWSE official dividend yield (already in %)
            twse_dy = stock.get("twse_dy")
            div_yield_pct = round(float(twse_dy), 2) if twse_dy else None

        price_float = round(float(price), 2)
        valuation = calculate_buffett_valuation(info, price_float)

        return {
            "ticker": ticker_sym,
            "code": stock["code"],
            "name": stock.get("name") or info.get("longName") or info.get("shortName") or stock["code"],
            "long_name": info.get("longName") or info.get("shortName") or stock.get("name", ""),
            "price": price_float,
            "currency": info.get("currency", "TWD"),
            "change_pct": change_pct,
            "sector": info.get("sector") or "未知",
            "industry": info.get("industry") or "未知",
            "market_cap": round(mc / 1e8, 1) if mc else None,
            "buffett_score": score,
            "grade": grade,
            "grade_label": grade_label,
            "grade_color": grade_color,
            "pe": round(pe, 1) if pe and pe > 0 else stock.get("twse_pe"),
            "pb": round(pb, 2) if pb else stock.get("twse_pb"),
            "roe": round(roe * 100, 1) if roe else None,
            "div_yield": div_yield_pct,
            "gross_margin": round(gm * 100, 1) if gm else None,
            "debt_equity": round(de, 1) if de else None,
            "breakdown": breakdown,
            "valuation": valuation,
        }
    except Exception as e:
        print(f"[tw_screener] {ticker_sym} error: {e}")
        return None


def run_screening():
    """Main screening job. Returns list of top-100 results."""
    global _status

    try:
        _status.update({"running": True, "progress": 0, "total": 0,
                        "message": "正在取得台股清單...", "started_at": datetime.now().isoformat()})

        print("[tw_screener] Starting screening process...")

        # Step 1: Get all TWSE stocks
        all_stocks = fetch_twse_base()
        if not all_stocks:
            _status.update({"running": False, "message": "無法取得台股清單"})
            print("[tw_screener] Failed to fetch TWSE stock list")
            return []

        print(f"[tw_screener] Fetched {len(all_stocks)} stocks from TWSE")

        # Step 2: Pre-filter — top MAX_CANDIDATES by daily trade value (liquid, large)
        all_stocks.sort(key=lambda s: s.get("trade_value", 0), reverse=True)
        candidates = all_stocks[:MAX_CANDIDATES]

        _status.update({"total": len(candidates), "message": f"開始評分 {len(candidates)} 檔候選股..."})
        print(f"[tw_screener] Screening {len(candidates)} candidates...")

        # Step 3: Parallel yfinance fetch + score
        results = []
        done = 0

        def worker(stock):
            nonlocal done
            res = fetch_single_stock(stock)
            done += 1
            _status["progress"] = done
            _status["message"] = f"評分中... ({done}/{len(candidates)}) {stock['code']} {stock.get('name','')}"
            if done % 10 == 0:  # Log every 10 stocks
                print(f"[tw_screener] Progress: {done}/{len(candidates)}")
            return res

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(worker, s): s for s in candidates}
            for future in as_completed(futures):
                try:
                    res = future.result(timeout=30)  # 30 second timeout per stock
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"[tw_screener] Worker error: {e}")
                    continue

        print(f"[tw_screener] Successfully scored {len(results)} stocks")

        # Step 4: Sort by score, return top 100
        results.sort(key=lambda x: x["buffett_score"], reverse=True)
        top100 = results[:100]

        # Add rank
        for i, r in enumerate(top100, 1):
            r["rank"] = i

        _status.update({"running": False, "progress": len(candidates), "message": "評分完成"})
        print(f"[tw_screener] Screening completed. Top 100 selected.")
        return top100

    except Exception as e:
        print(f"[tw_screener] Fatal error in run_screening: {e}")
        import traceback
        traceback.print_exc()
        _status.update({"running": False, "message": f"評分失敗：{str(e)}"})
        return []


# ── Cache management ─────────────────────────────────────────────────

def _save_cache(data: list):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        payload = {
            "timestamp": datetime.now().isoformat(),
            "count": len(data),
            "data": data,
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[tw_screener] Cache saved: {len(data)} stocks")
    except Exception as e:
        print(f"[tw_screener] Failed to save cache: {e}")


def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _cache_is_fresh(cache: dict) -> bool:
    try:
        ts = datetime.fromisoformat(cache["timestamp"])
        age_hours = (datetime.now() - ts).total_seconds() / 3600
        return age_hours < CACHE_MAX_AGE_HOURS
    except Exception:
        return False


def get_status():
    return dict(_status)


def start_refresh_background():
    """Start a background refresh thread (only one at a time)."""
    global _status
    with _refresh_lock:
        if _status["running"]:
            return False  # Already running
        _status["running"] = True

    def _job():
        try:
            data = run_screening()
            if data:
                _save_cache(data)
        except Exception as e:
            _status.update({"running": False, "message": f"錯誤: {e}"})

    t = threading.Thread(target=_job, daemon=True)
    t.start()
    return True


def get_top100(trigger_refresh_if_stale=True):
    """
    Return cached top-100 data.
    If cache is missing, run synchronously (blocking).
    If cache is stale, trigger background refresh and return stale data.
    """
    cache = _load_cache()

    if cache is None:
        # First run — must wait
        _status.update({"message": "首次執行，正在建立評分資料庫..."})
        data = run_screening()
        if data:
            _save_cache(data)
        return data, True  # data, is_fresh

    if _cache_is_fresh(cache):
        return cache["data"], True

    # Stale cache — return old data and kick off background refresh
    if trigger_refresh_if_stale:
        start_refresh_background()
    return cache["data"], False
