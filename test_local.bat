@echo off
echo ========================================
echo 本地測試運行
echo ========================================
echo.

echo 檢查依賴套件...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo 正在安裝依賴套件...
    pip install -r requirements.txt
)

echo.
echo 啟動應用程式...
echo 請訪問：http://localhost:5000
echo 按 Ctrl+C 停止服務器
echo.
python app.py
