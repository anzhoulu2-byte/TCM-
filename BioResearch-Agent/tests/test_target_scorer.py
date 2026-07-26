"""
TargetScorer 和 TargetPrioritizer 单元测试。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.modules.module_04_target.target_scorer import TargetScorer
from src.modules.module_04_target.prioritizer import TargetPrioritizer


class TestTargetScorer:
    @pytest.fixture
    def scorer(self) -> TargetScorer:
        with patch("src.modules.module_04_target.target_scorer.get_config"):
            return TargetScorer(output_dir=str(Path.cwd()))

    def test_score_full(self, scorer):
        evidence = {
            "literature": {"pmid_count": 200, "co_occurrence": ["cancer"]},
            "expression": {"log2fc": 2.5, "pvalue": 0.001, "padj": 0.005},
            "functional": {"go_terms": ["apoptosis"], "pathways": ["p53"], "domains": []},
            "druggability": {"family": "kinase", "known_drugs": ["DrugA"], "pocket": "binding"},
            "novelty": {"total_publications": 300, "clinical_trials": 2, "patents": 5},
            "safety": {"side_effects": [], "tissue_specificity": 0.8, "off_targets": []},
        }
        result = scorer.score("EGFR", evidence)
        assert 0 <= result["total_score"] <= 1
        assert len(result["dimensions"]) == 6

    def test_empty_evidence_returns_default(self, scorer):
        result = scorer.score("Unknown", {})
        assert result["total_score"] >= 0

    def test_literature_scoring(self, scorer):
        s, _ = scorer._score_literature_support({"pmid_count": 0}, "")
        assert s == 0.0
        s, _ = scorer._score_literature_support({"pmid_count": 2000}, "")
        assert s >= 0.8

    def test_novelty_inverse(self, scorer):
        s, _ = scorer._score_novelty({"total_publications": 5}, "")
        assert s > 0.8
        s, _ = scorer._score_novelty({"total_publications": 5000, "clinical_trials": 20}, "")
        assert s < 0.3

    def test_update_weights(self, scorer):
        scorer.update_weights({"literature_support": 0.5})
        w = scorer.get_weights()
        assert abs(sum(w.values()) - 1.0) < 0.01


class TestTargetPrioritizer:
    @pytest.fixture
    def prioritizer(self) -> TargetPrioritizer:
        with patch("src.modules.module_04_target.prioritizer.get_config"):
            return TargetPrioritizer(top_k=5, output_dir=str(Path.cwd()))

    def test_prioritize_empty(self, prioritizer):
        assert prioritizer.prioritize([]) == []

    def test_prioritize_sorts_by_score(self, prioritizer):
        candidates = [
            {"gene": "A", "evidence_data": {"expression": {"log2fc": 3.0, "padj": 0.001}}},
            {"gene": "B", "evidence_data": {"expression": {"log2fc": 1.0, "padj": 0.05}}},
        ]
        ranked = prioritizer.prioritize(candidates)
        assert ranked[0]["total_score"] >= ranked[1]["total_score"]

    def test_human_feedback_adjusts_ranking(self, prioritizer):
        candidates = [
            {"gene": "A", "evidence_data": {"expression": {"log2fc": 0.5, "padj": 0.01}}},
            {"gene": "B", "evidence_data": {"expression": {"log2fc": 0.3, "padj": 0.01}}},
        ]
        ranked = prioritizer.prioritize(candidates, human_feedback={"B": 0.9})
        assert ranked[0]["gene"] == "B"

    def test_rank_label(self, prioritizer):
        assert prioritizer._rank_label(1) == "Top Candidate"
        assert prioritizer._rank_label(10) == "Medium Priority"
