"""
PubMed 客户端 (PubMedClient)。

封装 NCBI E-utilities API (esearch + esummary)，提供 PubMed 文献检索与详情获取。
自动处理频率限制（每秒 ≤3 次请求），内置缓存与重试机制。
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp
from loguru import logger

from src.config import get_config


# ── 缓存条目 ──────────────────────────────────

@dataclass
class CacheEntry:
    """缓存条目，带过期时间。"""
    data: Any
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


# ── 速率限制器 ────────────────────────────────

class RateLimiter:
    """简单令牌桶速率限制器。

    确保 API 请求不超过 NCBI 的限制（每秒 3 次）。
    """

    def __init__(self, max_per_second: int = 3) -> None:
        self._max_per_second = max_per_second
        self._tokens = max_per_second
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """等待直到获得一个请求令牌。"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._max_per_second,
                self._tokens + elapsed * self._max_per_second,
            )
            self._last_refill = now

            if self._tokens < 1:
                wait = (1 - self._tokens) / self._max_per_second
                logger.debug(f"[速率限制] 等待 {wait:.2f}s")
                await asyncio.sleep(wait)
                self._tokens = 1

            self._tokens -= 1


# ── PubMed 客户端 ─────────────────────────────

class PubMedClient:
    """PubMed 文献检索客户端。

    基于 NCBI E-utilities API，支持文献搜索、详情获取。
    内置缓存、速率限制和重试机制。

    Attributes:
        email: 请求邮箱（NCBI 要求）
        tool: 工具名称
        base_url: E-utilities API 基础 URL
        max_retries: 最大重试次数
        timeout: HTTP 请求超时（秒）
        rate_limiter: 速率限制器（默认 3 次/秒）
        cache_ttl: 缓存有效期（秒，默认 600）
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        email: str | None = None,
        tool: str = "BioResearch-Agent",
        max_retries: int | None = None,
        timeout: int | None = None,
        cache_ttl: int = 600,
        proxy: str | None = None,
    ) -> None:
        config = get_config()

        self.email: str = email or config.pubmed_email or "research@example.com"
        self.tool: str = tool
        self.max_retries: int = max_retries if max_retries is not None else config.max_retries
        self.timeout: int = timeout if timeout is not None else config.request_timeout
        self.cache_ttl: int = cache_ttl
        self.proxy: str | None = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        # 速率限制器：NCBI 限制 3 次/秒（无 API Key），10 次/秒（有 API Key）
        self._rate_limiter = RateLimiter(max_per_second=10 if _has_api_key() else 3)

        # 内存缓存: key -> CacheEntry
        self._cache: dict[str, CacheEntry] = {}

        logger.info(
            f"PubMedClient 初始化完成, email={self.email}, "
            f"timeout={self.timeout}s, cache_ttl={self.cache_ttl}s"
            + (f", proxy={self.proxy}" if self.proxy else "")
        )

    # ── 公开方法 ──────────────────────────────

    async def search(
        self,
        query: str,
        max_results: int = 50,
        sort: str = "relevance",
        min_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """在 PubMed 中搜索文献。

        Args:
            query: 检索关键词（支持布尔运算符 AND / OR / NOT）
            max_results: 最大返回结果数（默认 50，上限 10000）
            sort: 排序方式 ("relevance" 或 "date")
            min_year: 最小发表年份过滤

        Returns:
            符合 LiteratureResult 模型的文献字典列表

        Examples:
            >>> client = PubMedClient()
            >>> results = await client.search("breast cancer TP53", max_results=10)
            >>> len(results) > 0
            True
            >>> results[0]["pmid"]
            '...'
        """
        if not query or not query.strip():
            logger.warning("[PubMed] 空查询，返回空列表")
            return []

        max_results = max(1, min(max_results, 10000))
        cache_key = f"search:{query}:{max_results}:{sort}:{min_year}"

        # 检查缓存
        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.info(f"[PubMed] 缓存命中: {query[:50]}...")
            return cached

        logger.info(f"[PubMed] 搜索: {query[:80]}... (max={max_results})")

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": sort,
            "email": self.email,
            "tool": self.tool,
        }
        if min_year:
            params["mindate"] = str(min_year)
            params["datetype"] = "pdat"

        for attempt in range(1, self.max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                data = await self._request("GET", self.ESEARCH_URL, params=params)

                id_list: list[str] = (
                    data.get("esearchresult", {}).get("idlist", [])
                )
                logger.info(f"[PubMed] 搜索到 {len(id_list)} 篇文献")

                if not id_list:
                    self._set_cache(cache_key, [])
                    return []

                # 分批获取详情（esummary 每次最多 200 个 ID）
                chunk_size = 200
                all_articles: list[dict[str, Any]] = []

                for i in range(0, len(id_list), chunk_size):
                    chunk = id_list[i : i + chunk_size]
                    chunk_results = await self.fetch_details(chunk)
                    all_articles.extend(chunk_results)

                self._set_cache(cache_key, all_articles)
                return all_articles

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[PubMed] 搜索失败 (尝试 {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error(f"[PubMed] 搜索重试耗尽")
                    return []

    async def fetch_details(self, pmids: list[str]) -> list[dict[str, Any]]:
        """根据 PMID 列表获取文献详细信息。

        Args:
            pmids: PubMed ID 列表

        Returns:
            符合 LiteratureResult 模型的文献字典列表
        """
        if not pmids:
            return []

        # 去重
        pmids = list(dict.fromkeys(pmids))
        cache_key = f"details:{','.join(sorted(pmids))}"

        # 检查缓存
        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.debug(f"[PubMed] 详情缓存命中: {len(pmids)} 篇")
            return cached

        logger.debug(f"[PubMed] 获取详情: {len(pmids)} 篇文献")

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "email": self.email,
            "tool": self.tool,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                data = await self._request("GET", self.ESUMMARY_URL, params=params)

                result = data.get("result", {})
                uids = result.get("uids", [])

                articles: list[dict[str, Any]] = []
                for uid in uids:
                    article_data = result.get(uid, {})
                    article = self._parse_esummary(article_data)
                    if article:
                        articles.append(article)

                self._set_cache(cache_key, articles)
                logger.debug(f"[PubMed] 详情获取成功: {len(articles)} 篇")
                return articles

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[PubMed] 详情获取失败 (尝试 {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error(f"[PubMed] 详情获取重试耗尽")
                    return []

    async def fetch_abstracts(self, pmids: list[str]) -> list[dict[str, Any]]:
        """通过 efetch XML 获取文献完整摘要。

        esummary 不返回摘要，efetch 返回完整的 PubMed XML，
        从中提取 AbstractText。

        Args:
            pmids: PubMed ID 列表（每次建议不超过 50 个）

        Returns:
            包含完整摘要的文献字典列表
        """
        if not pmids:
            return []

        pmids = list(dict.fromkeys(pmids))
        cache_key = f"abstracts:{','.join(sorted(pmids[:10]))}"

        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.debug(f"[PubMed] 摘要缓存命中: {len(pmids)} 篇")
            return cached

        logger.info(f"[PubMed] 获取摘要: {len(pmids)} 篇文献")

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self.email,
            "tool": self.tool,
        }
        # 如果超过上限，分批请求
        chunk_size = 50
        all_articles: list[dict[str, Any]] = []

        for i in range(0, len(pmids), chunk_size):
            chunk = pmids[i : i + chunk_size]
            params["id"] = ",".join(chunk)

            for attempt in range(1, self.max_retries + 1):
                try:
                    await self._rate_limiter.acquire()
                    raw_xml = await self._request_xml("GET", self.EFETCH_URL, params=params)
                    articles = self._parse_efetch_xml(raw_xml)
                    all_articles.extend(articles)
                    break
                except (aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError) as e:
                    logger.warning(f"[PubMed] 摘要获取失败 (尝试 {attempt}): {e}")
                    if attempt >= self.max_retries:
                        logger.error(f"[PubMed] 摘要获取重试耗尽")
                    else:
                        await asyncio.sleep(2**attempt)

        self._set_cache(cache_key, all_articles)
        logger.info(f"[PubMed] 摘要获取完成: {len(all_articles)} 篇")
        return all_articles

    async def _request_xml(
        self, method: str, url: str, params: dict[str, str] | None = None,
    ) -> str:
        """发送 HTTP 请求并返回 XML 文本。"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=aiohttp.TCPConnector(ssl=False),
            headers={"User-Agent": f"{self.tool}/{get_config().app_version}"},
        ) as session:
            async with session.request(method, url, params=params, proxy=self.proxy) as resp:
                resp.raise_for_status()
                return await resp.text()

    def _parse_efetch_xml(self, xml_text: str) -> list[dict[str, Any]]:
        """解析 efetch 返回的 PubMed XML，提取标题 + 摘要。"""
        articles: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
            for article_elem in root.findall(".//PubmedArticle"):
                try:
                    medline = article_elem.find(".//MedlineCitation")
                    if medline is None:
                        continue

                    # PMID
                    pmid_elem = medline.find("PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""

                    # Article
                    art = medline.find("Article")
                    if art is None:
                        continue

                    # Title
                    title_elem = art.find("ArticleTitle")
                    title = "".join(title_elem.itertext()) if title_elem is not None else ""

                    # Abstract
                    abstract_parts: list[str] = []
                    abstract_elem = art.find("Abstract")
                    if abstract_elem is not None:
                        for ab in abstract_elem.findall("AbstractText"):
                            label = ab.get("Label", "")
                            text = "".join(ab.itertext())
                            if label:
                                abstract_parts.append(f"{label}: {text}")
                            else:
                                abstract_parts.append(text)
                    abstract = "\n".join(abstract_parts)

                    # Authors
                    authors: list[str] = []
                    author_list = art.find(".//AuthorList")
                    if author_list is not None:
                        for author in author_list.findall("Author"):
                            last = author.find("LastName")
                            fore = author.find("ForeName")
                            if last is not None and fore is not None:
                                authors.append(f"{last.text} {fore.text}")
                            elif last is not None:
                                authors.append(last.text)

                    # Journal
                    journal_elem = art.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""

                    # Year
                    year = 0
                    pd_elem = art.find(".//Journal/JournalIssue/PubDate/Year")
                    if pd_elem is not None and pd_elem.text:
                        import re
                        m = re.search(r"\d{4}", pd_elem.text)
                        if m:
                            year = int(m.group())

                    # DOI
                    doi = ""
                    for eid in art.findall(".//ELocationID"):
                        if eid.get("EIdType") == "doi":
                            doi = eid.text or ""
                            break

                    articles.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                        "doi": doi,
                    })
                except Exception as e:
                    logger.debug(f"[PubMed] 解析单篇 XML 失败: {e}")
                    continue
        except ET.ParseError as e:
            logger.error(f"[PubMed] XML 解析失败: {e}")

        return articles

    # ── 内部方法 ──────────────────────────────

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """发送 HTTP 请求并返回 JSON 响应。

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数

        Returns:
            解析后的 JSON 数据

        Raises:
            aiohttp.ClientError: HTTP 请求失败
        """
        connector_kwargs: dict[str, Any] = {}
        if self.proxy:
            connector_kwargs["proxy"] = self.proxy

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=aiohttp.TCPConnector(ssl=False),
            headers={"User-Agent": f"{self.tool}/{get_config().app_version}"},
        ) as session:
            async with session.request(method, url, params=params) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)

    def _parse_esummary(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """解析 esummary JSON 返回为 LiteratureResult 格式。

        Args:
            data: esummary 返回的单篇文献数据

        Returns:
            标准化后的文献字典，解析失败返回 None
        """
        try:
            pmid = str(data.get("uid", ""))

            # 提取标题
            title = ""
            raw_title = data.get("title", "")
            if raw_title:
                title = self._clean_html(raw_title)

            # 提取摘要 - esummary 不包含摘要，用空字符串占位
            abstract = ""

            # 提取作者
            authors: list[str] = []
            raw_authors = data.get("authors", [])
            if isinstance(raw_authors, list):
                for author in raw_authors:
                    name = author.get("name", "") if isinstance(author, dict) else str(author)
                    if name:
                        authors.append(name)

            # 提取期刊
            journal = data.get("source", "")

            # 提取年份
            year = 0
            pub_date = data.get("pubdate", "")
            if pub_date:
                import re
                match = re.search(r"(\d{4})", pub_date)
                if match:
                    year = int(match.group(1))

            # 提取 DOI
            doi = ""
            elocation_id = data.get("elocationid", "")
            if "doi" in elocation_id.lower():
                doi = elocation_id.replace("doi: ", "").replace("doi:", "").strip()
            # 从 articleids 中查找 DOI
            article_ids = data.get("articleids", [])
            if isinstance(article_ids, list):
                for aid in article_ids:
                    if isinstance(aid, dict) and aid.get("idtype", "").lower() == "doi":
                        doi = aid.get("value", "")
                        break

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "doi": doi,
            }
        except Exception as e:
            logger.warning(f"[PubMed] 解析文献数据失败: {e}")
            return None

    def _clean_html(self, text: str) -> str:
        """去除 HTML 标签。"""
        import re
        return re.sub(r"<[^>]+>", "", text).strip()

    # ── 缓存管理 ──────────────────────────────

    def _get_cache(self, key: str) -> Any | None:
        """获取缓存数据（如果未过期）。"""
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._cache[key]
            return None
        return entry.data

    def _set_cache(self, key: str, data: Any) -> None:
        """设置缓存数据。"""
        self._cache[key] = CacheEntry(
            data=data,
            expires_at=datetime.now() + timedelta(seconds=self.cache_ttl),
        )

    def clear_cache(self) -> None:
        """清空所有缓存。"""
        self._cache.clear()
        logger.info("[PubMed] 缓存已清空")

    @property
    def cache_size(self) -> int:
        """当前缓存条目数。"""
        return len(self._cache)


def _has_api_key() -> bool:
    """检查是否有 NCBI API Key（环境变量 NCBI_API_KEY）。"""
    return bool(os.environ.get("NCBI_API_KEY") or get_config().deepseek_api_key)
