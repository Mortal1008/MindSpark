"""Beautiful Soup Web scraper."""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime

from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.core.readers.base import BasePydanticReader
from llama_index.core.schema import Document

logger = logging.getLogger(__name__)


def _mpweixin_reader(soup: Any, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """Extract text from Substack blog post."""
    meta_tag_title = soup.find("meta", attrs={"property": "og:title"})
    title = meta_tag_title["content"] if meta_tag_title else ""
    extra_info = {
        "title": title,
        # "Author": soup.select_one("span #js_author_name").getText(),
    }
    text = (
        soup.select_one("div #page-content").getText()
        if soup.select_one("div #page-content")
        else ""
    )
    return text, extra_info


def _baidu_baike_reader(soup: Any, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """Extract text from Baidu Baike page."""
    # 提取标题
    title = soup.select_one("h1#lemmaTitleH1")
    if not title:
        title = soup.select_one("title")
    title_text = title.get_text().strip() if title else ""

    # 提取内容
    content_div = soup.select_one("div.lemma-summary") or soup.select_one(
        "div.para-title"
    )
    text = ""

    if content_div:
        # 获取所有段落文本
        paragraphs = content_div.find_all(["p", "div"])
        text = "\n\n".join(
            [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
        )
    else:
        # 如果找不到特定的内容区域，尝试获取所有可能的内容
        content_elements = soup.select(
            "div.lemma-content, div.main-content, div.content"
        )
        if content_elements:
            text = "\n\n".join(
                [
                    elem.get_text().strip()
                    for elem in content_elements
                    if elem.get_text().strip()
                ]
            )

    # 清理文本
    text = "\n".join([line.strip() for line in text.split("\n") if line.strip()])

    extra_info = {"title": title_text, "source_type": "Baidu Baike"}

    return text, extra_info


DEFAULT_WEBSITE_EXTRACTOR: Dict[
    str, Callable[[Any, str], Tuple[str, Dict[str, Any]]]
] = {
    "mp.weixin.qq.com": _mpweixin_reader,
    "baike.baidu.com": _baidu_baike_reader,
}


class BeautifulSoupWebReader(BasePydanticReader):
    """BeautifulSoup web page reader.

    Reads pages from the web.
    Requires the `bs4` and `urllib` packages.

    Args:
        website_extractor (Optional[Dict[str, Callable]]): A mapping of website
            hostname (e.g. google.com) to a function that specifies how to
            extract text from the BeautifulSoup obj. See DEFAULT_WEBSITE_EXTRACTOR.
    """

    is_remote: bool = True
    _website_extractor: Dict[str, Callable] = PrivateAttr()

    def __init__(self, website_extractor: Optional[Dict[str, Callable]] = None) -> None:
        super().__init__()
        self._website_extractor = website_extractor or DEFAULT_WEBSITE_EXTRACTOR

    @classmethod
    def class_name(cls) -> str:
        """Get the name identifier of the class."""
        return "BeautifulSoupWebReader"

    def load_data(
        self,
        urls: List[str],
        custom_hostname: Optional[str] = None,
        include_url_in_text: Optional[bool] = True,
    ) -> List[Document]:
        """Load data from the urls.

        Args:
            urls (List[str]): List of URLs to scrape.
            custom_hostname (Optional[str]): Force a certain hostname in the case
                a website is displayed under custom URLs (e.g. Substack blogs)
            include_url_in_text (Optional[bool]): Include the reference url in the text of the document

        Returns:
            List[Document]: List of documents.

        """
        import requests
        from bs4 import BeautifulSoup

        # 添加模拟浏览器的请求头，避免被简单的反爬虫机制拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
        }

        documents = []
        for url in urls:
            try:
                # 使用包含请求头的GET请求
                page = requests.get(url, headers=headers, timeout=10)
                hostname = custom_hostname or urlparse(url).hostname or ""

                soup = BeautifulSoup(page.content, "html.parser")

                # 检测是否是百度安全验证页面
                page_text = soup.get_text().strip().lower()
                is_security_verify = any(
                    keyword in page_text
                    for keyword in [
                        "百度安全验证",
                        "安全验证",
                        "请拖动滑块",
                        "请完成安全验证",
                    ]
                )

                data = ""
                extra_info = {
                    "title": (
                        soup.select_one("title").get_text()
                        if soup.select_one("title")
                        else ""
                    ),
                    "url_source": url,
                    "creation_date": datetime.now()
                    .date()
                    .isoformat(),  # Convert datetime to ISO format string
                }

                # 如果检测到是安全验证页面，特殊处理
                if is_security_verify:
                    data = "⚠️ 无法直接获取内容：该网站需要安全验证\n\n提示：您可以尝试以下方法：\n1. 使用Jina AI Reader（如果可用）\n2. 手动打开网页复制内容\n3. 该网站可能有反爬虫机制"
                    extra_info["security_verification_required"] = True
                    extra_info["title"] = "需要安全验证 - " + (
                        extra_info["title"] or "无法访问的页面"
                    )
                else:
                    if hostname in self._website_extractor:
                        try:
                            data, metadata = self._website_extractor[hostname](
                                soup=soup,
                                url=url,
                                include_url_in_text=include_url_in_text,
                            )
                            extra_info.update(metadata)
                        except Exception as e:
                            logger.warning(
                                f"Special extractor for {hostname} failed: {e}"
                            )
                            # 如果特殊提取器失败，回退到通用提取器
                            data = self._extract_generic_content(soup)
                    else:
                        # 使用通用内容提取
                        data = self._extract_generic_content(soup)

                documents.append(Document(text=data, id_=url, extra_info=extra_info))
            except requests.RequestException as e:
                logger.error(f"Request error for {url}: {e}")
                data = f"⚠️ 请求失败：无法连接到该网站\n\n错误信息：{str(e)}"
                extra_info = {"title": "连接失败", "url_source": url, "error": str(e)}
                documents.append(Document(text=data, id_=url, extra_info=extra_info))
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                data = f"⚠️ 提取失败：无法从该网站获取内容\n\n错误信息：{str(e)}"
                extra_info = {"title": "提取失败", "url_source": url, "error": str(e)}
                documents.append(Document(text=data, id_=url, extra_info=extra_info))

        return documents

    def _extract_generic_content(self, soup: Any) -> str:
        """通用的内容提取方法，当没有特定网站提取器时使用。"""
        # 尝试智能提取主要内容
        # 1. 首先尝试提取常见的内容标签
        content_tags = [
            "article",
            "main",
            'div[class*="content"]',
            'div[class*="article"]',
            'div[id*="content"]',
            'div[id*="article"]',
        ]
        main_content = None

        for tag in content_tags:
            elements = soup.select(tag)
            if elements:
                # 选择文本最多的元素作为主要内容
                main_content = max(elements, key=lambda x: len(x.get_text(strip=True)))
                break

        # 2. 如果没有找到明显的内容标签，使用改进的方法提取文本
        if main_content:
            data = main_content.get_text(separator="\n", strip=True)
        else:
            # 移除常见的导航、广告、页脚等元素
            for element in soup.select(
                "nav, footer, header, aside, script, style, noscript, iframe, .ads, .advertisement, .banner, .sidebar"
            ):
                element.decompose()

            # 获取剩余文本，但保留段落结构
            paragraphs = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"])
            if paragraphs:
                # 只保留有一定长度的段落，过滤掉太短的文本碎片
                data = "\n\n".join(
                    [
                        p.get_text(strip=True)
                        for p in paragraphs
                        if len(p.get_text(strip=True)) > 20
                    ]
                )
            else:
                # 最后的备选方案：获取所有文本
                data = soup.get_text(separator="\n", strip=True)

        # 清理多余的空行
        data = "\n".join([line.strip() for line in data.split("\n") if line.strip()])

        # 如果提取的内容太短，说明可能没有提取到有效内容
        if len(data) < 50:
            data = "⚠️ 提取的内容较少或无法识别有效内容\n\n可能的原因：\n1. 网站结构复杂\n2. 内容为图片或非文本格式\n3. 网站有防爬虫措施"

        return data
