"""
数据模型定义 (Pydantic V2)。

定义项目中各阶段使用的核心数据结构，覆盖从研究问题提出到
最终报告生成的完整工作流。
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# 阶段 1 — 研究问题 (Research Question)
# ──────────────────────────────────────────────

class ResearchQuestion(BaseModel):
    """研究问题定义。

    表示用户提出的初始生物医学研究问题，用于驱动后续的
    检索、分析和报告生成流程。

    Attributes:
        disease: 目标疾病名称（如 "Alzheimer's disease"）
        question_type: 研究问题类型（如 "mechanism", "biomarker", "therapy"）
        description: 详细的研究问题描述
        keywords: 与问题相关的关键词列表，用于文献检索
    """

    disease: str = Field(
        ...,
        min_length=1,
        description="目标疾病名称，如 'Alzheimer's disease'",
        examples=["Breast cancer", "Type 2 diabetes", "COVID-19"],
    )
    question_type: str = Field(
        ...,
        min_length=1,
        description="研究问题类型: mechanism / biomarker / therapy / diagnosis / prognosis",
        examples=["mechanism", "biomarker", "therapy"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="详细的研究问题描述，包含研究背景和科学假设",
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="与问题相关的关键词列表，用于文献检索和过滤",
    )

    def __str__(self) -> str:
        return f"[{self.question_type}] {self.disease}: {self.description[:60]}..."


# ──────────────────────────────────────────────
# 阶段 2 — 文献检索结果 (Literature Result)
# ──────────────────────────────────────────────

class LiteratureResult(BaseModel):
    """文献检索结果。

    表示从 PubMed 等数据库检索得到的单篇文献元数据。

    Attributes:
        pmid: PubMed 唯一标识符
        title: 文献标题
        abstract: 文献摘要内容
        authors: 作者姓名列表
        journal: 发表期刊名称
        year: 发表年份
        doi: 数字对象标识符
    """

    pmid: str = Field(
        ...,
        min_length=1,
        description="PubMed 唯一标识符 (PMID)",
        examples=["12345678"],
    )
    title: str = Field(
        "",
        description="文献标题",
    )
    abstract: str = Field(
        "",
        description="文献摘要",
    )
    authors: List[str] = Field(
        default_factory=list,
        description="作者姓名列表",
    )
    journal: str = Field(
        "",
        description="发表期刊名称",
    )
    year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="发表年份",
        examples=[2024],
    )
    doi: str = Field(
        "",
        description="数字对象标识符 (DOI)",
        examples=["10.1038/s41586-024-00000-0"],
    )


# ──────────────────────────────────────────────
# 阶段 3 — 基因分析结果 (Gene Result)
# ──────────────────────────────────────────────

class GeneResult(BaseModel):
    """基因分析结果。

    表示从差异表达分析或功能基因组学分析中得到的单基因结果。

    Attributes:
        gene_symbol: 基因符号（如 "TP53", "BRCA1"）
        gene_id: 基因在参考数据库中的标识符（如 Entrez ID, Ensembl ID）
        score: 基因的统计学评分（如 fold change, -log10 p-value）
        evidence: 支持该基因为重要基因的证据描述列表
    """

    gene_symbol: str = Field(
        ...,
        min_length=1,
        description="基因符号，如 'TP53', 'BRCA1', 'EGFR'",
        examples=["TP53", "BRCA1", "EGFR"],
    )
    gene_id: str = Field(
        "",
        description="基因数据库标识符（Entrez ID / Ensembl ID）",
        examples=["7157", "ENSG00000141510"],
    )
    score: float = Field(
        0.0,
        description="基因的统计学评分（fold change / -log10 p-value / Z-score 等）",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="支持该基因为重要候选的证据描述列表",
    )


# ──────────────────────────────────────────────
# 阶段 4 — 综合分析结果 (Analysis Result)
# ──────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """综合分析结果。

    封装差异表达分析、功能富集分析等多维度分析的整体结果。

    Attributes:
        gene_list: 分析得到的基因列表
        differential_expression: 差异表达分析结果摘要
        enrichment_results: 功能富集分析结果列表（如 GO terms, KEGG pathways）
    """

    gene_list: List[GeneResult] = Field(
        default_factory=list,
        description="差异表达或筛选得到的基因列表",
    )
    differential_expression: str = Field(
        "",
        description="差异表达分析结果摘要，包含统计方法和阈值信息",
    )
    enrichment_results: List[str] = Field(
        default_factory=list,
        description="功能富集分析结果（GO terms, KEGG pathways, Reactome 等）",
    )

    def top_genes(self, n: int = 10) -> List[GeneResult]:
        """返回评分最高的 N 个基因。

        Args:
            n: 返回的基因数量

        Returns:
            按 score 降序排列的前 N 个 GeneResult
        """
        return sorted(self.gene_list, key=lambda g: g.score, reverse=True)[:n]


# ──────────────────────────────────────────────
# 阶段 5 — 药物靶点候选 (Target Candidate)
# ──────────────────────────────────────────────

class TargetCandidate(BaseModel):
    """药物靶点候选。

    表示经多维度评分和排序后的潜在药物靶点。

    Attributes:
        gene_symbol: 靶点对应的基因符号
        scores: 各维度评分字典，如 {"druggability": 0.85, "expression": 0.72, "literature": 0.91}
        evidence: 支持该靶点的文献或实验证据引用列表
        ranking: 在所有候选靶点中的排序序号
    """

    gene_symbol: str = Field(
        ...,
        min_length=1,
        description="靶点对应的基因符号",
        examples=["EGFR", "VEGFA", "PD-1"],
    )
    scores: Dict[str, float] = Field(
        default_factory=dict,
        description=(
            "各维度评分字典，如 "
            "{'druggability': 0.85, 'expression': 0.72, 'literature': 0.91, "
            "'safety': 0.60, 'novelty': 0.45}"
        ),
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="支持该靶点的证据来源（文献 PMID、数据库引用等）",
    )
    ranking: int = Field(
        0,
        ge=0,
        description="候选靶点的综合排名序号（1-based, 0 表示未排名）",
    )

    @property
    def average_score(self) -> float:
        """返回各维度评分的平均值。"""
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)


# ──────────────────────────────────────────────
# 阶段 6 — 实验方案 (Experimental Protocol)
# ──────────────────────────────────────────────

class ExperimentalProtocol(BaseModel):
    """实验方案。

    描述针对目标靶点设计的实验验证方案，包括实验目的、
    方法、材料和时间线。

    Attributes:
        title: 实验方案标题
        objective: 实验目的概述
        methods: 实验方法列表（如实验步骤、检测方法等）
        materials: 所需材料与试剂列表
        timeline: 实验时间线，如 "Day 1-3: Cell culture; Day 4-7: Treatment"
    """

    title: str = Field(
        ...,
        min_length=1,
        description="实验方案标题",
        examples=["EGFR 抑制剂敏感性验证方案"],
    )
    objective: str = Field(
        "",
        description="实验目的概述，说明要验证的科学假设",
    )
    methods: List[str] = Field(
        default_factory=list,
        description="实验方法与步骤列表",
        examples=[
            ["CCK-8 细胞活力检测", "Western blot 蛋白表达分析", "流式细胞术凋亡检测"],
        ],
    )
    materials: List[str] = Field(
        default_factory=list,
        description="所需材料、试剂与耗材列表",
    )
    timeline: str = Field(
        "",
        description="实验时间线描述",
        examples=["Day 1: 细胞接种 | Day 2: 药物处理 | Day 4-5: 检测与分析"],
    )


# ──────────────────────────────────────────────
# 阶段 7 — 最终报告 (Report)
# ──────────────────────────────────────────────

class Report(BaseModel):
    """综合研究报告。

    整合全流程分析结果，生成的结构化研究报告，
    包含可追溯的执行日志。

    Attributes:
        summary: 研究摘要，概述研究背景、方法和主要发现
        targets: 推荐的靶点候选列表
        protocol: 对应的实验验证方案
        traceability_log: 可追溯日志，记录每一步执行的模块、参数和结果，
            格式如 [{"step": 1, "module": "retrieval", "action": "search_pubmed",
            "params": {...}, "result": ...}, ...]
    """

    summary: str = Field(
        "",
        description="研究摘要，概述研究背景、分析方法和主要发现结论",
    )
    targets: List[TargetCandidate] = Field(
        default_factory=list,
        description="推荐的靶点候选列表（按优先级排序）",
    )
    protocol: Optional[ExperimentalProtocol] = Field(
        default=None,
        description="针对选定靶点的实验验证方案",
    )
    traceability_log: List[Dict] = Field(
        default_factory=list,
        description=(
            "可追溯执行日志，记录每个步骤的模块名称、调用参数和输出结果，"
            "确保结果可复现"
        ),
    )
