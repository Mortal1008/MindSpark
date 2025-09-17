
# MindSpark - A LLM RAG System

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39+-orange.svg)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-supported-blue.svg)](https://docker.com)

## 🌟 项目概述
MindSpark 是一个基于 **检索增强生成 (RAG)** 的个人知识库助手。  
它结合大语言模型（LLM）和向量检索，为用户提供智能、准确的问答服务，支持中文优化和多种文档格式。

## ✨ 核心特性
- **智能问答**：基于知识库的精准回答，支持多轮对话  
- **多源知识库**：支持文件上传、网页导入  
- **混合检索**：向量检索 + BM25，提高准确性  
- **多模型支持**：OpenAI、Ollama、DeepSeek、Moonshot、Zhipu  
- **向量数据库**：支持 Chroma、Elasticsearch  
- **直观界面**：基于 Streamlit，支持响应式设计  

## 🏗️ 技术栈
- **前端**: Streamlit  
- **后端**: Python, LlamaIndex, LangChain  
- **数据库**: Redis, MongoDB, Elasticsearch  
- **部署**: Docker, Docker Compose  

## 🚀 快速开始

### 方法一：Docker 部署 (推荐)
```bash
git clone https://github.com/your-username/mindspark.git
cd mindspark
cp .env.docker.example .env.docker
chmod +x deploy.sh
./deploy.sh
```

访问: [http://localhost:8501](http://localhost:8501)

### 方法二：本地运行

```bash
git clone https://github.com/your-username/mindspark.git
cd mindspark
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## 📄 许可证

本项目采用 [MIT License](LICENSE)。

## 📞 联系方式

* 项目主页: [GitHub](https://github.com/your-username/mindspark)
* 问题反馈: [Issues](https://github.com/your-username/mindspark/issues)
