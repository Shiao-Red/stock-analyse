@echo off
echo ========================================
echo 巴菲特選股系統 - 快速部署腳本
echo ========================================
echo.

echo [1/5] 初始化 Git 倉庫...
git init
if errorlevel 1 (
    echo 錯誤：請確認已安裝 Git
    echo 下載：https://git-scm.com/download/win
    pause
    exit /b 1
)

echo.
echo [2/5] 添加所有文件到 Git...
git add .

echo.
echo [3/5] 創建初始提交...
git commit -m "Initial commit - 巴菲特選股系統"

echo.
echo [4/5] 設定主分支為 main...
git branch -M main

echo.
echo ========================================
echo ✅ Git 倉庫準備完成！
echo ========================================
echo.
echo 接下來的步驟：
echo.
echo 【方案 1：Railway（推薦）】
echo 1. 前往 https://railway.app/
echo 2. 註冊/登入（可用 GitHub 登入）
echo 3. 點擊 "Start a New Project"
echo 4. 選擇 "Deploy from GitHub repo"
echo 5. 連接 GitHub 並選擇此專案
echo 6. 自動部署完成！
echo.
echo 【方案 2：推送到 GitHub】
echo 1. 在 GitHub 創建新倉庫
echo 2. 運行以下命令：
echo    git remote add origin https://github.com/你的用戶名/stock-analyse.git
echo    git push -u origin main
echo.
echo 【方案 3：Heroku】
echo 1. 安裝 Heroku CLI：https://devcenter.heroku.com/articles/heroku-cli
echo 2. 運行：heroku login
echo 3. 運行：heroku create your-app-name
echo 4. 運行：git push heroku main
echo.
echo ========================================
pause
