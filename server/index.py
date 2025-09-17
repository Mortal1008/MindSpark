# Index management - create, load and insert
import os
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core import load_index_from_storage, load_indices_from_storage
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from server.utils.file import get_save_dir
from server.stores.strage_context import STORAGE_CONTEXT
from server.ingestion import AdvancedIngestionPipeline
from config import DEV_MODE


class IndexManager:
    def __init__(self, index_name):
        self.index_name: str = index_name
        self.storage_context: StorageContext = STORAGE_CONTEXT
        self.index_id: str = None
        self.index: VectorStoreIndex = None

    def check_index_exists(self):
        indices = load_indices_from_storage(self.storage_context)
        print(f"Loaded {len(indices)} indices")
        if len(indices) > 0:
            self.index = indices[0]
            self.index_id = indices[0].index_id
            return True
        else:
            return False

    def init_index(self, nodes):
        self.index = VectorStoreIndex(
            nodes, storage_context=self.storage_context, store_nodes_override=True
        )  # note: no nodes in doc store if using vector database, set store_nodes_override=True to add nodes to doc store
        self.index_id = self.index.index_id
        # 无论开发模式还是生产模式，都持久化存储上下文，确保文档正确保存
        self.storage_context.persist()
        print(f"Created index {self.index.index_id}")
        return self.index

    def load_index(self):  # Load index from storage, using index_id if available
        # If index is already loaded (e.g., from check_index_exists), no need to reload
        if self.index is not None:
            print(f"Index {self.index.index_id} already loaded")
            return self.index

        # If we have a stored index_id, use it for loading
        if self.index_id is not None:
            self.index = load_index_from_storage(
                self.storage_context, index_id=self.index_id
            )
        else:
            # Fallback to loading without index_id (for backward compatibility)
            try:
                self.index = load_index_from_storage(self.storage_context)
            except ValueError as e:
                # If loading fails, try to check if indices exist first
                indices = load_indices_from_storage(self.storage_context)
                if len(indices) > 0:
                    self.index = indices[0]
                    self.index_id = indices[0].index_id
                else:
                    raise ValueError(
                        "No indices found in storage context. Please create an index first."
                    ) from e

        if not DEV_MODE:
            self.index._store_nodes_override = True
        print(f"Loaded index {self.index.index_id}")
        return self.index

    def insert_nodes(self, nodes):
        if self.index is not None:
            self.index.insert_nodes(nodes=nodes)
            # 无论开发模式还是生产模式，都持久化存储上下文，确保文档正确保存
            self.storage_context.persist()
            print(f"Inserted {len(nodes)} nodes into index {self.index.index_id}")
        else:
            self.init_index(nodes=nodes)
        return self.index

    # Build index based on documents under 'data' folder
    def load_dir(self, input_dir, chunk_size, chunk_overlap):
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap
        documents = SimpleDirectoryReader(
            input_dir=input_dir, recursive=True
        ).load_data()
        if len(documents) > 0:
            pipeline = AdvancedIngestionPipeline()
            nodes = pipeline.run(documents=documents)
            index = self.insert_nodes(nodes)
            return nodes
        else:
            print("No documents found")
            return []

    # get file's directory and create index
    def load_files(self, uploaded_files, chunk_size, chunk_overlap):
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap
        save_dir = get_save_dir()

        # 创建文件路径和标签的映射
        file_tags = {}
        files = []

        for file_info in uploaded_files:
            file_path = os.path.join(save_dir, file_info["name"])
            files.append(file_path)
            # 存储文件的标签信息
            tags = file_info.get("tags", [])
            if tags:
                file_tags[file_info["name"]] = tags

        print(files)
        documents = SimpleDirectoryReader(input_files=files).load_data()

        # 将标签应用到对应的文档元数据
        for doc in documents:
            file_name = doc.metadata.get("file_name")
            if file_name in file_tags:
                tags = file_tags[file_name]
                # 将tags列表转换为逗号分隔的字符串，因为Chroma要求metadata值必须是简单类型
                tags_str = ", ".join(tags) if tags else ""
                if hasattr(doc, "extra_info") and isinstance(doc.extra_info, dict):
                    doc.extra_info["tags"] = tags_str
                elif hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                    doc.metadata["tags"] = tags_str

        if len(documents) > 0:
            pipeline = AdvancedIngestionPipeline()
            nodes = pipeline.run(documents=documents)
            index = self.insert_nodes(nodes)
            return nodes
        else:
            print("No documents found")
            return []

    # Get URL and create index
    # https://docs.llamaindex.ai/en/stable/examples/data_connectors/WebPageDemo/
    def load_websites(
        self, websites, chunk_size, chunk_overlap, reader_type="beautifulsoup"
    ):
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

        # 提取URL列表，保留自定义名称和标签的映射关系
        url_list = []
        custom_names = {}
        url_tags = {}

        for website in websites:
            # 检查website是字典（带自定义名称）还是字符串
            if isinstance(website, dict):
                url = website.get("url")
                custom_name = website.get("name")
                if url:
                    url_list.append(url)
                    if custom_name:
                        custom_names[url] = custom_name
                    # 存储标签信息
                    tags = website.get("tags", [])
                    if tags:
                        url_tags[url] = tags
            else:
                # 如果是字符串，直接添加到URL列表
                url_list.append(website)

        if reader_type == "jina":
            from server.readers.jina_web import JinaWebReader

            try:
                documents = JinaWebReader().load_data(url_list)
            except Exception as e:
                print(f"Jina web reader failed: {e}")
                # Fallback to BeautifulSoup if Jina fails
                from server.readers.beautiful_soup_web import BeautifulSoupWebReader

                documents = BeautifulSoupWebReader().load_data(url_list)
        else:
            from server.readers.beautiful_soup_web import BeautifulSoupWebReader

            documents = BeautifulSoupWebReader().load_data(url_list)

        # 将自定义名称和标签应用到对应的文档元数据
        for doc in documents:
            url = doc.id_

            # 更新自定义名称
            if url in custom_names:
                # 更新文档的元数据中的标题
                if hasattr(doc, "extra_info") and isinstance(doc.extra_info, dict):
                    doc.extra_info["title"] = custom_names[url]
                    doc.extra_info["custom_name"] = custom_names[url]  # 另外存储一份
                elif hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                    doc.metadata["title"] = custom_names[url]
                    doc.metadata["custom_name"] = custom_names[url]  # 另外存储一份

            # 更新标签
            if url in url_tags:
                tags = url_tags[url]
                # 将标签列表转换为逗号分隔的字符串，以兼容Chroma向量存储
                # Chroma要求metadata值必须是简单类型（str, int, float, None）
                tags_str = ", ".join(tags) if tags else ""
                if hasattr(doc, "extra_info") and isinstance(doc.extra_info, dict):
                    doc.extra_info["tags"] = tags_str
                elif hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                    doc.metadata["tags"] = tags_str

        if len(documents) > 0:
            pipeline = AdvancedIngestionPipeline()
            nodes = pipeline.run(documents=documents)
            index = self.insert_nodes(nodes)
            return nodes
        else:
            print("No documents found")
            return []

    # Delete a document and all related nodes
    def delete_ref_doc(self, ref_doc_id):
        # 首先检查文档是否真的存在于doc_store中
        ref_doc_info = self.storage_context.docstore.get_all_ref_doc_info()
        if ref_doc_id not in ref_doc_info:
            raise ValueError(
                f"Document with ID {ref_doc_id} does not exist or has already been deleted."
            )

        try:
            # 检查index是否已初始化，如果没有则尝试加载
            if self.index is None:
                try:
                    self.load_index()
                except Exception as e:
                    print(f"Failed to load index: {e}")
                    # 索引加载失败，但我们仍然尝试直接从doc_store删除文档

            if self.index is not None:
                # 尝试通过索引删除文档（推荐方式）
                self.index.delete_ref_doc(
                    ref_doc_id=ref_doc_id, delete_from_docstore=True
                )
                print(f"Deleted document {ref_doc_id} through index")
            else:
                # 如果索引仍然不可用，尝试直接从doc_store删除文档
                print(
                    "Index is not available, attempting to delete directly from doc_store"
                )
                # 1. 获取文档的所有节点ID
                doc_info = ref_doc_info[ref_doc_id]
                node_ids = doc_info.node_ids

                # 2. 从vector_store中删除节点
                if (
                    hasattr(self.storage_context, "vector_store")
                    and self.storage_context.vector_store is not None
                ):
                    try:
                        self.storage_context.vector_store.delete(node_ids)
                        print(f"Deleted {len(node_ids)} nodes from vector_store")
                    except Exception as vs_e:
                        print(
                            f"Warning: Failed to delete nodes from vector_store: {vs_e}"
                        )

                # 3. 从doc_store中删除引用文档信息
                self.storage_context.docstore.delete_ref_doc(ref_doc_id)
                print(f"Deleted reference document {ref_doc_id} from doc_store")

                # 4. 从doc_store中删除关联的节点文档
                for node_id in node_ids:
                    try:
                        self.storage_context.docstore.delete_document(node_id)
                    except Exception as node_e:
                        print(f"Warning: Failed to delete node {node_id}: {node_e}")

            # 无论哪种方式，都持久化存储上下文
            self.storage_context.persist()
            print(f"Successfully deleted document {ref_doc_id} and persisted changes")

        except KeyError as e:
            # 处理文档ID不存在的情况
            print(f"Document with ID {ref_doc_id} not found. Error: {e}")
            raise ValueError(
                f"Document with ID {ref_doc_id} does not exist or has already been deleted."
            ) from e
        except Exception as e:
            # 处理其他可能的异常
            print(f"Error deleting document {ref_doc_id}: {e}")
            raise RuntimeError(f"Failed to delete document {ref_doc_id}") from e
