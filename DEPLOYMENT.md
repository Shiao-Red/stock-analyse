# 🚀 雲端部署指南

## 準備工作

所有部署配置文件已就緒：
- ✅ `requirements.txt` - Python 依賴套件
- ✅ `Procfile` - 啟動指令
- ✅ `runtime.txt` - Python 版本
- ✅ `.gitignore` - 忽略文件
- ✅ `app.py` - 已配置環境變數

---

## 🎯 推薦方案：Railway (最簡單)

### 優點
- ⚡ 免費額度：每月 $5 免費額度
- 🔄 自動部署：Git push 即部署
- 📊 內建監控面板
- 🌐 自動 HTTPS 網域

### 部署步驟

1. **創建 Git 倉庫**
```bash
cd C:\Users\traff\Desktop\stock_analyse
git init
git add .
git commit -m "Initial commit - 巴菲特選股系統"
```

2. **推送到 GitHub**
```bash
# 在 GitHub 創建新倉庫後
git remote add origin https://github.com/你的用戶名/stock-analyse.git
git branch -M main
git push -u origin main
```

3. **部署到 Railway**
   - 前往 https://railway.app/
   - 點擊 "Start a New Project"
   - 選擇 "Deploy from GitHub repo"
   - 選擇你的 `stock-analyse` 倉庫
   - Railway 會自動偵測 Python 並部署
   - 等待 2-3 分鐘完成部署
   - 點擊 "Generate Domain" 獲取網址

4. **訪問你的應用**
   - 網址類似：`https://stock-analyse-production.up.railway.app`

---

## 🌟 方案二：Render (完全免費)

### 優點
- 💰 完全免費（有限制）
- 🔐 自動 SSL 憑證
- 📈 易於擴展

### 部署步驟

1. **推送代碼到 GitHub**（同上）

2. **部署到 Render**
   - 前往 https://render.com/
   - 點擊 "New +" → "Web Service"
   - 連接 GitHub，選擇倉庫
   - 設定：
     ```
     Name: stock-analyse
     Environment: Python 3
     Build Command: pip install -r requirements.txt
     Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
     ```
   - 選擇 "Free" 方案
   - 點擊 "Create Web Service"

3. **注意事項**
   - 免費方案在閒置 15 分鐘後會休眠
   - 首次訪問需要 30-60 秒喚醒

---

## 🔥 方案三：Heroku

### 部署步驟

1. **安裝 Heroku CLI**
   - 下載：https://devcenter.heroku.com/articles/heroku-cli

2. **登入並部署**
```bash
# 登入
heroku login

# 創建應用
heroku create your-stock-app-name

# 部署
git push heroku main

# 開啟應用
heroku open
```

3. **查看日誌**
```bash
heroku logs --tail
```

---

## 🐳 方案四：Google Cloud Run (進階)

### 需要 Dockerfile

1. **創建 Dockerfile**（已在下方提供）

2. **部署**
```bash
gcloud run deploy stock-analyse \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

---

## ⚙️ 環境變數設定

如果需要設定環境變數（API keys 等）：

### Railway
Settings → Variables → 添加變數

### Render
Environment → Environment Variables → 添加

### Heroku
```bash
heroku config:set KEY=value
```

---

## 🔍 部署後檢查清單

- [ ] 首頁載入正常
- [ ] 搜尋股票功能正常（測試：2330.TW）
- [ ] 台股百強榜頁面正常
- [ ] 點擊"立即更新"觸發台股篩選
- [ ] 檢查 cache 目錄是否自動創建

---

## 🐛 常見問題

### 1. 應用啟動失敗
**檢查**：
```bash
# Railway/Render 查看 Logs
# 確認 requirements.txt 套件是否都安裝成功
```

### 2. 台股更新很慢或超時
**原因**：免費方案 CPU/記憶體限制
**解決**：
- 修改 `tw_screener.py` 中的 `MAX_CANDIDATES` 從 200 降到 100
- 減少 `MAX_WORKERS` 從 8 降到 4

### 3. cache 目錄不存在
**自動處理**：代碼已包含 `os.makedirs(CACHE_DIR, exist_ok=True)`

### 4. 免費方案限制
- **Railway**: 每月 $5 額度（約 500 小時）
- **Render**: 750 小時/月，15分鐘閒置休眠
- **Heroku**: 需綁定信用卡才有免費額度

---

## 📊 效能優化建議

部署到雲端後：

1. **減少資料抓取量**
```python
# tw_screener.py
MAX_CANDIDATES = 100  # 原本 200
MAX_WORKERS = 4       # 原本 8
```

2. **增加 cache 有效期**
```python
# tw_screener.py
CACHE_MAX_AGE_HOURS = 48  # 原本 24
```

3. **添加 CDN**（進階）
   - 使用 Cloudflare 加速靜態資源

---

## 🎉 部署成功！

部署後你的應用會有一個公開網址，例如：
- `https://stock-analyse-production.up.railway.app`
- `https://stock-analyse.onrender.com`

分享給朋友開始使用吧！🚀

---

## 📞 需要協助？

如遇到問題，請檢查：
1. 部署平台的 Logs（日誌）
2. 確認所有配置文件存在
3. GitHub 倉庫是否 public
