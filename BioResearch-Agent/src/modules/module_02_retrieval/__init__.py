"""
Module 02: 文献与数据检索层 (Literature & Data Retrieval)。

负责从 PubMed、Open Targets 等生物医学数据库检索文献和基因数据，
提供统一的检索接口和缓存机制。
"""

from .pubmed_client import PubMedClient
from .open_targets_client import OpenTargetsClient
from .retriever import LiteratureRetriever
from .literature_analyzer import LiteratureAnalyzer

__all__ = [
    "PubMedClient",
    "OpenTargetsClient",
    "LiteratureRetriever",
    "LiteratureAnalyzer",
]
