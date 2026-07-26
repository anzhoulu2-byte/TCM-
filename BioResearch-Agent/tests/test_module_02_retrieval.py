"""
Module 02: 文献与数据检索层 — 单元测试。

使用 pytest + pytest-asyncio 测试 PubMedClient、OpenTargetsClient、LiteratureRetriever。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.module_02_retrieval import PubMedClient, OpenTargetsClient, LiteratureRetriever


# ═══════════════════════════════════════════════
# PubMedClient 测试
# ═══════════════════════════════════════════════

class TestPubMedClient:
    @pytest.fixture
    def client(self) -> PubMedClient:
        with patch("src.modules.module_02_retrieval.pubmed_client.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.pubmed_email = "test@example.com"
            cfg.max_retries = 1
            cfg.request_timeout = 30
            cfg.app_version = "1.0.0"
            mock_cfg.return_value = cfg
            return PubMedClient(max_retries=1, timeout=30, cache_ttl=0)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client: PubMedClient):
        """测试空查询返回空列表。"""
        result = await client.search("")
        assert result == []

        result = await client.search("   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_cache_hit(self, client: PubMedClient):
        """测试缓存命中。"""
        client._cache["search:test:50:relevance:None"] = MagicMock(
            is_expired=False, data=[{"pmid": "123"}]
        )
        result = await client.search("test")
        assert result == [{"pmid": "123"}]

    def test_parse_esummary_basic(self, client: PubMedClient):
        """测试 esummary 解析。"""
        data = {
            "uid": "12345678",
            "title": "Test <i>Article</i> Title",
            "source": "Nature",
            "pubdate": "2024 Jan 15",
            "authors": [{"name": "Smith J"}, {"name": "Doe A"}],
            "elocationid": "doi: 10.1038/test.2024.12345",
        }
        result = client._parse_esummary(data)
        assert result["pmid"] == "12345678"
        assert "Test Article Title" in result["title"]
        assert "Smith J" in result["authors"]
        assert result["journal"] == "Nature"
        assert result["year"] == 2024
        assert "10.1038" in result["doi"]

    def test_parse_esummary_no_authors(self, client: PubMedClient):
        """测试无作者场景。"""
        data = {
            "uid": "99999999",
            "title": "No Authors",
            "source": "Test Journal",
            "pubdate": "2023",
            "elocationid": "",
        }
        result = client._parse_esummary(data)
        assert result["pmid"] == "99999999"
        assert result["authors"] == []
        assert result["year"] == 2023

    def test_clean_html(self, client: PubMedClient):
        """测试 HTML 标签清理。"""
        assert client._clean_html("Hello <b>World</b>") == "Hello World"
        assert client._clean_html("<p>Test</p>") == "Test"
        assert client._clean_html("No tags") == "No tags"


# ═══════════════════════════════════════════════
# OpenTargetsClient 测试
# ═══════════════════════════════════════════════

class TestOpenTargetsClient:
    @pytest.fixture
    def client(self) -> OpenTargetsClient:
        with patch("src.modules.module_02_retrieval.open_targets_client.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.max_retries = 1
            cfg.request_timeout = 30
            mock_cfg.return_value = cfg
            return OpenTargetsClient(max_retries=1, timeout=30, cache_ttl=0)

    @pytest.mark.asyncio
    async def test_get_disease_genes_empty_name(self, client: OpenTargetsClient):
        """测试空疾病名返回空列表。"""
        result = await client.get_disease_genes("")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_disease_genes_cache_hit(self, client: OpenTargetsClient):
        """测试缓存命中。"""
        client._cache["genes:alzheimer:50"] = MagicMock(
            is_expired=False, data=[{"gene_symbol": "APOE"}]
        )
        result = await client.get_disease_genes("alzheimer")
        assert result == [{"gene_symbol": "APOE"}]

    def test_cache_expiry(self, client: OpenTargetsClient):
        """测试缓存过期。"""
        from datetime import datetime, timedelta
        from src.modules.module_02_retrieval.open_targets_client import _CacheEntry

        expired = _CacheEntry(data="test", expires_at=datetime.now() - timedelta(seconds=1))
        client._cache["key"] = expired
        assert client._get_cache("key") is None
        assert "key" not in client._cache

    def test_cache_valid(self, client: OpenTargetsClient):
        """测试缓存有效。"""
        from datetime import datetime, timedelta
        from src.modules.module_02_retrieval.open_targets_client import _CacheEntry

        valid = _CacheEntry(data="test", expires_at=datetime.now() + timedelta(seconds=300))
        client._cache["key"] = valid
        assert client._get_cache("key") == "test"


# ═══════════════════════════════════════════════
# LiteratureRetriever 测试
# ═══════════════════════════════════════════════

class TestLiteratureRetriever:
    @pytest.fixture
    def retriever(self) -> LiteratureRetriever:
        with patch("src.modules.module_02_retrieval.retriever.get_config"):
            mock_pubmed = MagicMock(spec=PubMedClient)
            mock_pubmed.search = AsyncMock(return_value=[
                {"pmid": "1", "title": "Article 1", "year": 2024},
                {"pmid": "2", "title": "Article 2", "year": 2023},
            ])
            mock_ot = MagicMock(spec=OpenTargetsClient)
            mock_ot.get_disease_genes = AsyncMock(return_value=[
                {"gene_symbol": "APOE", "score": 0.9},
                {"gene_symbol": "APP", "score": 0.8},
            ])
            return LiteratureRetriever(
                pubmed_client=mock_pubmed,
                open_targets_client=mock_ot,
                max_literature=50,
                max_genes=50,
            )

    @pytest.mark.asyncio
    async def test_retrieve_full(self, retriever: LiteratureRetriever):
        """测试完整检索流程。"""
        question = {
            "disease": "Alzheimer disease",
            "keywords": ["amyloid", "tau"],
            "question_type": "mechanism",
        }
        result = await retriever.retrieve(question)

        assert len(result["literature"]) == 2
        assert len(result["associated_genes"]) == 2
        assert result["metadata"]["total_literature"] == 2
        assert result["metadata"]["total_genes"] == 2
        assert "PubMed" in result["metadata"]["sources"]
        assert result["metadata"]["disease"] == "Alzheimer disease"

    @pytest.mark.asyncio
    async def test_retrieve_empty_input(self, retriever: LiteratureRetriever):
        """测试空输入。"""
        result = await retriever.retrieve({"disease": "", "keywords": []})
        assert len(result["literature"]) == 0
        assert result["metadata"].get("error") == "缺少检索条件"

    def test_build_pubmed_query(self, retriever: LiteratureRetriever):
        """测试 PubMed 查询构建。"""
        query = retriever._build_pubmed_query(
            disease="Breast Cancer",
            keywords=["TP53", "BRCA1"],
            question_type="mechanism",
        )
        assert '"Breast Cancer"' in query
        assert '"TP53"' in query
        assert '"BRCA1"' in query
        assert "mechanism" in query or "pathway" in query

    def test_build_pubmed_query_no_type(self, retriever: LiteratureRetriever):
        """测试无问题类型时的查询构建。"""
        query = retriever._build_pubmed_query(
            disease="COVID-19",
            keywords=["treatment"],
            question_type="",
        )
        assert '"COVID-19"' in query
        assert '"treatment"' in query

    def test_get_type_keywords(self, retriever: LiteratureRetriever):
        """测试问题类型关键词映射。"""
        kws = retriever._get_type_keywords("therapy")
        assert "therapy" in kws
        assert "clinical trial" in kws

        kws = retriever._get_type_keywords("unknown_type")
        assert kws == []
