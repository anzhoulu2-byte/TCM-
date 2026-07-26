"""
靶点多维评分器 (TargetScorer)。

从文献支持度、表达差异、功能重要性、可药性、新颖性、安全性
六个维度对候选靶点进行综合评分。每项分数均附带可追溯的证据链。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from src.config import get_config


# ── 默认权重 ──────────────────────────────────

DEFAULT_WEIGHTS = {
    "literature_support": 0.20,
    "expression_foldchange": 0.15,
    "functional_importance": 0.20,
    "druggability": 0.20,
    "novelty": 0.10,
    "safety": 0.15,
}

DIMENSION_DESCRIPTIONS = {
    "literature_support": "文献支持度 — 基于 PubMed 文献计数与共现频率",
    "expression_foldchange": "表达差异倍数 — 来自差异表达分析的 log2FC 与显著性",
    "functional_importance": "功能重要性 — GO 功能富集、通路参与度与蛋白结构域",
    "druggability": "可药性评分 — 靶点家族、已知药物相互作用、口袋结构",
    "novelty": "新颖性评分 — 未被充分研究的程度（反向文献计数）",
    "safety": "安全性评分 — 已知副作用、组织特异性表达、脱靶风险",
}


class TargetScorer:
    """靶点多维评分器。

    从多个维度对候选基因进行靶点适用性评分，
    每个评分附带完整的证据链记录。

    Attributes:
        weights: 各维度权重配置
        output_dir: 结果保存目录
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        output_dir: str | None = None,
    ) -> None:
        # 合并用户权重与默认权重
        self.weights: dict[str, float] = dict(DEFAULT_WEIGHTS)
        if weights:
            for k, v in weights.items():
                if k in self.weights:
                    self.weights[k] = v
                    logger.info(f"自定义权重: {k} = {v}")

        # 归一化权重
        total = sum(self.weights.values())
        if not np.isclose(total, 1.0):
            self.weights = {k: v / total for k, v in self.weights.items()}
            logger.debug(f"权重已归一化: {self.weights}")

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "targets"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"TargetScorer 初始化, 权重: {self.weights}")

    # ── 主评分方法 ──────────────────────────

    def score(
        self,
        gene: str,
        evidence_data: dict[str, Any],
    ) -> dict[str, Any]:
        """对单个靶点进行全维度评分。

        Args:
            gene: 基因符号
            evidence_data: 证据数据字典，包含各维度所需的原始数据
                - "literature": {"pmid_count": int, "co_occurrence": list[str]}
                - "expression": {"log2fc": float, "pvalue": float, "padj": float}
                - "functional": {"go_terms": list[str], "pathways": list[str], "domains": list[str]}
                - "druggability": {"family": str, "known_drugs": list[str], "pocket": str}
                - "novelty": {"total_publications": int, "clinical_trials": int, "patents": int}
                - "safety": {"side_effects": list[str], "tissue_specificity": float, "off_targets": list[str]}

        Returns:
            dict 包含：
            - "gene" (str): 基因符号
            - "dimensions" (dict): 各维度评分及其证据链
            - "total_score" (float): 加权总分 (0-1)
            - "evidence_chain" (list[dict]): 完整证据链日志
            - "output_files" (dict): 保存的文件路径

        Examples:
            >>> scorer = TargetScorer()
            >>> evidence = {"expression": {"log2fc": 2.5, "pvalue": 0.001}}
            >>> result = scorer.score("TP53", evidence)
            >>> 0 <= result["total_score"] <= 1
            True
        """
        logger.info(f"评分靶点: {gene}")

        dimensions: dict[str, dict[str, Any]] = {}
        evidence_chain: list[dict[str, Any]] = []

        # ── 1. 文献支持度 ──────────────────────
        lit_data = evidence_data.get("literature", {})
        lit_score, lit_evidence = self._score_literature_support(lit_data, gene)
        dimensions["literature_support"] = {
            "score": lit_score,
            "weight": self.weights["literature_support"],
            "evidence": lit_evidence,
        }
        evidence_chain.append({
            "dimension": "literature_support",
            "score": lit_score,
            "weight": self.weights["literature_support"],
            "summary": lit_evidence.get("summary", ""),
        })

        # ── 2. 表达差异倍数 ────────────────────
        expr_data = evidence_data.get("expression", {})
        expr_score, expr_evidence = self._score_expression(expr_data, gene)
        dimensions["expression_foldchange"] = {
            "score": expr_score,
            "weight": self.weights["expression_foldchange"],
            "evidence": expr_evidence,
        }
        evidence_chain.append({
            "dimension": "expression_foldchange",
            "score": expr_score,
            "weight": self.weights["expression_foldchange"],
            "summary": expr_evidence.get("summary", ""),
        })

        # ── 3. 功能重要性 ──────────────────────
        func_data = evidence_data.get("functional", {})
        func_score, func_evidence = self._score_functional_importance(func_data, gene)
        dimensions["functional_importance"] = {
            "score": func_score,
            "weight": self.weights["functional_importance"],
            "evidence": func_evidence,
        }
        evidence_chain.append({
            "dimension": "functional_importance",
            "score": func_score,
            "weight": self.weights["functional_importance"],
            "summary": func_evidence.get("summary", ""),
        })

        # ── 4. 可药性 ──────────────────────────
        drug_data = evidence_data.get("druggability", {})
        drug_score, drug_evidence = self._score_druggability(drug_data, gene)
        dimensions["druggability"] = {
            "score": drug_score,
            "weight": self.weights["druggability"],
            "evidence": drug_evidence,
        }
        evidence_chain.append({
            "dimension": "druggability",
            "score": drug_score,
            "weight": self.weights["druggability"],
            "summary": drug_evidence.get("summary", ""),
        })

        # ── 5. 新颖性 ──────────────────────────
        nov_data = evidence_data.get("novelty", {})
        nov_score, nov_evidence = self._score_novelty(nov_data, gene)
        dimensions["novelty"] = {
            "score": nov_score,
            "weight": self.weights["novelty"],
            "evidence": nov_evidence,
        }
        evidence_chain.append({
            "dimension": "novelty",
            "score": nov_score,
            "weight": self.weights["novelty"],
            "summary": nov_evidence.get("summary", ""),
        })

        # ── 6. 安全性 ──────────────────────────
        safe_data = evidence_data.get("safety", {})
        safe_score, safe_evidence = self._score_safety(safe_data, gene)
        dimensions["safety"] = {
            "score": safe_score,
            "weight": self.weights["safety"],
            "evidence": safe_evidence,
        }
        evidence_chain.append({
            "dimension": "safety",
            "score": safe_score,
            "weight": self.weights["safety"],
            "summary": safe_evidence.get("summary", ""),
        })

        # ── 加权总分 ──────────────────────────
        total_score = sum(
            d["score"] * d["weight"] for d in dimensions.values()
        )
        total_score = round(float(np.clip(total_score, 0, 1)), 4)

        # 保存
        output_files = self._save_score(gene, dimensions, total_score, evidence_chain)

        result = {
            "gene": gene,
            "dimensions": dimensions,
            "total_score": total_score,
            "evidence_chain": evidence_chain,
            "output_files": output_files,
        }

        logger.info(f"{gene}: 总分={total_score:.4f} (文献={lit_score:.2f}, "
                     f"表达={expr_score:.2f}, 功能={func_score:.2f}, "
                     f"可药性={drug_score:.2f}, 新颖={nov_score:.2f}, "
                     f"安全={safe_score:.2f})")
        return result

    # ── 各维度评分逻辑 ────────────────────────

    def _score_literature_support(
        self, data: dict[str, Any], gene: str
    ) -> tuple[float, dict[str, Any]]:
        """文献支持度评分 (0-1)。

        基于 PMID 数量和与疾病的共现频率。
        """
        pmid_count = data.get("pmid_count", 0) or 0
        co_occurrence = data.get("co_occurrence", []) or []

        # 文献数量评分（对数压缩）
        if pmid_count <= 0:
            raw = 0.0
        elif pmid_count <= 10:
            raw = 0.3
        elif pmid_count <= 50:
            raw = 0.5
        elif pmid_count <= 200:
            raw = 0.7
        elif pmid_count <= 1000:
            raw = 0.85
        else:
            raw = 1.0

        # 共现频率加分
        co_occur_score = min(0.15, len(co_occurrence) * 0.03)

        score = round(min(raw + co_occur_score, 1.0), 4)

        evidence = {
            "source": "PubMed",
            "pmid_count": pmid_count,
            "co_occurrence": co_occurrence[:5],
            "summary": (
                f"{pmid_count} 篇相关文献"
                + (f", {len(co_occurrence)} 个共现关键词" if co_occurrence else "")
            ),
        }
        return score, evidence

    def _score_expression(
        self, data: dict[str, Any], gene: str
    ) -> tuple[float, dict[str, Any]]:
        """表达差异评分 (0-1)。

        基于 log2FC 和显著性水平。
        """
        log2fc = float(data.get("log2fc", 0) or 0)
        pvalue = float(data.get("pvalue", 1) or 1)
        padj = float(data.get("padj", 1) or 1)

        # log2FC 评分
        fc_score = min(abs(log2fc) / 5.0, 1.0)

        # 显著性评分
        if padj < 0.001:
            p_score = 1.0
        elif padj < 0.01:
            p_score = 0.8
        elif padj < 0.05:
            p_score = 0.5
        else:
            p_score = 0.2

        score = round(0.6 * fc_score + 0.4 * p_score, 4)

        evidence = {
            "source": "DifferentialExpression",
            "log2fc": log2fc,
            "pvalue": pvalue,
            "padj": padj,
            "summary": f"log2FC={log2fc:.2f}, p-adj={padj:.2e}",
        }
        return score, evidence

    def _score_functional_importance(
        self, data: dict[str, Any], gene: str
    ) -> tuple[float, dict[str, Any]]:
        """功能重要性评分 (0-1)。

        基于 GO 注释数、通路参与数和蛋白结构域。
        """
        go_terms = data.get("go_terms", []) or []
        pathways = data.get("pathways", []) or []
        domains = data.get("domains", []) or []

        go_score = min(len(go_terms) / 20.0, 0.4)
        pathway_score = min(len(pathways) / 5.0, 0.4)
        domain_score = min(len(domains) * 0.1, 0.2)

        score = round(min(go_score + pathway_score + domain_score, 1.0), 4)

        evidence = {
            "source": "GO / KEGG / InterPro",
            "go_terms": go_terms[:5],
            "pathways": pathways[:5],
            "domains": domains[:3],
            "summary": (
                f"{len(go_terms)} GO terms, {len(pathways)} pathways, "
                f"{len(domains)} domains"
            ),
        }
        return score, evidence

    def _score_druggability(
        self, data: dict[str, Any], gene: str
    ) -> tuple[float, dict[str, Any]]:
        """可药性评分 (0-1)。

        基于靶点家族、已知药物、口袋结构。
        """
        family = str(data.get("family", "")).lower()
        known_drugs = data.get("known_drugs", []) or []
        pocket = str(data.get("pocket", "")).lower()

        # 有利的靶点家族加分
        favorable_families = [
            "gpcr", "kinase", "protease", "ion channel", "nuclear receptor",
            "enzyme", "transporter",
        ]
        family_score = 0.3 if any(f in family for f in favorable_families) else 0.1

        # 已知药物加分
        drug_score = min(len(known_drugs) * 0.15, 0.4)

        # 口袋结构加分
        pocket_score = 0.3 if ("pocket" in pocket or "binding" in pocket or
                                "active" in pocket or "catalytic" in pocket) else 0.1

        score = round(min(family_score + drug_score + pocket_score, 1.0), 4)

        evidence = {
            "source": "DrugBank / ChEMBL / PDB",
            "family": family,
            "known_drugs": known_drugs[:5],
            "has_pocket": pocket != "",
            "summary": (
                f"Family: {family or 'unknown'}"
                + (f", {len(known_drugs)} known drugs" if known_drugs else "")
            ),
        }
        return score, evidence

    def _score_novelty(
        self, data: dict[str, Any], gene: str
    ) -> tuple[float, dict[str, Any]]:
        """新颖性评分 (0-1)。

        高新颖性 = 未被充分研究（反向评分：文献越少越新颖）。
        """
        total_pubs = int(data.get("total_publications", 0) or 0)
        trials = int(data.get("clinical_trials", 0) or 0)
        patents = int(data.get("patents", 0) or 0)

        # 文献越少 → 新颖性越高
        if total_pubs <= 10:
            pub_score = 1.0
        elif total_pubs <= 50:
            pub_score = 0.8
        elif total_pubs <= 200:
            pub_score = 0.5
        elif total_pubs <= 1000:
            pub_score = 0.3
        else:
            pub_score = 0.1

        # 临床试验和专利越多 → 新颖性越低
        research_density = min((trials * 0.2 + patents * 0.1), 0.5)
        novelty = max(pub_score - research_density, 0.0)

        score = round(novelty, 4)

        evidence = {
            "source": "PubMed / ClinicalTrials.gov / USPTO",
            "total_publications": total_pubs,
            "clinical_trials": trials,
            "patents": patents,
            "summary": (
                f"{total_pubs} publications, {trials} trials, {patents} patents"
            ),
        }
        return score, evidence

    def _score_safety(
        self, data: dict[str, Any], gene: str
    ) -> tuple[float, dict[str, Any]]:
        """安全性评分 (0-1)。

        高安全性 = 低副作用风险。
        """
        side_effects = data.get("side_effects", []) or []
        tissue_specificity = float(data.get("tissue_specificity", 0.5) or 0.5)
        off_targets = data.get("off_targets", []) or []

        # 副作用惩罚
        se_penalty = min(len(side_effects) * 0.15, 0.5)

        # 组织特异性：高特异性 = 高安全性
        spec_score = tissue_specificity * 0.3

        # 脱靶惩罚
        off_penalty = min(len(off_targets) * 0.1, 0.3)

        score = round(max(0.5 - se_penalty + spec_score - off_penalty, 0.0), 4)

        evidence = {
            "source": "SIDER / GTEx / OpenTargets Safety",
            "side_effects": side_effects[:5],
            "tissue_specificity": tissue_specificity,
            "off_targets": off_targets[:3],
            "summary": (
                f"{len(side_effects)} side effects, "
                f"tissue specificity: {tissue_specificity:.2f}"
            ),
        }
        return score, evidence

    # ── 持久化 ──────────────────────────────

    def _save_score(
        self,
        gene: str,
        dimensions: dict,
        total_score: float,
        evidence_chain: list[dict],
    ) -> dict[str, str]:
        """保存评分结果为 JSON。"""
        files: dict[str, str] = {}
        data = {
            "gene": gene,
            "total_score": total_score,
            "dimensions": {
                k: {
                    "score": v["score"],
                    "weight": v["weight"],
                    "summary": v["evidence"].get("summary", ""),
                }
                for k, v in dimensions.items()
            },
            "evidence_chain": evidence_chain,
        }
        json_path = self._output_dir / f"score_{gene}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        files["json"] = str(json_path)
        return files

    def get_weights(self) -> dict[str, float]:
        """返回当前权重配置。"""
        return dict(self.weights)

    def update_weights(self, new_weights: dict[str, float]) -> None:
        """动态更新权重（支持人工反馈调整）。"""
        for k, v in new_weights.items():
            if k in self.weights:
                self.weights[k] = v
        # 归一化
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}
        logger.info(f"权重已更新: {self.weights}")

    @property
    def dimension_descriptions(self) -> dict[str, str]:
        """返回各维度中文说明。"""
        return dict(DIMENSION_DESCRIPTIONS)
