# 使用官方 Python 運行時作為基礎鏡像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建 cache 目錄
RUN mkdir -p cache

# 暴露端口
EXPOSE 8080

# 設定環境變數
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# 啟動命令
CMD exec gunicorn --bind :$PORT --workers 2 --timeout 120 --threads 4 app:app
