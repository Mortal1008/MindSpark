#!/bin/bash

set -e

echo "🚀 开始部署MindSpark Docker化版本..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p data storage localmodels logs ssl

# 设置权限
chmod 755 data storage localmodels logs

# 检查.env.docker文件
if [ ! -f ".env.docker" ]; then
    echo "❌ .env.docker文件不存在，请先配置环境变量"
    exit 1
fi

# 构建Docker镜像
echo "🔨 构建Docker镜像..."
docker-compose build --no-cache

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose down

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 检查服务健康状态
echo "🏥 检查服务健康状态..."
for i in {1..30}; do
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo "✅ MindSpark应用已启动"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ MindSpark应用启动超时"
        docker-compose logs mindspark-app
        exit 1
    fi
    echo "等待应用启动... ($i/30)"
    sleep 5
done

# 显示访问信息
echo "🎉 部署完成！"
echo "📱 访问地址: http://localhost"
echo "🔧 Streamlit地址: http://localhost:8501"
echo "📊 Redis地址: http://localhost:6379"
echo "🔍 Chroma地址: http://localhost:8000"
echo "🤖 Ollama地址: http://localhost:11434"

# 显示日志（可选）
echo "📋 查看日志: docker-compose logs -f"
