"""
Module 04: 靶点发现与推理层 — 单元测试。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.modules.module_04_target import TargetScorer, TargetPrioritizer


# ═══════════════════════════════════════════════
# TargetScorer 测试
# ═══════════════════════════════════════════════

class TestTargetScorer:
    @pytest.fixture
    def scorer(self) -> TargetScorer:
        with patch("src.modules.module_04_target.target_scorer.get_config"):
            return TargetScorer(output_dir=str(Path.cwd()))

    @pytest.fixture
    def minimal_evidence(self) -> dict:
        return {
            "literature": {"pmid_count": 150, "co_occurrence": ["cancer", "apoptosis"]},
            "expression": {"log2fc": 2.5, "pvalue": 0.001, "padj": 0.005},
            "functional": {
                "go_terms": ["DNA repair", "cell cycle", "apoptosis"],
                "pathways": ["p53 signaling", "Apoptosis"],
                "domains": ["DNA-binding"],
            },
            "druggability": {
                "family": "kinase",
                "known_drugs": ["DrugA", "DrugB"],
                "pocket": "active site binding pocket",
            },
            "novelty": {
                "total_publications": 500,
                "clinical_trials": 3,
                "patents": 5,
            },
            "safety": {
                "side_effects": [],
                "tissue_specificity": 0.8,
                "off_targets": [],
            },
        }

    def test_score_full(self, scorer, minimal_evidence):
        """测试完整评分流程。"""
        result = scorer.score("TP53", minimal_evidence)
        assert result["gene"] == "TP53"
        assert 0 <= result["total_score"] <= 1
        assert len(result["dimensions"]) == 6
        assert len(result["evidence_chain"]) == 6

    def test_score_empty_evidence(self, scorer):
        """测试空证据降级。"""
        result = scorer.score("UnknownGene", {})
        assert result["gene"] == "UnknownGene"
        assert result["total_score"] >= 0

    def test_score_literature(self, scorer):
        """测试文献维度评分。"""
        score, ev = scorer._score_literature_support({"pmid_count": 0}, "")
        assert score == 0.0

        score, ev = scorer._score_literature_support({"pmid_count": 1000}, "")
        assert score >= 0.7

    def test_score_expression(self, scorer):
        """测试表达维度评分。"""
        score, ev = scorer._score_expression({"log2fc": 0, "padj": 1.0}, "")
        assert score < 0.3

        score, ev = scorer._score_expression({"log2fc": 5.0, "padj": 0.0001}, "")
        assert score > 0.7

    def test_score_druggability(self, scorer):
        """测试可药性评分。"""
        drug_data = {"family": "gpcr", "known_drugs": ["A"] * 3, "pocket": "binding pocket"}
        score, ev = scorer._score_druggability(drug_data, "")
        assert score > 0.5

        score, ev = scorer._score_druggability({}, "")
        assert score < 0.5

    def test_score_novelty(self, scorer):
        """测试新颖性评分（反向）。"""
        score, ev = scorer._score_novelty({"total_publications": 5}, "")
        assert score > 0.8  # 少文献 = 高新颖性

        score, ev = scorer._score_novelty({"total_publications": 5000, "clinical_trials": 20}, "")
        assert score < 0.3  # 多研究 = 低新颖性

    def test_score_safety(self, scorer):
        """测试安全性评分。"""
        score, ev = scorer._score_safety({"side_effects": [], "tissue_specificity": 0.9}, "")
        assert score > 0.7

        score, ev = scorer._score_safety({"side_effects": ["A"] * 5, "tissue_specificity": 0.1}, "")
        assert score < 0.5

    def test_update_weights(self, scorer):
        """测试权重更新。"""
        original = scorer.get_weights()
        scorer.update_weights({"literature_support": 0.5})
        updated = scorer.get_weights()
        assert updated["literature_support"] != original["literature_support"]
        # 检查归一化
        assert abs(sum(updated.values()) - 1.0) < 0.01


# ═══════════════════════════════════════════════
# TargetPrioritizer 测试
# ═══════════════════════════════════════════════

class TestTargetPrioritizer:
    @pytest.fixture
    def prioritizer(self) -> TargetPrioritizer:
        with patch("src.modules.module_04_target.prioritizer.get_config"):
            return TargetPrioritizer(
                top_k=5, use_ml=False, output_dir=str(Path.cwd()),
            )

    @pytest.fixture
    def candidates(self) -> list[dict]:
        return [
            {
                "gene": "TP53",
                "evidence_data": {"expression": {"log2fc": 3.0, "padj": 0.001}},
            },
            {
                "gene": "EGFR",
                "evidence_data": {"expression": {"log2fc": 1.5, "padj": 0.01}},
            },
            {
                "gene": "BRCA1",
                "evidence_data": {"expression": {"log2fc": 2.0, "padj": 0.005}},
            },
        ]

    def test_prioritize_basic(self, prioritizer, candidates):
        """测试基本排序流程。"""
        ranked = prioritizer.prioritize(candidates, top_k=5)
        assert len(ranked) == 3
        assert ranked[0]["ranking"] == 1
        assert ranked[0]["total_score"] >= ranked[1]["total_score"]
        assert all("ranking" in c for c in ranked)
        assert all("rank_label" in c for c in ranked)

    def test_prioritize_top_k(self, prioritizer, candidates):
        """测试 top_k 截断。"""
        ranked = prioritizer.prioritize(candidates, top_k=1)
        assert len(ranked) == 1

    def test_prioritize_empty(self, prioritizer):
        """测试空候选列表。"""
        ranked = prioritizer.prioritize([], top_k=5)
        assert ranked == []

    def test_human_feedback(self, prioritizer, candidates):
        """测试人工反馈调整。"""
        # 加入人工反馈，将 TP53 分数调低
        feedback = {"TP53": 0.2, "EGFR": 0.9}
        ranked = prioritizer.prioritize(candidates, top_k=5, human_feedback=feedback)
        # EGFR 应因反馈成为 top
        assert ranked[0]["gene"] == "EGFR"
        assert "feedback_applied" in ranked[0] or "feedback_applied" in ranked[1]

    def test_rank_label(self, prioritizer):
        """测试排名标签。"""
        assert prioritizer._rank_label(1) == "Top Candidate"
        assert prioritizer._rank_label(3) == "High Priority"
        assert prioritizer._rank_label(10) == "Medium Priority"
        assert prioritizer._rank_label(50) == "Background"

    def test_apply_human_feedback(self, prioritizer):
        """测试反馈整合逻辑。"""
        candidates = [
            {"gene": "GeneA", "total_score": 0.8, "dimensions": {}},
            {"gene": "GeneB", "total_score": 0.5, "dimensions": {}},
        ]
        feedback = {"GeneA": 0.3, "GeneC": 0.9}
        adjusted = prioritizer._apply_human_feedback(candidates, feedback)
        # GeneA 应被调整
        gene_a = [c for c in adjusted if c["gene"] == "GeneA"][0]
        assert gene_a["total_score"] != 0.8
        assert "feedback_applied" in gene_a
        # GeneB 无反馈，保持不变
        gene_b = [c for c in adjusted if c["gene"] == "GeneB"][0]
        assert gene_b["total_score"] == 0.5
