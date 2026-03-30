# 🏦 巴菲特選股系統

基於華倫·巴菲特投資理念的智能選股分析工具，自動評分並計算股票內在價值。

## ✨ 功能特色

### 📊 個股分析
- **8大財務指標評分**：ROE、毛利率、負債比、本益比、自由現金流、營業利益率、市值、股息殖利率
- **巴菲特評分系統**：0-100分綜合評分，A-F分級
- **內在價值計算**：混合 EPS×品質P/E 與葛拉漢公式
- **買賣價格區間**：強力買入、買入區間、合理持有、考慮賣出、強力賣出
- **護城河偵測**：自動識別企業競爭優勢訊號
- **視覺化圖表**：股價走勢、盈利趨勢

### 🇹🇼 台股百強榜
- **自動篩選排名**：每日從1000+上市公司中評分，排名前100強
- **多維度篩選**：按評級、買賣訊號、產業分類
- **即時更新**：背景多線程抓取，進度實時顯示
- **交互式表格**：點擊查看詳細評分、排序、搜尋

## 🚀 本地運行

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動應用
python app.py

# 訪問
http://localhost:5000
```

## 📦 部署到雲端

### 方案 1：Railway (推薦)
1. 前往 [Railway](https://railway.app/)
2. 點擊 "New Project" → "Deploy from GitHub repo"
3. 選擇此專案
4. 自動偵測 Python 並部署

### 方案 2：Render
1. 前往 [Render](https://render.com/)
2. 點擊 "New Web Service"
3. 連接 GitHub 倉庫
4. 設定：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`

### 方案 3：Heroku
```bash
heroku login
heroku create your-app-name
git push heroku main
```

## 📊 資料來源

- **台股資料**：台灣證券交易所 Open API (TWSE)
- **財務數據**：Yahoo Finance API
- **更新頻率**：台股百強榜每24小時自動刷新

## ⚠️ 免責聲明

本系統僅供投資教育參考，不構成任何投資建議。
投資有風險，請自行評估並諮詢專業顧問。

## 🛠️ 技術棧

- **後端**：Flask (Python)
- **資料處理**：Pandas, yfinance
- **前端**：原生 HTML/CSS/JS
- **圖表**：Chart.js
- **部署**：Gunicorn

## 📖 巴菲特選股原則

1. **經濟護城河** - 持久競爭優勢
2. **能力圈原則** - 只投資了解的行業
3. **高ROE** - 股東權益報酬率 > 10%
4. **充裕現金流** - 正向自由現金流
5. **低負債** - 財務穩健
6. **誠實管理層** - 合理配置資本
7. **合理估值** - 30%安全邊際
8. **長期持有** - 10年以上投資視角

---

Made with 💡 by Claude Code
