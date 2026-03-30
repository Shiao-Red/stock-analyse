@echo off
chcp 65001 > nul
echo ========================================
echo 推送到 GitHub
echo ========================================
echo.
echo 請先在 GitHub 創建倉庫：
echo https://github.com/new
echo.
echo 倉庫名稱：stock-analyse
echo 設為 Public，不要勾選任何選項
echo.
echo ========================================
pause
echo.

set /p username=請輸入你的 GitHub 用戶名:
if "%username%"=="" (
    echo 錯誤：用戶名不能為空
    pause
    exit /b 1
)

echo.
echo 設定遠端倉庫...
git remote add origin https://github.com/%username%/stock-analyse.git 2>nul
if errorlevel 1 (
    echo 遠端倉庫已存在，嘗試更新...
    git remote set-url origin https://github.com/%username%/stock-analyse.git
)

echo.
echo 推送代碼到 GitHub...
echo 如果要求登入，請輸入你的 GitHub 帳號密碼
echo （或使用 Personal Access Token）
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo ❌ 推送失敗
    echo ========================================
    echo 可能原因：
    echo 1. 倉庫不存在或名稱錯誤
    echo 2. 需要 GitHub 認證
    echo 3. 網路問題
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 推送成功！
echo ========================================
echo.
echo 查看你的倉庫：
echo https://github.com/%username%/stock-analyse
echo.
echo 接下來前往 Render 部署：
echo https://render.com/
echo.
pause
