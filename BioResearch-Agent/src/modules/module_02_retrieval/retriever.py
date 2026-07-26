"""
文献检索整合器 (LiteratureRetriever)。

整合 PubMed 文献检索和 Open Targets 疾病-基因查询，
根据研究问题自动构建布尔查询关键词，输出统一格式的检索结果。
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

from loguru import logger

from src.modules.module_02_retrieval.pubmed_client import PubMedClient
from src.modules.module_02_retrieval.open_targets_client import OpenTargetsClient

from src.config import get_config


class LiteratureRetriever:
    """文献检索整合器。

    整合 PubMedClient 和 OpenTargetsClient，根据研究问题自动
    构建查询策略，返回统一的检索结果（文献 + 基因 + 元数据）。

    Attributes:
        pubmed_client: PubMed 检索客户端
        open_targets_client: Open Targets 客户端
        max_literature: PubMed 最大检索数量
        max_genes: Open Targets 最大基因数量
        proxy: 代理地址（可选）
    """

    def __init__(
        self,
        pubmed_client: PubMedClient | None = None,
        open_targets_client: OpenTargetsClient | None = None,
        max_literature: int = 50,
        max_genes: int = 50,
        proxy: str | None = None,
    ) -> None:
        self.pubmed_client = pubmed_client or PubMedClient(proxy=proxy)
        self.open_targets_client = open_targets_client or OpenTargetsClient(proxy=proxy)
        self._config = get_config()
        self.max_literature: int = max_literature
        self.max_genes: int = max_genes

        logger.info("LiteratureRetriever 初始化完成")

    # ── 公开方法 ──────────────────────────────

    async def retrieve(self, question: dict[str, Any]) -> dict[str, Any]:
        """根据研究问题执行多源检索。

        自动提取问题中的疾病名和关键词，生成布尔查询，
        并行检索 PubMed 和 Open Targets。

        Args:
            question: 研究问题字典，包含以下键：
                - "disease" (str): 疾病名称
                - "keywords" (list[str]): 关键词列表
                - "question_type" (str, optional): 问题类型
                - "description" (str, optional): 详细描述

        Returns:
            dict 包含：
            - "literature" (list[dict]): 文献列表 (LiteratureResult 格式)
            - "associated_genes" (list[dict]): 关联基因列表
            - "metadata" (dict): 检索元数据总览

        Examples:
            >>> retriever = LiteratureRetriever()
            >>> question = {"disease": "Alzheimer disease",
            ...             "keywords": ["amyloid", "tau", "neuroinflammation"],
            ...             "question_type": "mechanism"}
            >>> result = await retriever.retrieve(question)
            >>> len(result["literature"]) > 0
            True
            >>> result["metadata"]["total_literature"]
            50
        """
        # 提取并验证输入
        disease = str(question.get("disease", "")).strip()
        keywords = list(question.get("keywords", []))
        question_type = str(question.get("question_type", "")).strip()
        description = str(question.get("description", "")).strip()

        if not disease and not keywords:
            logger.warning("[Retriever] 缺少疾病名和关键词，返回空结果")
            return self._empty_result("缺少检索条件")

        logger.info(f"[Retriever] 开始检索: disease={disease}, keywords={keywords}")

        # 生成布尔查询
        pubmed_query = self._build_pubmed_query(disease, keywords, question_type)
        logger.debug(f"[Retriever] PubMed 查询: {pubmed_query}")

        # 并行执行检索
        literature_task = self.pubmed_client.search(
            query=pubmed_query,
            max_results=self.max_literature,
        )
        genes_task = self.open_targets_client.get_disease_genes(
            disease_name=disease or " ".join(keywords),
            max_results=self.max_genes,
        ) if disease else asyncio.sleep(0, [])

        literature, associated_genes = await asyncio.gather(
            literature_task, genes_task, return_exceptions=True
        )

        # 处理异常
        if isinstance(literature, Exception):
            logger.error(f"[Retriever] PubMed 检索异常: {literature}")
            literature = []
        if isinstance(associated_genes, Exception):
            logger.error(f"[Retriever] Open Targets 检索异常: {associated_genes}")
            associated_genes = []

        # 构建元数据
        metadata = self._build_metadata(
            disease=disease,
            keywords=keywords,
            pubmed_query=pubmed_query,
            num_literature=len(literature),
            num_genes=len(associated_genes),
        )

        result = {
            "literature": literature,
            "associated_genes": associated_genes,
            "metadata": metadata,
        }

        logger.success(
            f"[Retriever] 检索完成: {metadata['total_literature']} 篇文献, "
            f"{metadata['total_genes']} 个关联基因"
        )
        return result

    # ── 查询构建 ──────────────────────────────

    def _build_pubmed_query(
        self,
        disease: str,
        keywords: list[str],
        question_type: str,
    ) -> str:
        """构建 PubMed 布尔查询字符串。

        将疾病名和关键词组合为 AND 连接的布尔表达式。

        Args:
            disease: 疾病名称
            keywords: 关键词列表
            question_type: 问题类型（用于添加类型相关词）

        Returns:
            PubMed 布尔查询字符串
        """
        terms: list[str] = []

        # 添加疾病名（用引号包裹精确匹配）
        if disease:
            terms.append(f'"{disease}"')

        # 添加关键词
        for kw in keywords:
            kw = kw.strip()
            if kw and kw not in terms:
                terms.append(f'"{kw}"')

        # 根据问题类型添加补充关键词
        type_keywords = self._get_type_keywords(question_type)
        for tk in type_keywords:
            if tk not in terms:
                terms.append(tk)

        if not terms:
            return ""

        return " AND ".join(terms)

    def _get_type_keywords(self, question_type: str) -> list[str]:
        """根据问题类型生成补充检索词。

        Args:
            question_type: 问题类型

        Returns:
            补充关键词列表
        """
        type_map: dict[str, list[str]] = {
            "mechanism": [
                "mechanism", "pathway", "signaling", "molecular",
            ],
            "biomarker": [
                "biomarker", "diagnostic", "prognostic", "prediction",
            ],
            "therapy": [
                "therapy", "treatment", "drug", "therapeutic", "clinical trial",
            ],
            "diagnosis": [
                "diagnosis", "detection", "screening", "early diagnosis",
            ],
            "drug_target_identification": [
                "drug target", "therapeutic target", "inhibitor",
            ],
        }

        return type_map.get(question_type.lower(), [])

    # ── 元数据构建 ────────────────────────────

    def _build_metadata(
        self,
        disease: str,
        keywords: list[str],
        pubmed_query: str,
        num_literature: int,
        num_genes: int,
    ) -> dict[str, Any]:
        """构建检索元数据。

        Args:
            disease: 疾病名称
            keywords: 关键词列表
            pubmed_query: PubMed 查询字符串
            num_literature: 文献数量
            num_genes: 基因数量

        Returns:
            元数据字典
        """
        num_literature_relevant = int(
            num_literature * 0.7
        )  # 简化估算，实际可添加相关性过滤

        return {
            "disease": disease,
            "keywords": keywords,
            "pubmed_query": pubmed_query,
            "sources": ["PubMed", "Open Targets"],
            "total_literature": num_literature,
            "total_literature_relevant": min(num_literature_relevant, num_literature),
            "total_genes": num_genes,
            "retrieved_at": datetime.now().isoformat(),
        }

    def _empty_result(self, reason: str) -> dict[str, Any]:
        """返回空结果。"""
        return {
            "literature": [],
            "associated_genes": [],
            "metadata": {
                "error": reason,
                "sources": [],
                "total_literature": 0,
                "total_literature_relevant": 0,
                "total_genes": 0,
                "retrieved_at": datetime.now().isoformat(),
            },
        }
