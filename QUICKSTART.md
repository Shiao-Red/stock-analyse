# ⚡ 快速開始 - 3 分鐘部署到雲端

## 🎯 最簡單的方式（推薦）

### 步驟 1：準備代碼
雙擊運行 `deploy.bat`，它會：
- ✅ 初始化 Git 倉庫
- ✅ 提交所有文件
- ✅ 準備好部署

### 步驟 2：選擇平台部署

#### 🚂 Railway（最推薦）
1. 訪問 https://railway.app/
2. 用 GitHub 登入
3. 點擊 "New Project" → "Deploy from GitHub repo"
4. 授權並選擇你的倉庫
5. 等待 2-3 分鐘自動部署
6. 點擊 "Generate Domain" 獲取網址
7. ✅ 完成！訪問你的網址

**特點**：
- 💰 每月 $5 免費額度
- ⚡ 自動 CI/CD
- 📊 監控面板
- 🔥 不會休眠

#### 🌐 Render（完全免費）
1. 訪問 https://render.com/
2. 用 GitHub 登入
3. 點擊 "New +" → "Web Service"
4. 選擇倉庫
5. 設定：
   - **Name**: `stock-analyse`
   - **Environment**: `Python 3`
   - **Build Command**: 自動偵測
   - **Start Command**: 自動偵測
6. 選擇 **Free** 方案
7. 點擊 "Create Web Service"
8. ✅ 完成！（約 5 分鐘）

**特點**：
- 💰 完全免費
- ⚠️ 15 分鐘閒置後休眠
- 🔐 自動 SSL

---

## 📋 部署前檢查清單

- [x] ✅ `requirements.txt` - Python 依賴
- [x] ✅ `Procfile` - 啟動指令
- [x] ✅ `runtime.txt` - Python 版本
- [x] ✅ `.gitignore` - 忽略文件
- [x] ✅ `Dockerfile` - Docker 部署
- [x] ✅ `app.py` - 已配置環境變數

---

## 🧪 本地測試

部署前想先測試？雙擊 `test_local.bat`：
```
訪問：http://localhost:5000
```

---

## 🎁 部署後你將擁有

✅ 一個公開訪問的網站
✅ 自動 HTTPS 加密
✅ 股票分析功能
✅ 台股百強榜
✅ 自動數據更新

示例網址：
- Railway: `https://stock-analyse-production.up.railway.app`
- Render: `https://stock-analyse.onrender.com`

---

## 🐛 遇到問題？

### 問題 1：Git 未安裝
下載安裝：https://git-scm.com/download/win

### 問題 2：沒有 GitHub 帳號
1. 註冊：https://github.com/
2. 創建新倉庫（Public）
3. 按照提示推送代碼

### 問題 3：部署失敗
1. 檢查部署平台的 Logs
2. 確認 `requirements.txt` 正確
3. 查看 `DEPLOYMENT.md` 詳細說明

---

## 📚 更多資訊

- 詳細部署指南：`DEPLOYMENT.md`
- 專案說明：`README.md`
- 技術文檔：代碼註釋

---

## 🎉 下一步

部署成功後：
1. 分享你的網址給朋友
2. 測試搜尋功能（試試：2330.TW）
3. 點擊「立即更新」開始台股篩選
4. 享受你的巴菲特選股系統！

**祝你投資順利！** 📈✨
