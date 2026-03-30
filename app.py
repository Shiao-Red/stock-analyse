from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
import traceback
import tw_screener
import time

app = Flask(__name__)

# Configure yfinance to be more reliable
yf.pdr_override()


def get_ticker_info_safe(ticker: str, max_retries=3):
    """Safely get ticker info with retries"""
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Validate info
            if not info or not isinstance(info, dict):
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None, None

            return stock, info
        except Exception as e:
            print(f"[get_ticker_info_safe] Attempt {attempt + 1} failed for {ticker}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                return None, None
    return None, None


def safe_val(val, default=None):
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except Exception:
        pass
    return val


def score_stock(info, _hist=None):
    """Calculate 0-100 Buffett Score. Returns (total_score, breakdown_dict)."""
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
        fcf_b = round(fcf / 1e9, 2)
        breakdown["自由現金流"] = {"value": fcf_b, "score": pts, "max": 10,
                                   "label": f"${fcf_b}B", "pass": fcf > 0}
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
        breakdown["市值"] = {"value": round(mc / 1e9, 1), "score": pts, "max": 5,
                             "label": f"${round(mc/1e9,1)}B", "pass": mc >= 1e9}
        total += pts
    else:
        breakdown["市值"] = {"value": None, "score": 0, "max": 5, "label": "N/A", "pass": False}

    # 8. Dividend Yield (10 pts)
    dy = safe_val(info.get("dividendYield"))
    if dy is not None and 0 < dy <= 0.30:
        dp = dy * 100
        pts = 10 if dp >= 2 else (6 if dp >= 1 else 3)
        breakdown["股息殖利率"] = {"value": round(dp, 2), "score": pts, "max": 10,
                                   "label": f"{round(dp,2)}%", "pass": dp >= 1}
        total += pts
    else:
        breakdown["股息殖利率"] = {"value": 0, "score": 0, "max": 10, "label": "0%", "pass": False}

    return min(total, 100), breakdown


def calculate_buffett_valuation(info: dict, current_price: float):
    """
    計算巴菲特式內在價值與買賣區間。
    方法：EPS × 品質調整後合理P/E（以ROE定品質等級）
          與 葛拉漢公式（V* = EPS × (8.5 + 2g) × 4.4 / Y）混合使用
    買入：低於合理價30%（安全邊際）
    賣出：高於合理價20~40%
    """
    eps = safe_val(info.get("trailingEps"))
    if not eps or eps <= 0:
        return None

    roe = safe_val(info.get("returnOnEquity"), 0) or 0
    # Growth: use earningsGrowth, fall back to revenueGrowth, default 5%
    growth = safe_val(info.get("earningsGrowth")) or safe_val(info.get("revenueGrowth")) or 0.05
    growth = max(min(float(growth), 0.25), -0.05)  # cap -5% ~ +25%

    # Quality-based fair P/E (Buffett: great business deserves higher multiple)
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

    # Growth adjustment: each 1% of growth above 5% adds ~0.5 to fair P/E
    growth_bonus = (growth * 100 - 5) * 0.5 if growth * 100 > 5 else 0
    fair_pe = max(8.0, min(30.0, base_pe + growth_bonus))

    # Method 1: EPS × Fair P/E
    fair_value_pe = eps * fair_pe

    # Method 2: Graham Formula  V* = EPS × (8.5 + 2g) × 4.4 / Y
    g_pct = growth * 100
    risk_free = 4.5  # approximate current risk-free rate
    graham_value = eps * (8.5 + 2 * g_pct) * 4.4 / risk_free
    graham_value = max(graham_value, eps * 6)  # sanity floor

    # Blend: 60% EPS-based + 40% Graham
    fair_value = fair_value_pe * 0.6 + graham_value * 0.4

    # Price zones
    buy_strong = round(fair_value * 0.70, 1)   # 強力買入上限 (≥30% MOS)
    buy_zone   = round(fair_value * 0.85, 1)   # 買入區間上限 (≥15% MOS)
    fair_value = round(fair_value, 1)
    sell_zone  = round(fair_value * 1.20, 1)   # 賣出區間下限 (+20%)
    sell_strong = round(fair_value * 1.40, 1)  # 強力賣出下限 (+40%)

    # Current price signal
    signal, signal_color = "無法判斷", "#94a3b8"
    price_to_fair = None
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


def get_stock_analysis(ticker: str):
    try:
        print(f"[Analysis] Starting analysis for: {ticker}")

        # Use safe getter with retries
        stock, info = get_ticker_info_safe(ticker)

        if not stock or not info:
            print(f"[Analysis] Failed to get data for {ticker}")
            return {"error": f"無法獲取 '{ticker}' 的資料。請確認：\n• 台股代號需加 .TW（例：2330.TW）\n• 美股直接輸入代號（例：AAPL）\n• 代號是否正確"}

        # Check if info is valid
        if len(info) < 5:
            print(f"[Analysis] Insufficient data for {ticker}")
            return {"error": f"'{ticker}' 資料不完整，可能已下市或代號錯誤"}

        if not info.get("regularMarketPrice") and not info.get("currentPrice"):
            print(f"[Analysis] No price data for {ticker}")
            return {"error": f"'{ticker}' 無價格資料，可能已停牌或下市"}

        name = info.get("longName") or info.get("shortName") or ticker
        print(f"[Analysis] Successfully got data for: {name}")
        price = safe_val(info.get("currentPrice")) or safe_val(info.get("regularMarketPrice"))
        currency = info.get("currency", "USD")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        description = info.get("longBusinessSummary", "")[:300] + "..." if info.get("longBusinessSummary") else ""
        country = info.get("country", "N/A")
        exchange = info.get("exchange", "N/A")

        prev_close = safe_val(info.get("previousClose"))
        change_pct = None
        if price and prev_close:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        try:
            hist = stock.history(period="3mo")
            if not hist.empty:
                price_history = [round(float(v), 2) for v in hist["Close"].tolist()]
                dates_history = [d.strftime("%Y-%m-%d") for d in hist.index.tolist()]
            else:
                price_history, dates_history = [], []
        except Exception:
            price_history, dates_history = [], []

        try:
            financials = stock.financials
            earnings_data = []
            if financials is not None and not financials.empty:
                for idx in financials.index:
                    if "Net Income" in str(idx):
                        row = financials.loc[idx]
                        earnings_data = sorted(
                            [(str(col.year), round(float(val) / 1e9, 2))
                             for col, val in row.items() if pd.notna(val)],
                            key=lambda x: x[0]
                        )
                        break
        except Exception:
            earnings_data = []

        buffett_score, breakdown = score_stock(info)

        if buffett_score >= 80:
            grade, grade_label, grade_color = "A", "強力買進", "#00c853"
        elif buffett_score >= 65:
            grade, grade_label, grade_color = "B", "值得關注", "#64dd17"
        elif buffett_score >= 50:
            grade, grade_label, grade_color = "C", "謹慎評估", "#ffd600"
        elif buffett_score >= 35:
            grade, grade_label, grade_color = "D", "風險偏高", "#ff6d00"
        else:
            grade, grade_label, grade_color = "F", "不符標準", "#d50000"

        moat_signals = []
        gm = safe_val(info.get("grossMargins"), 0)
        if gm and gm > 0.4:
            moat_signals.append("高毛利率 → 定價能力強")
        roe = safe_val(info.get("returnOnEquity"), 0)
        if roe and roe > 0.15:
            moat_signals.append("高ROE → 競爭優勢顯著")
        de = safe_val(info.get("debtToEquity"), 999)
        if de and de < 50:
            moat_signals.append("低負債 → 財務體質穩健")
        fcf = safe_val(info.get("freeCashflow"), 0)
        if fcf and fcf > 0:
            moat_signals.append("正自由現金流 → 不依賴外部融資")
        dy = safe_val(info.get("dividendYield"), 0)
        if dy and 0 < dy <= 0.30 and dy > 0.01:
            moat_signals.append("穩定股息 → 股東回報有保障")

        valuation = calculate_buffett_valuation(info, price)

        return {
            "ticker": ticker.upper(),
            "name": name,
            "price": price,
            "currency": currency,
            "change_pct": change_pct,
            "sector": sector,
            "industry": industry,
            "country": country,
            "exchange": exchange,
            "description": description,
            "buffett_score": buffett_score,
            "grade": grade,
            "grade_label": grade_label,
            "grade_color": grade_color,
            "breakdown": breakdown,
            "moat_signals": moat_signals,
            "valuation": valuation,
            "price_history": price_history,
            "dates_history": dates_history,
            "earnings_data": earnings_data,
            "pe": safe_val(info.get("trailingPE")),
            "pb": safe_val(info.get("priceToBook")),
            "roe": roe * 100 if roe else None,
            "market_cap": safe_val(info.get("marketCap")),
            "52w_high": safe_val(info.get("fiftyTwoWeekHigh")),
            "52w_low": safe_val(info.get("fiftyTwoWeekLow")),
        }
    except Exception as e:
        error_msg = str(e)
        print(f"[Analysis] Exception for {ticker}: {error_msg}")
        traceback.print_exc()

        # Provide more helpful error messages
        if "Expecting value" in error_msg or "JSONDecodeError" in error_msg:
            return {"error": f"無法獲取 '{ticker}' 的資料。可能原因：\n1. 股票代號錯誤（台股請使用 .TW 結尾，如：2330.TW）\n2. Yahoo Finance 暫時無法回應\n3. 該股票已下市或停牌\n\n請稍後再試或確認代號是否正確。"}
        elif "404" in error_msg or "Not Found" in error_msg:
            return {"error": f"找不到股票代號 '{ticker}'，請確認輸入是否正確"}
        else:
            return {"error": f"分析時發生錯誤：{error_msg}"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze/<ticker>")
def analyze(ticker):
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 12:
        return jsonify({"error": "無效的股票代號"}), 400
    result = get_stock_analysis(ticker)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


# ── Taiwan Top 100 routes ─────────────────────────────────────────────

@app.route("/tw-top100")
def tw_top100():
    return render_template("tw_top100.html")


@app.route("/api/tw-top100")
def api_tw_top100():
    try:
        cache = tw_screener._load_cache()
        status = tw_screener.get_status()

        print(f"[API] tw-top100 request - cache exists: {cache is not None}, running: {status['running']}")

        if cache:
            return jsonify({
                "data": cache.get("data", []),
                "timestamp": cache.get("timestamp"),
                "total_screened": cache.get("count", 0),
                "is_fresh": tw_screener._cache_is_fresh(cache),
                "running": status["running"],
                "status": status,
            })

        return jsonify({
            "data": [],
            "timestamp": None,
            "total_screened": 0,
            "is_fresh": False,
            "running": status["running"],
            "status": status,
        })
    except Exception as e:
        print(f"[API] tw-top100 error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e), "data": []}), 500


@app.route("/api/tw-top100/refresh", methods=["POST"])
def api_tw_top100_refresh():
    try:
        print("[API] Refresh request received")
        started = tw_screener.start_refresh_background()
        message = "更新已開始" if started else "已在更新中"
        print(f"[API] Refresh started: {started}")
        return jsonify({"started": started, "message": message})
    except Exception as e:
        print(f"[API] Refresh error: {e}")
        traceback.print_exc()
        return jsonify({"started": False, "message": f"更新失敗：{str(e)}"}), 500


@app.route("/api/tw-top100/status")
def api_tw_top100_status():
    return jsonify(tw_screener.get_status())


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
