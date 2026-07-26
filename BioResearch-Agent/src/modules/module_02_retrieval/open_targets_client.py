"""
Open Targets 客户端 (OpenTargetsClient)。

封装 Open Targets Platform GraphQL API (v4)，
支持按疾病名称检索关联基因（靶点）信息。
内置缓存与重试机制。
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from loguru import logger

from src.config import get_config


# ── 缓存条目 ──────────────────────────────────

@dataclass
class _CacheEntry:
    data: Any
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


# ── GraphQL 查询 ──────────────────────────────

DISEASE_GENES_QUERY = """
query diseaseGenes($diseaseName: String!, $pageSize: Int!) {
  search(queryString: $diseaseName, entityNames: ["disease"]) {
    hits {
      id
      name
    }
  }
}
"""

# 查询疾病关联基因（基于疾病 ID）
DISEASE_ASSOCIATIONS_QUERY = """
query diseaseAssociations($diseaseId: String!, $pageSize: Int!) {
  disease(ensemblId: $diseaseId) {
    id
    name
    associatedTargets(page: { index: 0, size: $pageSize }) {
      count
      rows {
        target {
          id
          approvedSymbol
          approvedName
          biotype
        }
        score
        predictiveHarmScore
        geneticConstraint
      }
    }
  }
}
"""


class OpenTargetsClient:
    """Open Targets Platform 客户端。

    通过 GraphQL API 查询疾病-基因关联数据，
    用于获取疾病相关的潜在药物靶点。

    Attributes:
        api_url: GraphQL API 端点地址
        max_retries: 最大重试次数
        timeout: HTTP 请求超时（秒）
        cache_ttl: 缓存有效期（秒，默认 600）
        proxy: 代理地址（可选）
    """

    API_URL = "https://api.platform.opentargets.org/api/v4/graphql"

    def __init__(
        self,
        api_url: str | None = None,
        max_retries: int | None = None,
        timeout: int | None = None,
        cache_ttl: int = 600,
        proxy: str | None = None,
    ) -> None:
        config = get_config()

        self.api_url: str = api_url or self.API_URL
        self.max_retries: int = max_retries if max_retries is not None else config.max_retries
        self.timeout: int = timeout if timeout is not None else config.request_timeout
        self.cache_ttl: int = cache_ttl
        self.proxy: str | None = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        # 内存缓存
        self._cache: dict[str, _CacheEntry] = {}

        logger.info(
            f"OpenTargetsClient 初始化完成, "
            f"timeout={self.timeout}s, cache_ttl={self.cache_ttl}s"
            + (f", proxy={self.proxy}" if self.proxy else "")
        )

    # ── 公开方法 ──────────────────────────────

    async def get_disease_genes(
        self,
        disease_name: str,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """查询疾病关联基因列表。

        先搜索疾病 ID，再查询该疾病下的关联基因（靶点）。

        Args:
            disease_name: 疾病名称（如 "Alzheimer disease", "breast cancer"）
            max_results: 最大返回基因数（默认 50）

        Returns:
            基因字典列表，每个字典包含：
            - gene_symbol (str): 基因符号
            - gene_id (str): Ensembl ID
            - gene_name (str): 基因全名
            - score (float): 关联评分
            - evidence (list[str]): 关联证据

        Examples:
            >>> client = OpenTargetsClient()
            >>> genes = await client.get_disease_genes("Alzheimer disease", max_results=10)
            >>> len(genes) > 0
            True
            >>> genes[0]["gene_symbol"]
            'APOE'
        """
        if not disease_name or not disease_name.strip():
            logger.warning("[OpenTargets] 空疾病名，返回空列表")
            return []

        disease_name = disease_name.strip()
        cache_key = f"genes:{disease_name}:{max_results}"

        # 检查缓存
        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.info(f"[OpenTargets] 缓存命中: {disease_name}")
            return cached

        logger.info(f"[OpenTargets] 查询疾病关联基因: {disease_name}")

        try:
            # 第一步：搜索疾病 ID
            disease_id = await self._search_disease(disease_name)
            if not disease_id:
                logger.warning(f"[OpenTargets] 未找到疾病: {disease_name}")
                self._set_cache(cache_key, [])
                return []

            # 第二步：获取关联基因
            genes = await self._get_associations(disease_id, max_results)
            self._set_cache(cache_key, genes)
            logger.info(f"[OpenTargets] 找到 {len(genes)} 个关联基因")
            return genes

        except Exception as e:
            logger.error(f"[OpenTargets] 查询失败: {e}")
            return []

    # ── 内部方法 ──────────────────────────────

    async def _search_disease(self, disease_name: str) -> str | None:
        """搜索疾病并返回第一个匹配的 Ensembl ID。

        Args:
            disease_name: 疾病名称

        Returns:
            疾病 Ensembl ID，未找到返回 None
        """
        variables = {"diseaseName": disease_name, "pageSize": 5}

        for attempt in range(1, self.max_retries + 1):
            try:
                data = await self._graphql_request(
                    DISEASE_GENES_QUERY, variables
                )
                hits = (
                    data.get("data", {})
                    .get("search", {})
                    .get("hits", [])
                )
                if hits:
                    disease_id = hits[0].get("id", "")
                    if disease_id:
                        logger.debug(f"[OpenTargets] 疾病 ID: {disease_id} ({hits[0].get('name')})")
                        return disease_id

                logger.warning(f"[OpenTargets] 疾病搜索无结果: {disease_name}")
                return None

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[OpenTargets] 疾病搜索失败 (尝试 {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    return None

        return None

    async def _get_associations(
        self, disease_id: str, max_results: int
    ) -> list[dict[str, Any]]:
        """根据疾病 ID 获取关联基因。

        Args:
            disease_id: 疾病 Ensembl ID
            max_results: 最大返回数

        Returns:
            标准化的基因字典列表
        """
        variables = {
            "diseaseId": disease_id,
            "pageSize": min(max_results, 100),
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                data = await self._graphql_request(
                    DISEASE_ASSOCIATIONS_QUERY, variables
                )
                rows = (
                    data.get("data", {})
                    .get("disease", {})
                    .get("associatedTargets", {})
                    .get("rows", [])
                )

                genes: list[dict[str, Any]] = []
                for row in rows:
                    target = row.get("target", {})
                    gene_symbol = target.get("approvedSymbol", "")
                    if not gene_symbol:
                        continue

                    gene_id = target.get("id", "")
                    score = row.get("score", 0.0) or 0.0

                    # 构建证据列表
                    evidence: list[str] = []
                    if row.get("geneticConstraint"):
                        evidence.append("genetic_constraint")
                    if row.get("predictiveHarmScore") is not None:
                        evidence.append("predictive_harm")

                    genes.append({
                        "gene_symbol": gene_symbol,
                        "gene_id": gene_id,
                        "gene_name": target.get("approvedName", ""),
                        "biotype": target.get("biotype", ""),
                        "score": float(score),
                        "evidence": evidence,
                    })

                # 按评分降序排列
                genes.sort(key=lambda g: g["score"], reverse=True)
                return genes

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[OpenTargets] 关联查询失败 (尝试 {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
                else:
                    return []

        return []

    async def _graphql_request(
        self, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        """发送 GraphQL 请求。

        Args:
            query: GraphQL 查询字符串
            variables: 查询变量

        Returns:
            API 响应 JSON

        Raises:
            aiohttp.ClientError: HTTP 请求失败
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        payload = {"query": query, "variables": variables}

        connector_kwargs: dict[str, Any] = {}
        if self.proxy:
            connector_kwargs["proxy"] = self.proxy

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        ) as session:
            async with session.post(
                self.api_url, json=payload, proxy=self.proxy,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── 缓存管理 ──────────────────────────────

    def _get_cache(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._cache[key]
            return None
        return entry.data

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = _CacheEntry(
            data=data,
            expires_at=datetime.now() + timedelta(seconds=self.cache_ttl),
        )

    def clear_cache(self) -> None:
        """清空所有缓存。"""
        self._cache.clear()
        logger.info("[OpenTargets] 缓存已清空")

    @property
    def cache_size(self) -> int:
        return len(self._cache)
