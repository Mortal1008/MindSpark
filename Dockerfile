FROM python:3.11-slim AS builder

# 安装系统依赖（包括编译工具）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装Ollama（可选）
RUN curl -fsSL https://ollama.ai/install.sh | sh

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 升级pip并安装依赖
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.11-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制所有内容
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

WORKDIR /app

# 复制应用代码和配置
COPY --chown=appuser:appuser . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
