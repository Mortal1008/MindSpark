# Log configuration
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# 读取 .env 环境变量 (SMTP 配置等)
try:
    from dotenv import load_dotenv

    load_dotenv(".env")  # 不覆盖已有系统环境
except ImportError:
    logging.warning("未安装 python-dotenv，跳过加载 .env 文件。")

# Configure the Streamlit Web Application
import streamlit as st
from frontend.state import init_state
from frontend.auth import require_login_ui, inject_global_css, logout

if __name__ == "__main__":

    st.set_page_config(
        page_title="MindSpark - A LLM RAG system",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items=None,
    )

    inject_global_css()
    st.logo("frontend/images/MindSpark_Logo.png")

    if not hasattr(st.session_state, "initialized"):
        init_state()

    # Auth gate
    if "user" not in st.session_state:
        # 未登录时提供占位导航以清空之前登录残留的页面
        placeholder_pages = {
            "认证": [st.Page("frontend/auth_placeholder.py", title="登录")]
        }
        placeholder_nav = st.navigation(placeholder_pages, position="sidebar")
        placeholder_nav.run()
        require_login_ui()
    else:
        with st.sidebar:
            st.markdown(f"**User:** {st.session_state['user']['email']}")
            if st.button("Log out"):
                logout()
        pages = {
            "Application": [
                st.Page("frontend/Document_QA.py", title="Query"),
            ],
            "Knowledge Base": [
                st.Page("frontend/KB_File.py", title="File"),
                st.Page("frontend/KB_Web.py", title="Web"),
                st.Page("frontend/KB_Manage.py", title="Manage"),
            ],
            "Model & Tool": [
                st.Page("frontend/Model_LLM.py", title="LLM"),
                st.Page("frontend/Model_Embed.py", title="Embed"),
                st.Page("frontend/Model_Rerank.py", title="Rerank"),
                st.Page("frontend/Storage.py", title="Storage"),
            ],
            "Settings": [
                st.Page("frontend/Setting_Advanced.py", title="Advanced"),
            ],
        }

        pg = st.navigation(pages, position="sidebar")
        pg.run()
