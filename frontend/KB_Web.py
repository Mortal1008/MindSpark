import time
import streamlit as st
import time
import pandas as pd

# 导入所需的网页读取器
from server.readers.beautiful_soup_web import BeautifulSoupWebReader
from server.readers.jina_web import JinaWebReader


def handle_website():
    # 确保session_state中有必要的配置参数
    if "websites" not in st.session_state:
        st.session_state["websites"] = []

    # 初始化chunk_size和chunk_overlap参数，设置默认值
    if "chunk_size" not in st.session_state:
        st.session_state.chunk_size = 1000  # 默认值，可根据需要调整

    if "chunk_overlap" not in st.session_state:
        st.session_state.chunk_overlap = 200  # 默认值，可根据需要调整

    # 确保session_state中有预览相关的配置
    if "preview_content" not in st.session_state:
        st.session_state.preview_content = None
    if "preview_title" not in st.session_state:
        st.session_state.preview_title = None
    if "show_preview" not in st.session_state:
        st.session_state.show_preview = False
    if "preview_error" not in st.session_state:
        st.session_state.preview_error = None

    st.header("Load Web Pages")
    st.caption(
        "Enter URLs and optionally give custom names for web pages to add to the knowledge base."
    )

    with st.form("website-form", clear_on_submit=True):
        st.markdown("### Add Website")
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            new_website = st.text_input(
                "Web page address", placeholder="https://example.com"
            )
        with col2:
            custom_name = st.text_input(
                "Custom name (optional)", placeholder="Give a name"
            )
        tags_input = st.text_input(
            "Tags (optional)", placeholder="tag1, tag2", help="不同标签用英文逗号分隔"
        )

        add_button = st.form_submit_button("Add")
        if add_button and new_website != "":
            # 使用字典存储URL、自定义名称和标签
            # 解析标签输入，去除空格并过滤空标签
            tags = []
            if tags_input:
                tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]

            website_info = {
                "url": new_website,
                "name": custom_name if custom_name else None,
                "tags": tags,
            }
            st.session_state["websites"].append(website_info)

    with st.expander(
        "Text processing parameter configuration",
        expanded=True,
    ):
        cols = st.columns(2)
        chunk_size = cols[0].number_input(
            "Maximum length of a single text block: ",
            1,
            4096,
            st.session_state.chunk_size,
            key="web_chunk_size",
        )
        chunk_overlap = cols[1].number_input(
            "Adjacent text overlap length: ",
            0,
            st.session_state.chunk_size,
            st.session_state.chunk_overlap,
            key="web_chunk_overlap",
        )

        # Add web reader selection
        reader_type = st.selectbox(
            "Web Page Reader Type:",
            options=["BeautifulSoup Reader", "Jina AI Reader"],
            index=0,
            help="BeautifulSoup Reader is basic but works offline. Jina AI Reader provides better content extraction but requires internet access.",
        )

    # 添加URL内容预览函数
    def preview_url_content(url, reader_type):
        try:
            st.session_state.preview_error = None
            if reader_type == "Jina AI Reader":
                # 使用Jina阅读器
                reader = JinaWebReader()
                documents = reader.load_data([url])
            else:
                # 使用BeautifulSoup阅读器
                reader = BeautifulSoupWebReader()
                documents = reader.load_data([url])

            if documents and len(documents) > 0:
                doc = documents[0]
                # 获取标题和内容
                title = doc.metadata.get("title", "Preview")
                content = doc.text

                # 更新session_state以显示预览
                st.session_state.preview_title = title
                st.session_state.preview_content = content
            else:
                st.session_state.preview_error = "无法从该URL提取内容。"
        except Exception as e:
            st.session_state.preview_error = f"预览失败: {str(e)}"
        finally:
            # 显示预览模态框
            st.session_state.show_preview = True

    if st.session_state["websites"] != []:
        st.markdown("### Added Websites")

        # 显示已添加的网站列表并提供删除、编辑标签和预览功能
        for idx, site_info in enumerate(st.session_state["websites"]):
            url = site_info["url"]
            name = site_info["name"] or url  # 如果没有自定义名称，显示URL
            current_tags = site_info.get("tags", [])

            st.markdown("---")
            st.subheader(name)
            st.caption(url)

            # 显示和编辑标签
            tags_str = ", ".join(current_tags) if current_tags else ""
            new_tags_str = st.text_input(
                "Tags", value=tags_str, placeholder="tag1, tag2", key=f"tags_{idx}"
            )

            # 如果标签输入有变化，更新标签
            if new_tags_str != tags_str:
                # 解析新标签，去除空格并过滤空标签
                new_tags = [
                    tag.strip() for tag in new_tags_str.split(",") if tag.strip()
                ]
                st.session_state["websites"][idx]["tags"] = new_tags

            # 添加操作按钮列
            col1, col2 = st.columns(2)
            with col1:
                # 添加预览按钮
                if st.button("👁️ Preview", key=f"preview_{idx}", help="预览URL内容"):
                    preview_url_content(url, reader_type)
            with col2:
                # 添加删除按钮
                if st.button(
                    "🗑️ Delete", key=f"delete_{idx}", help="Delete this website"
                ):
                    # 直接在回调中删除网站
                    del st.session_state["websites"][idx]
                    st.rerun()
        st.write("")

    process_button = st.button(
        "Save", key="process_website", disabled=len(st.session_state["websites"]) == 0
    )
    if process_button:
        print("Generating index...")
        with st.spinner(
            text="Loading documents and building the index, may take a minute or two"
        ):
            # 使用所选的读取器类型，并传递带自定义名称的网站列表
            if reader_type == "Jina AI Reader":
                st.session_state.index_manager.load_websites(
                    st.session_state["websites"],
                    chunk_size,
                    chunk_overlap,
                    reader_type="jina",
                )
            else:
                st.session_state.index_manager.load_websites(
                    st.session_state["websites"],
                    chunk_size,
                    chunk_overlap,
                    reader_type="beautifulsoup",
                )
            st.toast("✔️ Knowledge base index generation complete", icon="🎉")
            st.session_state.websites = []
            time.sleep(4)
        st.rerun()

    # 显示URL内容预览界面（使用自定义方式替代st.modal）
    if st.session_state.show_preview:
        # 添加一个特殊的容器来显示预览内容
        st.markdown("---")
        st.subheader("URL Content Preview")

        # 创建一个可折叠的容器来显示预览内容
        with st.container():
            if st.session_state.preview_error:
                st.error(st.session_state.preview_error)
            else:
                if st.session_state.preview_title:
                    st.markdown(f"### {st.session_state.preview_title}")
                if st.session_state.preview_content:
                    # 限制内容显示长度，避免过长的内容
                    max_content_length = 5000
                    if len(st.session_state.preview_content) > max_content_length:
                        st.text_area(
                            "Extracted Content",
                            value=st.session_state.preview_content[:max_content_length],
                            height=500,
                            disabled=True,
                        )
                        st.info(f"内容过长，仅显示前{max_content_length}个字符...")
                    else:
                        st.text_area(
                            "Extracted Content",
                            value=st.session_state.preview_content,
                            height=500,
                            disabled=True,
                        )

                    # 添加内容质量判断提示
                    content_length = len(st.session_state.preview_content.strip())
                    if content_length < 100:
                        st.warning(
                            "⚠️ 提取的内容较少，可能是无效内容或无法正确解析的网页。"
                        )
                    elif content_length > 10000:
                        st.info(
                            "ℹ️ 提取的内容较多，可能包含不必要的信息，建议检查是否需要全部入库。"
                        )
                else:
                    st.info("没有提取到内容。")

            # 关闭预览按钮
            if st.button("Close Preview", key="close_preview_button"):
                st.session_state.show_preview = False
                st.session_state.preview_content = None
                st.session_state.preview_title = None
                st.session_state.preview_error = None
                st.rerun()

        st.markdown("---")


handle_website()
