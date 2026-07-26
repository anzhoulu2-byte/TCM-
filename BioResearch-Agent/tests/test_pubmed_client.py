"""
PubMedClient 单元测试。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.module_02_retrieval.pubmed_client import PubMedClient


class TestPubMedClient:
    @pytest.fixture
    def client(self) -> PubMedClient:
        with patch("src.modules.module_02_retrieval.pubmed_client.get_config") as m:
            cfg = MagicMock()
            cfg.pubmed_email = "test@example.com"
            cfg.max_retries = 1
            cfg.request_timeout = 30
            cfg.app_version = "1.0.0"
            m.return_value = cfg
            return PubMedClient(max_retries=1, timeout=30, cache_ttl=0)

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self, client):
        assert await client.search("") == []
        assert await client.search("   ") == []

    @pytest.mark.asyncio
    async def test_search_cache_hit(self, client):
        client._cache["search:breast cancer:50:relevance:None"] = MagicMock(
            is_expired=False, data=[{"pmid": "123"}])
        result = await client.search("breast cancer")
        assert result == [{"pmid": "123"}]

    def test_parse_esummary_full(self, client):
        data = {"uid": "12345678", "title": "Test <i>Article</i>",
                "source": "Nature", "pubdate": "2024 Jan 15",
                "authors": [{"name": "Smith J"}],
                "elocationid": "doi: 10.1038/test"}
        result = client._parse_esummary(data)
        assert result["pmid"] == "12345678"
        assert "Test Article" in result["title"]
        assert result["year"] == 2024

    def test_parse_esummary_no_authors(self, client):
        result = client._parse_esummary({"uid": "99", "title": "X",
                                          "source": "J", "pubdate": "2023"})
        assert result["authors"] == []
        assert result["year"] == 2023

    def test_clean_html_removes_tags(self, client):
        assert client._clean_html("<b>Bold</b>") == "Bold"
        assert client._clean_html("No tags") == "No tags"
