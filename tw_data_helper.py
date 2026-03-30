"""
台股資料輔助模組
當 yfinance 無法獲取台股資料時，使用台灣證交所 Open API
"""
import requests
import time
from datetime import datetime


def get_tw_stock_info(stock_code: str):
    """
    從台灣證交所 API 獲取台股基本資料
    stock_code: 4位數代號，例如 "2330"
    """
    try:
        # 移除 .TW 後綴
        code = stock_code.replace(".TW", "").replace(".tw", "")

        if not code.isdigit() or len(code) != 4:
            return None

        print(f"[tw_data_helper] Fetching TW stock data for {code}")

        # 1. 獲取即時股價 (STOCK_DAY_ALL)
        url_price = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        headers = {"User-Agent": "Mozilla/5.0"}

        resp = requests.get(url_price, headers=headers, timeout=10)
        resp.raise_for_status()

        price_data = None
        for item in resp.json():
            if item.get("Code") == code:
                price_data = item
                break

        if not price_data:
            print(f"[tw_data_helper] Stock {code} not found in STOCK_DAY_ALL")
            return None

        # 2. 獲取本益比、殖利率等 (BWIBBU_ALL)
        url_ratio = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        ratio_data = {}

        try:
            resp2 = requests.get(url_ratio, headers=headers, timeout=10)
            resp2.raise_for_status()

            for item in resp2.json():
                if item.get("Code") == code:
                    ratio_data = item
                    break
        except Exception as e:
            print(f"[tw_data_helper] Failed to get ratio data: {e}")

        # 解析資料
        def safe_float(val, default=None):
            try:
                if val and val != "-":
                    return float(str(val).replace(",", ""))
                return default
            except:
                return default

        name = price_data.get("Name", code)
        close_price = safe_float(price_data.get("ClosingPrice"))
        change = safe_float(price_data.get("Change"))
        trade_value = safe_float(price_data.get("TradeValue", 0))
        trade_volume = safe_float(price_data.get("TradeVolume", 0))

        pe_ratio = safe_float(ratio_data.get("PEratio"))
        pb_ratio = safe_float(ratio_data.get("PBratio"))
        div_yield = safe_float(ratio_data.get("DividendYield"))

        # 計算漲跌幅
        change_pct = None
        if close_price and change:
            prev_close = close_price - change
            if prev_close > 0:
                change_pct = round((change / prev_close) * 100, 2)

        result = {
            "ticker": f"{code}.TW",
            "code": code,
            "name": name,
            "long_name": name,
            "price": close_price,
            "currency": "TWD",
            "change_pct": change_pct,
            "sector": "未知",
            "industry": "未知",
            "country": "Taiwan",
            "exchange": "TPE",
            "pe": pe_ratio,
            "pb": pb_ratio,
            "div_yield": div_yield,
            "market_cap": None,  # TWSE API 沒有提供
            "trade_value": trade_value,
            "trade_volume": trade_volume,
            "data_source": "TWSE Open API",
            "description": f"{name} - 台灣上市股票",
        }

        print(f"[tw_data_helper] Successfully fetched data for {code}: {name}")
        return result

    except Exception as e:
        print(f"[tw_data_helper] Error fetching TW stock {stock_code}: {e}")
        import traceback
        traceback.print_exc()
        return None


def enrich_tw_stock_with_yfinance(tw_data: dict, yf_info: dict):
    """
    用 yfinance 資料補充台股資料
    """
    if not tw_data or not yf_info:
        return tw_data

    try:
        # 補充 yfinance 有但 TWSE API 沒有的資料
        tw_data["sector"] = yf_info.get("sector", tw_data.get("sector", "未知"))
        tw_data["industry"] = yf_info.get("industry", tw_data.get("industry", "未知"))
        tw_data["market_cap"] = yf_info.get("marketCap")
        tw_data["description"] = yf_info.get("longBusinessSummary", "")[:300] if yf_info.get("longBusinessSummary") else tw_data.get("description", "")

        # 如果 yfinance 有更準確的資料，使用 yfinance
        if yf_info.get("trailingPE") and not tw_data.get("pe"):
            tw_data["pe"] = round(yf_info.get("trailingPE"), 1)

        if yf_info.get("priceToBook") and not tw_data.get("pb"):
            tw_data["pb"] = round(yf_info.get("priceToBook"), 2)

        tw_data["data_source"] = "TWSE + yfinance"

    except Exception as e:
        print(f"[tw_data_helper] Error enriching data: {e}")

    return tw_data


def is_tw_stock(ticker: str) -> bool:
    """檢查是否為台股代號"""
    ticker_upper = ticker.upper()
    if ".TW" in ticker_upper or ".TWO" in ticker_upper:
        return True

    # 純數字4碼也可能是台股
    code = ticker.replace(".TW", "").replace(".tw", "").replace(".TWO", "").replace(".two", "")
    if code.isdigit() and len(code) == 4:
        return True

    return False


# 測試函數
if __name__ == "__main__":
    # 測試台積電
    result = get_tw_stock_info("2330")
    if result:
        print("\n=== 台積電資料 ===")
        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print("無法獲取資料")
