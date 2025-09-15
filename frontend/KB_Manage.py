import os
import time
from math import ceil
import pandas as pd
import streamlit as st
import os


def get_unique_files_info(ref_doc_info):
    docs = []
    seen_paths = set()

    for ref_doc_id, ref_doc in ref_doc_info.items():

        metadata = ref_doc.metadata
        file_path = metadata.get("file_path", None)

        if file_path is None:
            title = metadata.get("title", None)
            url = metadata.get("url_source", None)
            docs.append(
                {
                    "id": ref_doc_id,
                    "name": title,
                    "type": "url",
                    "path": url,
                    "date": metadata["creation_date"],
                    "tags": metadata.get("tags", []),
                }
            )

        if file_path and file_path not in seen_paths:
            base_name, extension = os.path.splitext(metadata["file_name"])
            # Remove the leading dot from the extension
            extension = extension.lstrip(".")

            file_info = {
                "id": ref_doc_id,
                "name": base_name,
                "type": extension,
                "path": file_path,
                #'file_size': metadata['file_size'],
                "date": metadata["creation_date"],
                "tags": metadata.get("tags", []),
            }
            docs.append(file_info)
            seen_paths.add(file_path)

    return docs


def handle_knowledgebase():
    st.header("Manage Knowledge Base")
    st.caption("Manage documents and web urls in your knowledge base.")

    from server.stores.strage_context import STORAGE_CONTEXT

    doc_store = STORAGE_CONTEXT.docstore

    try:
        # 直接尝试获取所有引用文档信息，不依赖doc_store.docs属性
        # 这对RedisDocumentStore等生产环境中的存储更兼容
        ref_doc_info = doc_store.get_all_ref_doc_info()

        # 检查是否有文档
        if not ref_doc_info:
            st.write("Knowledge base is empty")
            return  # 提前返回，避免后续处理

        # 处理文档列表
        unique_files = get_unique_files_info(ref_doc_info)
        st.write("You have total", len(unique_files), "documents.")
        df = pd.DataFrame(unique_files)
    except Exception as e:
        print(f"Error getting document info: {e}")
        st.error("Failed to load document information. Please try again.")
        st.write("Knowledge base is empty")
        return  # 提前返回，避免后续处理

    # 获取所有唯一标签用于搜索
    all_tags = set()
    for _, row in df.iterrows():
        tags = row["tags"]
        if isinstance(tags, list):
            all_tags.update(tags)
        elif isinstance(tags, str) and tags:
            all_tags.update([tag.strip() for tag in tags.split(",") if tag.strip()])

    # 添加高级搜索功能
    st.subheader("Search")

    # 创建搜索条件区域
    with st.expander("Search Criteria", expanded=True):
        # 初始化搜索条件会话状态
        if "search_conditions" not in st.session_state:
            st.session_state.search_conditions = [
                {"logic": "AND", "field": "tags", "value": "", "id": 0}
            ]
            st.session_state.next_condition_id = 1

        # 获取所有唯一的文档类型
        all_types = set(df["type"].unique())

        # 定义可搜索字段
        search_fields = {"tags": "标签", "type": "文档类型", "name": "文档名称"}

        # 显示搜索条件
        # 显示搜索条件
        for i, condition in enumerate(st.session_state.search_conditions):
            # 统一使用相同的列布局，确保所有行对齐
            cols = st.columns([1, 2, 4, 1])

            # 逻辑运算符选择器 - 仅在非第一行显示
            if i != 0:
                condition["logic"] = cols[0].selectbox(
                    "Logic",
                    options=["AND", "OR", "NOT"],
                    index=["AND", "OR", "NOT"].index(condition["logic"]),
                    key=f"logic_{condition['id']}",
                    help="选择逻辑运算符",
                )

            # 字段选择器
            condition["field"] = cols[1].selectbox(
                "Field",
                options=list(search_fields.keys()),
                format_func=lambda x: search_fields[x],
                key=f"field_{condition['id']}",
                help="选择要搜索的字段",
            )

            # 值输入框
            if condition["field"] == "type":
                condition["value"] = cols[2].selectbox(
                    "Document Type",
                    options=[""] + sorted(all_types),
                    index=(
                        0
                        if condition["value"] == ""
                        else (
                            sorted(all_types).index(condition["value"]) + 1
                            if condition["value"] in all_types
                            else 0
                        )
                    ),
                    key=f"value_{condition['id']}",
                    help="选择文档类型",
                )
            elif condition["field"] == "tags":
                condition["value"] = cols[2].selectbox(
                    "Tags",
                    options=[""] + sorted(all_tags),
                    index=(
                        0
                        if condition["value"] == ""
                        else (
                            sorted(all_tags).index(condition["value"]) + 1
                            if condition["value"] in all_tags
                            else 0
                        )
                    ),
                    key=f"value_{condition['id']}",
                    help="选择标签",
                )
            else:
                condition["value"] = cols[2].text_input(
                    "Search Text",
                    value=condition["value"],
                    key=f"value_{condition['id']}",
                    label_visibility="collapsed",
                )

            # 删除按钮 - 仅在非第一行显示垃圾桶图标，并垂直居中
            if i != 0:
                with cols[3]:
                    # 添加删除文本标签
                    st.markdown(
                        "<div style='font-size: 14px; margin-bottom: 5px;'>DEL</div>",
                        unsafe_allow_html=True,
                    )

                    # 添加删除按钮
                    if st.button("🗑️", key=f"remove_{condition['id']}", help="删除条件"):
                        st.session_state.search_conditions = [
                            c
                            for c in st.session_state.search_conditions
                            if c["id"] != condition["id"]
                        ]
                        st.rerun()

        # 添加新条件按钮
        if st.button("+ Add Search Condition"):
            st.session_state.search_conditions.append(
                {
                    "logic": "AND",
                    "field": "tags",
                    "value": "",
                    "id": st.session_state.next_condition_id,
                }
            )
            st.session_state.next_condition_id += 1
            st.rerun()

    # 根据搜索条件过滤文档
    filtered_docs = []
    has_active_conditions = False

    # 检查是否有有效的搜索条件
    for condition in st.session_state.search_conditions:
        if condition["value"] != "":
            has_active_conditions = True
            break

    if has_active_conditions:
        # 遍历所有文档
        for _, row in df.iterrows():
            # 文档是否匹配所有条件
            doc_matches = True

            # 跟踪是否已经处理了至少一个非空条件
            has_processed_condition = False

            # 遍历所有搜索条件
            for i, condition in enumerate(st.session_state.search_conditions):
                # 跳过空值条件
                if condition["value"] == "":
                    continue

                # 根据字段类型检查条件是否匹配
                match = False

                if condition["field"] == "type":
                    match = row["type"] == condition["value"]
                elif condition["field"] == "tags":
                    doc_tags = row["tags"]
                    if isinstance(doc_tags, list):
                        tags_list = doc_tags
                    elif isinstance(doc_tags, str):
                        tags_list = [
                            tag.strip() for tag in doc_tags.split(",") if tag.strip()
                        ]
                    else:
                        tags_list = []
                    match = condition["value"] in tags_list
                elif condition["field"] == "name":
                    match = condition["value"].lower() in str(row["name"]).lower()

                # 应用逻辑运算符
                if not has_processed_condition:
                    # 第一个非空条件直接设置结果
                    doc_matches = match
                    has_processed_condition = True
                else:
                    # 后续条件应用逻辑运算符
                    # 对于非第一行的条件，使用其指定的逻辑运算符
                    if condition["logic"] == "AND":
                        doc_matches = doc_matches and match
                    elif condition["logic"] == "OR":
                        doc_matches = doc_matches or match
                    elif condition["logic"] == "NOT":
                        doc_matches = doc_matches and not match

            # 如果文档匹配所有条件，添加到结果列表
            if doc_matches:
                filtered_docs.append(row)

        df = pd.DataFrame(filtered_docs)
        st.write(f"Found {len(df)} documents matching search criteria.")

    # 确保tags列存在并转换为字符串格式以便显示
    if "tags" not in df.columns:
        df["tags"] = ""
    else:
        df["tags"] = df["tags"].apply(
            lambda x: (
                ", ".join(x) if isinstance(x, list) and x else (str(x) if x else "")
            )
        )

    # Pagination settings

    page_size = 12
    total_pages = ceil(len(df) / page_size)

    if "curr_page" not in st.session_state.keys():
        st.session_state.curr_page = 1

    curr_page = min(st.session_state["curr_page"], total_pages)

    # Displaying pagination buttons
    if total_pages > 1:
        prev, next, _, col3 = st.columns([1, 1, 6, 2])

        if next.button("Next"):
            curr_page = min(curr_page + 1, total_pages)
            st.session_state["curr_page"] = curr_page

        if prev.button("Prev"):
            curr_page = max(curr_page - 1, 1)
            st.session_state["curr_page"] = curr_page

        with col3:
            st.write("Page: ", curr_page, "/", total_pages)

    start_index = (curr_page - 1) * page_size
    end_index = curr_page * page_size
    df_paginated = df.iloc[start_index:end_index]

    # 创建一个DataFrame副本，用于显示
    df_display = df_paginated.copy()

    # 添加调试信息，帮助确认DataFrame确实包含数据
    if not df_display.empty:
        st.write(f"显示第 {curr_page} 页，共 {len(df_display)} 个文档")
    else:
        st.info("当前页没有文档")

    # 使用data_editor实现双击编辑标签功能
    if not df_display.empty:
        # 选择要显示的列
        display_columns = ["name", "type", "date", "tags"]
        display_df = df_display[display_columns].copy()

        # 确保标签列显示为字符串
        display_df["tags"] = display_df["tags"].apply(
            lambda x: (
                ", ".join(x) if isinstance(x, list) and x else (str(x) if x else "")
            )
        )

        # 存储原始文档ID与显示行的映射
        doc_id_map = {idx: doc["id"] for idx, doc in df_display.iterrows()}

        # 创建可编辑的数据表格
        edited_df = st.data_editor(
            display_df,
            width=800,
            column_config={
                "name": st.column_config.TextColumn("Name", width=300, disabled=True),
                "type": st.column_config.TextColumn("Type", width=100, disabled=True),
                "date": st.column_config.TextColumn(
                    "Creation Date", width=150, disabled=True
                ),
                "tags": st.column_config.TextColumn("Tags", width=250),
            },
            hide_index=True,
            use_container_width=True,
            key="doc_editor",
        )

        # 检查是否有编辑并更新标签
        if st.session_state.get("doc_editor", None) is not None:
            # 获取编辑的单元格信息
            edited_cells = st.session_state.doc_editor.get("edited_cells", {})
            if edited_cells:
                # 获取文档ID到原始索引的映射
                id_to_original_idx = {
                    doc["id"]: idx for idx, doc in df_display.iterrows()
                }

                # 遍历所有编辑的单元格
                for row_idx, col_dict in edited_cells.items():
                    if "tags" in col_dict:
                        # 获取原始文档索引
                        original_idx = int(row_idx)
                        doc_id = doc_id_map[original_idx]

                        # 获取更新后的标签
                        new_tags = edited_df.iloc[original_idx]["tags"]

                        # 处理标签格式
                        tags_list = [
                            tag.strip() for tag in new_tags.split(",") if tag.strip()
                        ]
                        tags_str = ", ".join(tags_list)

                        try:
                            # 获取原始文档引用信息
                            ref_doc = ref_doc_info[doc_id]

                            # 更新文档元数据中的标签
                            if hasattr(ref_doc, "metadata") and isinstance(
                                ref_doc.metadata, dict
                            ):
                                ref_doc.metadata["tags"] = tags_str

                                # 更新文档存储
                                doc_store.set_ref_doc_info({doc_id: ref_doc})

                                # 持久化存储上下文
                                STORAGE_CONTEXT.persist()

                                st.toast(f"✔️ 标签已更新: {tags_str}", icon="🎉")
                        except Exception as e:
                            print(f"Error updating tags for document {doc_id}: {e}")
                            st.error(f"更新标签失败，请重试。")

        # 保留删除功能所需的doc_options创建
        doc_options = {
            f"{doc['name']} ({doc['type']})": doc["id"]
            for _, doc in df_display.iterrows()
        }
    else:
        doc_options = {}

    # 显示删除按钮区域

    # 添加会话状态变量来存储当前选中的文档ID
    if "selected_doc_id" not in st.session_state:
        st.session_state.selected_doc_id = None

    # 显示删除按钮区域
    st.markdown("### Delete Document")

    # 使用之前创建的doc_options变量，不需要重新创建

    if doc_options:
        selected_doc_name = st.selectbox(
            "Select a document to delete:",
            options=list(doc_options.keys()),
            help="Select a document to delete",
        )

        if selected_doc_name:
            selected_doc_id = doc_options[selected_doc_name]

            # 删除确认对话框
            if st.button(
                "🗑️ Delete Selected Document", type="primary", key="delete_selected"
            ):
                with st.spinner(text="Deleting document and related index..."):
                    st.session_state.index_manager.delete_ref_doc(selected_doc_id)
                    st.toast(
                        f'✔️ Deleted document: {selected_doc_name.split(" (")[0]}',
                        icon="🎉",
                    )
                    time.sleep(2)
                    st.rerun()
    else:
        st.info("No documents to delete on this page.")

    # 标签编辑功能已通过data_editor实现
    # 以下是旧的编辑功能代码，已被内联编辑功能取代
    st.caption(
        "💡 You can double-click on any tag cell to edit it directly in the table above."
    )
    st.caption("💡 不同标签用英文逗号分隔")


handle_knowledgebase()
