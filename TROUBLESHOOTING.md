# 🔧 故障排除指南

## 🚨 當前問題：個股和排行榜都失敗

我已經推送了重大修復，請按照以下步驟操作：

---

## ✅ 步驟 1：確認 Render 重新部署

1. **前往 Render Dashboard**
   - https://dashboard.render.com/

2. **選擇你的服務** `stock-analyse`

3. **查看 Events 標籤**
   - 應該看到 "Deploy started"
   - 等待變成 "Deploy live"（約 3-5 分鐘）

4. **查看部署日誌**
   - 點擊 "Logs" 標籤
   - 查找是否有錯誤訊息
   - 應該看到類似：
     ```
     Installing dependencies...
     Successfully installed flask-3.0.0 yfinance-0.2.48 ...
     Starting service...
     ```

---

## ✅ 步驟 2：測試診斷端點

部署完成後，**先測試診斷端點**：

### 訪問
```
https://你的網址.onrender.com/api/health
```

### 預期結果（成功）
```json
{
  "status": "ok",
  "python_version": "3.11.x",
  "yfinance_test": {
    "ticker": "AAPL",
    "success": true,
    "info_keys": 100+
  },
  "session_configured": true
}
```

### 如果失敗
會顯示詳細錯誤訊息，請複製完整的 JSON 回應。

---

## ✅ 步驟 3：測試個股分析

如果診斷端點成功，測試個股：

### 測試 1：美股（簡單）
```
搜尋：AAPL
```

### 測試 2：台股
```
搜尋：2330.TW
```

---

## 🔍 查看詳細日誌

### 在 Render Dashboard

1. **點擊 "Logs" 標籤**

2. **搜尋股票時，應該看到**：
   ```
   [get_ticker_info_safe] Attempt 1 for AAPL
   [get_ticker_info_safe] Fast info available for AAPL
   [get_ticker_info_safe] Info keys: ['address1', 'city', ...]
   [Analysis] Successfully got data for: Apple Inc.
   ```

3. **如果失敗，會看到**：
   ```
   [get_ticker_info_safe] Attempt 1 failed for XXX: ...
   ```

---

## 🆘 常見問題和解決方案

### 問題 1：部署時依賴安裝失敗

**症狀**：
```
ERROR: Could not find a version that satisfies the requirement...
```

**解決**：
1. 檢查 Render 使用的 Python 版本
2. 在 Render 設定中確認 Python 版本為 3.11
3. 如果不是，在 Environment Variables 添加：
   - Key: `PYTHON_VERSION`
   - Value: `3.11.0`

---

### 問題 2：yfinance 返回空資料

**症狀**：
```
[get_ticker_info_safe] Invalid info for XXX: dict=True, len=0
```

**可能原因**：
- Yahoo Finance API 限制
- 網路連接問題
- 股票代號錯誤

**解決**：
1. 確認代號格式正確（台股加 .TW）
2. 等待 5-10 分鐘再試
3. 查看 `/api/health` 是否正常

---

### 問題 3：Render 服務一直重啟

**症狀**：頁面顯示 "Service Unavailable"

**解決**：
1. 查看 Render Logs
2. 找到錯誤訊息
3. 可能是記憶體不足（免費方案 512MB）
4. 考慮進一步減少 `MAX_CANDIDATES`

---

### 問題 4：個股分析超時

**症狀**：等很久沒有回應

**解決**：
1. Render 免費方案 CPU 較慢，需等待 10-30 秒
2. 查看 Logs 確認是否在處理
3. 如果超過 1 分鐘，可能需要優化

---

## 📊 性能優化選項

如果服務太慢或經常失敗，可以調整：

### 選項 1：減少台股候選數量

編輯 `tw_screener.py`：
```python
MAX_CANDIDATES = 30    # 從 50 降到 30
MAX_WORKERS = 2        # 從 3 降到 2
```

### 選項 2：增加 Cache 有效期

編輯 `tw_screener.py`：
```python
CACHE_MAX_AGE_HOURS = 48  # 從 24 增加到 48
```

### 選項 3：禁用台股百強榜

如果只需要個股分析功能，可以暫時註釋掉台股相關路由。

---

## 📞 需要協助時提供的資訊

如果仍然無法解決，請提供：

1. **診斷端點結果**
   - 訪問 `/api/health` 的完整 JSON

2. **Render 日誌**
   - 複製最近的 20-30 行日誌

3. **錯誤訊息**
   - 前端顯示的完整錯誤

4. **測試的股票代號**
   - 你嘗試搜尋了什麼

5. **Render 服務資訊**
   - 部署區域（Region）
   - Python 版本

---

## 🎯 本次修復內容

### ✅ 更新依賴套件
- yfinance: 0.2.40 → 0.2.48（最新版本）
- 添加 lxml, html5lib, beautifulsoup4

### ✅ 配置 HTTP Session
- 自動重試機制（3次）
- 退避策略（backoff）
- 處理 429, 500, 502, 503, 504 錯誤

### ✅ 設定 User-Agent
- 模擬真實瀏覽器請求
- 避免被 Yahoo Finance 封鎖

### ✅ 添加詳細日誌
- 每一步都記錄
- 便於診斷問題

### ✅ 添加診斷端點
- `/api/health` 快速檢查系統狀態

---

## 📋 測試清單

完成部署後，請按順序測試：

- [ ] ✅ 訪問首頁 - 頁面載入正常
- [ ] ✅ 訪問 `/api/health` - 返回成功狀態
- [ ] ✅ 搜尋 `AAPL` - 個股分析成功
- [ ] ✅ 搜尋 `2330.TW` - 台股分析成功
- [ ] ✅ 訪問 `/tw-top100` - 百強榜頁面載入
- [ ] ✅ 點擊"立即更新" - 開始篩選（需等待 5-10 分鐘）

---

## 🚀 如果一切正常

恭喜！系統已成功部署。記得：

1. **撤銷 GitHub Token**（安全性）
   - https://github.com/settings/tokens

2. **分享你的網址**
   - 讓朋友一起使用！

3. **監控使用情況**
   - Render 免費方案有限制
   - 每月 750 小時

---

## 📧 仍需協助？

將上述資訊整理好，告訴我：
- 哪個步驟失敗了
- 看到什麼錯誤訊息
- 診斷端點的回應

我會繼續協助你！🔧
