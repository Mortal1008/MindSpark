# Document-based Q&A
import time
import re
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import uuid
from frontend.state import init_keys
from server.stores.chat_store import CHAT_MEMORY
from llama_index.core.llms import ChatMessage, MessageRole
from server.engine import create_query_engine
from server.stores.config_store import CONFIG_STORE
from config import STORAGE_DIR

# 确保存储目录存在
os.makedirs(STORAGE_DIR, exist_ok=True)
CHAT_SESSIONS_FILE = os.path.join(STORAGE_DIR, "chat_sessions.json")

# 添加会话持久化函数


def save_chat_sessions_to_file():
    """保存聊天会话到本地文件"""
    if "chat_sessions" in st.session_state:
        # 创建一个可序列化的会话副本
        serializable_sessions = {}
        for session_id, session_data in st.session_state.chat_sessions.items():
            # 复制会话数据
            serializable_session = session_data.copy()
            # 序列化消息列表
            serializable_messages = []
            for msg in session_data.get("messages", []):
                # 将ChatMessage对象转换为字典
                if hasattr(msg, "role") and hasattr(msg, "content"):
                    serializable_messages.append(
                        {
                            "role": (
                                msg.role.value
                                if hasattr(msg.role, "value")
                                else str(msg.role)
                            ),
                            "content": msg.content,
                        }
                    )
            serializable_session["messages"] = serializable_messages
            serializable_sessions[session_id] = serializable_session

        # 保存可序列化的数据
        with open(CHAT_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable_sessions, f, ensure_ascii=False, indent=2)


def load_chat_sessions_from_file():
    """从本地文件加载聊天会话"""
    if os.path.exists(CHAT_SESSIONS_FILE):
        try:
            with open(CHAT_SESSIONS_FILE, "r", encoding="utf-8") as f:
                sessions_data = json.load(f)

                # 将序列化的数据转换回原始格式
                loaded_sessions = {}
                for session_id, session_data in sessions_data.items():
                    # 复制会话数据
                    loaded_session = session_data.copy()
                    # 反序列化消息列表
                    messages = []
                    for msg_data in session_data.get("messages", []):
                        # 将字典转换回ChatMessage对象
                        role = (
                            MessageRole(msg_data["role"])
                            if isinstance(msg_data["role"], str)
                            else msg_data["role"]
                        )
                        messages.append(
                            ChatMessage(role=role, content=msg_data["content"])
                        )
                    loaded_session["messages"] = messages
                    loaded_sessions[session_id] = loaded_session

                return loaded_sessions
        except Exception as e:
            print(f"Error loading chat sessions from file: {e}")
            return {}
    return {}


# 初始化会话状态
init_keys()


# 会话管理辅助函数
def get_chat_sessions():
    """获取所有聊天会话列表"""
    if "chat_sessions" not in st.session_state:
        # 尝试从文件加载会话数据
        st.session_state.chat_sessions = load_chat_sessions_from_file()
    return st.session_state.chat_sessions


def save_current_chat_session():
    """保存当前聊天会话"""
    # 获取当前聊天消息
    messages = CHAT_MEMORY.get()
    if messages and len(messages) > 1:  # 至少有一条用户消息和一条助手消息
        # 生成唯一的会话ID
        session_id = str(uuid.uuid4())
        # 使用第一条用户消息作为会话预览
        preview_text = ""
        for msg in messages:
            if msg.role == MessageRole.USER:
                preview_text = msg.content[:50] + (
                    "..." if len(msg.content) > 50 else ""
                )
                break

        # 获取当前时间作为会话时间
        session_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 深拷贝消息列表，确保每次保存的是独立的消息副本
        saved_messages = []
        for msg in messages:
            # 创建新的ChatMessage对象，确保完全独立的副本
            saved_msg = ChatMessage(role=msg.role, content=msg.content)
            saved_messages.append(saved_msg)

        # 保存会话
        chat_sessions = get_chat_sessions()
        chat_sessions[session_id] = {
            "id": session_id,
            "preview": preview_text,
            "time": session_time,
            "messages": saved_messages,
        }

        # 更新会话状态
        st.session_state.chat_sessions = chat_sessions

        # 保存会话到文件
        save_chat_sessions_to_file()

        # 清空当前聊天记录，为新会话做准备
        CHAT_MEMORY.reset()
        CHAT_MEMORY.put(
            ChatMessage(
                role=MessageRole.ASSISTANT,
                content="Feel free to ask about anything in the knowledge base",
            )
        )


def load_chat_session(session_id):
    """加载指定的聊天会话"""
    chat_sessions = get_chat_sessions()
    if session_id in chat_sessions:
        session = chat_sessions[session_id]
        # 清空当前聊天记录
        CHAT_MEMORY.reset()
        # 加载会话消息
        for message in session["messages"]:
            CHAT_MEMORY.put(message)
        return True
    return False


def rename_chat_session(session_id, new_name):
    """重命名指定的聊天会话"""
    chat_sessions = get_chat_sessions()
    if session_id in chat_sessions and new_name.strip():
        # 更新会话的预览文本（作为会话名称）
        chat_sessions[session_id]["preview"] = new_name.strip()
        st.session_state.chat_sessions = chat_sessions
        # 保存会话到文件
        save_chat_sessions_to_file()
        return True
    return False


def delete_chat_session(session_id):
    """删除指定的聊天会话"""
    chat_sessions = get_chat_sessions()
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        st.session_state.chat_sessions = chat_sessions
        # 保存会话到文件
        save_chat_sessions_to_file()
        return True
    return False


def clear_all_chat_sessions():
    """清空所有聊天会话"""
    st.session_state.chat_sessions = {}
    # 保存会话到文件
    save_chat_sessions_to_file()


def perform_query(prompt):
    if not st.session_state.query_engine:
        print("Index is not initialized yet")
    if (not prompt) or prompt.strip() == "":
        print("Query text is required")
    try:
        query_response = st.session_state.query_engine.query(prompt)
        return query_response
    except Exception as e:
        # print(f"An error occurred while processing the query: {e}")
        print(f"An error occurred while processing the query: {type(e).__name__}: {e}")


# https://github.com/halilergul1/QA-app
def simple_format_response_and_sources(response):
    primary_response = getattr(response, "response", "")
    output = {"response": primary_response}
    sources = []
    if hasattr(response, "source_nodes"):
        for node in response.source_nodes:
            node_data = getattr(node, "node", None)
            if node_data:
                metadata = getattr(node_data, "metadata", {})
                text = getattr(node_data, "text", "")
                text = re.sub(
                    r"\n\n|\n|\u2028",
                    lambda m: {"\n\n": "\u2028", "\n": " ", "\u2028": "\n\n"}[
                        m.group()
                    ],
                    text,
                )
                source_info = {
                    "file": metadata.get("file_name", "N/A"),
                    "page": metadata.get("page_label", "N/A"),
                    "text": text,
                }
                sources.append(source_info)
    output["sources"] = sources
    return output


def chatbox():
    # 初始化聊天历史记录会话状态
    if "show_history" not in st.session_state:
        st.session_state.show_history = False
    if "selected_sessions" not in st.session_state:
        st.session_state.selected_sessions = []
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = False
    if "confirm_clear_all" not in st.session_state:
        st.session_state.confirm_clear_all = False
    # 添加重命名相关的会话状态
    if "editing_session_id" not in st.session_state:
        st.session_state.editing_session_id = None
    if "editing_name" not in st.session_state:
        st.session_state.editing_name = ""

    # 创建历史记录入口按钮
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.subheader("Chat with Knowledge Base")
    with col2:
        history_button = st.button("📋 History", key="history_button")
        if history_button:
            st.session_state.show_history = not st.session_state.show_history

    # 显示历史记录面板
    if st.session_state.show_history:
        with st.expander("Chat History", expanded=True):
            chat_sessions = get_chat_sessions()

            # 按时间倒序排列会话
            sorted_sessions = sorted(
                chat_sessions.items(), key=lambda x: x[1]["time"], reverse=True
            )

            # 批量选择和管理区域
            if sorted_sessions:
                # 避免列嵌套，使用垂直布局
                st.markdown("### Manage Chat Sessions")

                # 选择全部复选框
                select_all = st.checkbox("Select All", key="select_all")
                if select_all:
                    st.session_state.selected_sessions = [
                        session_id for session_id, _ in sorted_sessions
                    ]
                elif not select_all and st.session_state.selected_sessions:
                    st.session_state.selected_sessions = []

                # 删除选中和清空全部按钮
                button_container = st.container()
                with button_container:
                    # 使用两列布局，但确保这是顶层列
                    col1, col2 = st.columns(2)
                    with col1:
                        delete_selected = st.button(
                            "Delete Selected",
                            key="delete_selected",
                            disabled=len(st.session_state.selected_sessions) == 0,
                        )
                        if delete_selected:
                            st.session_state.confirm_delete = True
                    with col2:
                        clear_all = st.button(
                            "Clear All History",
                            key="clear_all",
                            disabled=len(sorted_sessions) == 0,
                        )
                        if clear_all:
                            st.session_state.confirm_clear_all = True

                # 删除确认对话框
                if st.session_state.confirm_delete:
                    st.error(
                        "Are you sure you want to delete selected chat sessions? This action cannot be undone."
                    )
                    # 使用两列布局，但确保这是顶层列
                    col_conf, col_cancel = st.columns(2)
                    with col_conf:
                        if st.button("Confirm Delete", key="confirm_delete"):
                            for session_id in st.session_state.selected_sessions:
                                delete_chat_session(session_id)
                            st.session_state.selected_sessions = []
                            st.session_state.confirm_delete = False
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel", key="cancel_delete"):
                            st.session_state.confirm_delete = False

                # 清空所有历史确认对话框
                if st.session_state.confirm_clear_all:
                    st.error(
                        "Are you sure you want to clear ALL chat history? This action cannot be undone."
                    )
                    # 使用两列布局，但确保这是顶层列
                    col_conf, col_cancel = st.columns(2)
                    with col_conf:
                        if st.button("Confirm Clear All", key="confirm_clear_all"):
                            clear_all_chat_sessions()
                            st.session_state.confirm_clear_all = False
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel", key="cancel_clear_all"):
                            st.session_state.confirm_clear_all = False

                st.markdown("---")

                # 显示会话列表
                st.markdown("### Chat Sessions")
                for session_id, session in sorted_sessions:
                    # 使用一行容器来显示每个会话
                    session_row = st.container(border=True)
                    with session_row:
                        # 使用顶层列来布局会话项的各个部分
                        col_check, col_info, col_delete = st.columns([0.05, 0.85, 0.1])

                        with col_check:
                            is_selected = st.checkbox(
                                "",
                                key=f"select_{session_id}",
                                value=session_id in st.session_state.selected_sessions,
                            )
                            if (
                                is_selected
                                and session_id not in st.session_state.selected_sessions
                            ):
                                st.session_state.selected_sessions.append(session_id)
                            elif (
                                not is_selected
                                and session_id in st.session_state.selected_sessions
                            ):
                                st.session_state.selected_sessions.remove(session_id)

                        with col_info:
                            # 显示时间
                            st.text(session["time"])

                            # 处理重命名逻辑
                            if st.session_state.editing_session_id == session_id:
                                # 显示文本输入框进行重命名
                                new_name = st.text_input(
                                    "Edit session name:",
                                    value=st.session_state.editing_name,
                                    key=f"rename_input_{session_id}",
                                    label_visibility="visible",
                                )

                                # 直接放置按钮，不使用列
                                save_key = f"save_name_{session_id}"
                                cancel_key = f"cancel_name_{session_id}"

                                if st.button("Save", key=save_key):
                                    if new_name.strip():
                                        rename_chat_session(session_id, new_name)
                                        st.session_state.editing_session_id = None
                                        st.session_state.editing_name = ""
                                        st.rerun()

                                if st.button("Cancel", key=cancel_key):
                                    st.session_state.editing_session_id = None
                                    st.session_state.editing_name = ""
                                    st.rerun()
                            else:
                                # 在同一行显示名称和按钮
                                name_col, edit_col, load_col = st.columns(
                                    [0.6, 0.2, 0.2]
                                )

                                with name_col:
                                    st.write(f"**{session['preview']}**")

                                with edit_col:
                                    edit_key = f"edit_name_{session_id}"
                                    if st.button(
                                        "Edit Name",
                                        key=edit_key,
                                        help="Click to rename this chat session",
                                    ):
                                        st.session_state.editing_session_id = session_id
                                        st.session_state.editing_name = session[
                                            "preview"
                                        ]
                                        st.rerun()

                                with load_col:
                                    load_key = f"load_{session_id}"
                                    if st.button("Load", key=load_key):
                                        load_chat_session(session_id)
                                        st.session_state.show_history = False
                                        st.rerun()

                        with col_delete:
                            if st.button(
                                "🗑️",
                                key=f"del_{session_id}",
                                help="Delete this chat session",
                            ):
                                delete_chat_session(session_id)
                                st.rerun()
            else:
                st.info("No chat history available.")

    # 添加新会话按钮
    if len(CHAT_MEMORY.get()) > 1:  # 仅当有对话历史时显示
        col_left, col_right = st.columns([0.9, 0.1])
        with col_right:
            if st.button("New Chat", key="new_chat"):
                # 保存当前会话
                save_current_chat_session()
                # 重新加载页面以显示新会话
                st.rerun()

    # Load Q&A history
    messages = CHAT_MEMORY.get()
    if len(messages) == 0:
        # Initialize Q&A record
        CHAT_MEMORY.put(
            ChatMessage(
                role=MessageRole.ASSISTANT,
                content="Feel free to ask about anything in the knowledge base",
            )
        )
        messages = CHAT_MEMORY.get()

    # Show Q&A records
    for message in messages:
        with st.chat_message(message.role):
            st.write(message.content)

    if prompt := st.chat_input(
        "Input your question"
    ):  # Prompt the user to input the question then add it to the message history
        with st.chat_message(MessageRole.USER):
            st.write(prompt)
            CHAT_MEMORY.put(ChatMessage(role=MessageRole.USER, content=prompt))
        with st.chat_message(MessageRole.ASSISTANT):
            with st.spinner("Thinking..."):
                start_time = time.time()
                response = perform_query(prompt)
                end_time = time.time()
                query_time = round(end_time - start_time, 2)
                if response is None:
                    st.write("Couldn't come up with an answer.")
                else:
                    response_text = st.write_stream(response.response_gen)
                    st.write(f"Took {query_time} second(s)")
                    details_title = f"Found {len(response.source_nodes)} document(s)"
                    with st.expander(
                        details_title,
                        expanded=False,
                    ):
                        source_nodes = []
                        for item in response.source_nodes:
                            node = item.node
                            score = item.score

                            # 优先使用file_name（适用于文件文档）
                            title = node.metadata.get("file_name", None)

                            # 如果没有file_name，尝试使用自定义名称（网页文档的情况）
                            if title is None:
                                # 先尝试获取自定义名称
                                title = node.metadata.get("custom_name", None)

                                # 如果没有自定义名称，再尝试获取网页标题
                                if title is None:
                                    title = node.metadata.get("title", "N/A")

                            # 获取其他信息
                            page_label = node.metadata.get("page_label", "N/A")
                            text = node.text
                            short_text = text[:50] + "..." if len(text) > 50 else text

                            # 添加到源节点列表
                            source_nodes.append(
                                {
                                    "Title": title,
                                    "Page": page_label,
                                    "Text": short_text,
                                    "Score": f"{score:.2f}",
                                }
                            )
                        df = pd.DataFrame(source_nodes)
                        st.table(df)
                    # store the answer in the chat history
                    CHAT_MEMORY.put(
                        ChatMessage(role=MessageRole.ASSISTANT, content=response_text)
                    )


def main():
    st.header("Query")
    if st.session_state.llm is not None:
        current_llm_info = CONFIG_STORE.get(key="current_llm_info")
        current_llm_settings = CONFIG_STORE.get(key="current_llm_settings")
        st.caption(
            "LLM `"
            + current_llm_info["service_provider"]
            + "` `"
            + current_llm_info["model"]
            + "` Response mode `"
            + current_llm_settings["response_mode"]
            + "` Top K `"
            + str(current_llm_settings["top_k"])
            + "` Temperature `"
            + str(current_llm_settings["temperature"])
            + "` Reranking `"
            + str(current_llm_settings["use_reranker"])
            + "` Top N `"
            + str(current_llm_settings["top_n"])
            + "` Reranker `"
            + current_llm_settings["reranker_model"]
            + "`"
        )
        if st.session_state.index_manager is not None:
            if st.session_state.index_manager.check_index_exists():
                st.session_state.index_manager.load_index()
                st.session_state.query_engine = create_query_engine(
                    index=st.session_state.index_manager.index,
                    use_reranker=current_llm_settings["use_reranker"],
                    response_mode=current_llm_settings["response_mode"],
                    top_k=current_llm_settings["top_k"],
                    top_n=current_llm_settings["top_n"],
                    reranker=current_llm_settings["reranker_model"],
                )
                print("Index loaded and query engine created")
                chatbox()
            else:
                print("Index does not exist yet")
                st.warning(
                    "Your knowledge base is empty. Please upload some documents into it first."
                )
        else:
            print("IndexManager is not initialized yet.")
            st.warning("Please upload documents into your knowledge base first.")
    else:
        st.warning("Please configure LLM first.")


main()
