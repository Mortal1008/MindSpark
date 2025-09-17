import time
import pandas as pd
import streamlit as st
from server.utils.file import save_uploaded_file, get_save_dir
import uuid


# 移除直接执行函数的方式，改为在需要时调用
def handle_file():
    # 确保session_state中有必要的配置参数
    if "uploaded_files_with_tags" not in st.session_state:
        st.session_state.uploaded_files_with_tags = []

    st.header("Load Files")
    st.caption("Load Files like PDF, DOCX, TXT, etc. to create a knowledge base index.")

    # 第一步：上传文件
    with st.form("upload-form", clear_on_submit=True):
        uploaded_files = st.file_uploader(
            "Upload files: ", accept_multiple_files=True, label_visibility="hidden"
        )
        upload_button = st.form_submit_button(
            "Upload Files",
            help="Click here to upload the selected files.",
        )

        if len(uploaded_files) > 0 and upload_button:
            print("Starting to upload files...")
            print(uploaded_files)
            for file in uploaded_files:
                with st.spinner(f"Uploading {file.name}..."):
                    save_dir = get_save_dir()
                    save_uploaded_file(file, save_dir)
                    # 为每个文件创建一个唯一ID，以便后续编辑标签
                    file_id = str(uuid.uuid4())
                    st.session_state.uploaded_files_with_tags.append(
                        {
                            "id": file_id,
                            "name": file.name,
                            "type": file.type,
                            "size": file.size,
                            "tags": [],
                        }
                    )
            st.toast("✔️ Upload successful", icon="🎉")

    # 第二步：显示已上传的文件并允许添加/编辑标签
    if len(st.session_state.uploaded_files_with_tags) > 0:
        st.markdown("### Uploaded Files with Tags")

        # 为每个已上传的文件显示并允许编辑标签
        for idx, file_info in enumerate(st.session_state.uploaded_files_with_tags):
            st.markdown("---")
            st.subheader(file_info["name"])
            st.caption(f"Type: {file_info['type']}, Size: {file_info['size']} bytes")

            # 显示和编辑标签
            tags_str = ", ".join(file_info["tags"]) if file_info["tags"] else ""
            new_tags_str = st.text_input(
                "Tags",
                value=tags_str,
                placeholder="tag1, tag2",
                key=f"edit_tags_{file_info['id']}",
                help="不同标签用英文逗号分隔",
            )

            # 如果标签输入有变化，更新标签
            if new_tags_str != tags_str:
                # 解析新标签，去除空格并过滤空标签
                new_tags = [
                    tag.strip() for tag in new_tags_str.split(",") if tag.strip()
                ]
                st.session_state.uploaded_files_with_tags[idx]["tags"] = new_tags

            # 添加删除按钮
            if st.button(
                "🗑️ Delete",
                key=f"delete_file_{file_info['id']}",
                help="Delete this file",
            ):
                # 直接在回调中删除文件
                del st.session_state.uploaded_files_with_tags[idx]
                st.rerun()

    with st.expander(
        "Text Splitter Settings",
        expanded=True,
    ):
        cols = st.columns(2)
        chunk_size = cols[0].number_input(
            "Maximum length of a single text block: ",
            1,
            4096,
            st.session_state.chunk_size,
        )
        chunk_overlap = cols[1].number_input(
            "Adjacent text overlap length: ",
            0,
            st.session_state.chunk_size,
            st.session_state.chunk_overlap,
        )

    # 初始化uploaded_files，确保向后兼容
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []

    # 保存按钮 - 将文件和标签一起传递给后端
    if st.button(
        "Save",
        disabled=len(st.session_state.uploaded_files_with_tags) == 0,
        help="After uploading files and adding tags, click here to generate the index and save it to the knowledge base.",
    ):
        print("Generating index...")
        with st.spinner(
            text="Loading documents and building the index, may take a minute or two"
        ):
            # 更新uploaded_files以向后兼容
            st.session_state.uploaded_files = [
                {k: v for k, v in file.items() if k != "id" and k != "tags"}
                for file in st.session_state.uploaded_files_with_tags
            ]

            # 调用后端load_files方法，传入包含标签信息的文件列表
            st.session_state.index_manager.load_files(
                st.session_state.uploaded_files_with_tags, chunk_size, chunk_overlap
            )
            st.toast("✔️ Knowledge base index generation complete", icon="🎉")
            st.session_state.uploaded_files_with_tags = []
            st.session_state.uploaded_files = []
            time.sleep(4)
            st.rerun()


# 直接调用函数，确保Streamlit加载页面时显示内容
handle_file()
