# Chinese title enhance
# Source：LangchainChatChat, QAnything

from llama_index.core.schema import BaseNode
from llama_index.core.schema import TransformComponent
from typing import List, Optional
import re


def under_non_alpha_ratio(text: str, threshold: float = 0.5) -> bool:
    """Checks if the proportion of non-alpha characters in the text snippet exceeds a given
    threshold. This helps prevent text like "-----------BREAK---------" from being tagged
    as a title or narrative text. The ratio does not count spaces.

    Parameters
    ----------
    text
        The input string to test
    threshold
        If the proportion of non-alpha characters exceeds this threshold, the function
        returns False
    """
    if not text.strip():
        return False

    # Count non-space characters
    total_count = len([char for char in text if char.strip()])
    if total_count == 0:
        return False

    # Count alphabetic characters (including Chinese characters)
    alpha_count = len([char for char in text if char.strip() and (char.isalpha() or '\u4e00' <= char <= '\u9fff')])
    
    ratio = alpha_count / total_count
    return ratio < threshold


def is_possible_title(
        text: str,
        title_max_word_length: int = 20,
        non_alpha_threshold: float = 0.5,
) -> bool:
    """Checks to see if the text passes all of the checks for a valid title.

    Parameters
    ----------
    text
        The input text to check
    title_max_word_length
        The maximum number of words a title can contain
    non_alpha_threshold
        The minimum number of alpha characters the text needs to be considered a title
    """

    # If the text length is zero, it is not a title
    if not text.strip():
        return False

    # If the text ends with punctuation, it is not a title
    ENDS_IN_PUNCT_PATTERN = r"[^\w\s]\Z"
    ENDS_IN_PUNCT_RE = re.compile(ENDS_IN_PUNCT_PATTERN)
    if ENDS_IN_PUNCT_RE.search(text) is not None:
        return False

    # Check if text ends with common Chinese/English punctuation
    PUNCTUATION_PATTERN = r"[,\.，。：:；;!！?？》〉】\]\)）]\Z"
    if re.search(PUNCTUATION_PATTERN, text):
        return False

    # The text should not be too long (split by spaces for efficiency)
    words = text.split()
    if len(words) > title_max_word_length:
        return False

    # The ratio of non-alpha characters should not be too high
    if under_non_alpha_ratio(text, threshold=non_alpha_threshold):
        return False

    # Prevent flagging salutations or purely numeric text as titles
    if text.endswith((",", ".", "，", "。", "：", ":")):
        return False

    if text.isnumeric():
        return False

    # Check if the text has meaningful content (not just symbols or numbers)
    # Remove common title markers like "第X章" etc. for content check
    content_text = re.sub(r'第[零一二三四五六七八九十百千万\d]+[章节条]', '', text)
    if not content_text.strip():
        return False

    # Additional checks for Chinese titles
    # Chinese titles often contain specific patterns
    chinese_title_patterns = [
        r'^第[零一二三四五六七八九十百千万\d]+[章节条]',  # 第一章, 第一节等
        r'^[一二三四五六七八九十]、',  # 一、标题
        r'^\(\d+\)',  # (1) 标题
        r'^\d+[\.\、]',  # 1.标题 或 1、标题
        r'^[①②③④⑤⑥⑦⑧⑨⑩]',  # 带圈数字
    ]

    # If matches common Chinese title patterns, more likely to be a title
    for pattern in chinese_title_patterns:
        if re.match(pattern, text.strip()):
            return True

    # For other text, require it to be relatively short and meaningful
    if len(text.strip()) <= 50:  # Reasonable length for a title
        # Check if it contains meaningful text (not just symbols)
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        has_alpha = any(char.isalpha() for char in text)
        if has_chinese or has_alpha:
            return True

    return False


def zh_title_enhance(docs: List[BaseNode]) -> List[BaseNode]:
    """Enhance Chinese documents by identifying titles and adding context."""
    if not docs:
        print("文件不存在")
        return []

    title: Optional[str] = None
    enhanced_docs: List[BaseNode] = []
    
    for doc in docs:
        current_text = getattr(doc, 'text', '') or getattr(doc, 'page_content', '')
        
        if not current_text:
            enhanced_docs.append(doc)
            continue
            
        if is_possible_title(current_text):
            # Set metadata and update current title
            if hasattr(doc, 'metadata'):
                doc.metadata['category'] = 'cn_Title'
            title = current_text
            enhanced_docs.append(doc)
        elif title:
            # Enhance non-title documents with title context
            enhanced_text = f"下文与({title})有关。{current_text}"
            if hasattr(doc, 'text'):
                doc.text = enhanced_text
            elif hasattr(doc, 'page_content'):
                doc.page_content = enhanced_text
            enhanced_docs.append(doc)
        else:
            enhanced_docs.append(doc)
    
    return enhanced_docs


class ChineseTitleExtractor(TransformComponent):
    """LlamaIndex transform component for Chinese title extraction and enhancement."""
    
    def __call__(self, nodes, **kwargs):
        """Process nodes to enhance Chinese titles."""
        return zh_title_enhance(nodes)