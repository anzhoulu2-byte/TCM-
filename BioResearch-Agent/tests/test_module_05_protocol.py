"""
Module 05: 实验方案生成层 — 单元测试。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.modules.module_05_protocol import (
    ProtocolGenerator,
    ResourceRecommender,
    FeasibilityAnalyzer,
)


# ═══════════════════════════════════════════════
# ProtocolGenerator 测试
# ═══════════════════════════════════════════════

class TestProtocolGenerator:
    @pytest.fixture
    def gen(self) -> ProtocolGenerator:
        with patch("src.modules.module_05_protocol.protocol_generator.get_config"):
            return ProtocolGenerator(output_dir=str(Path.cwd()))

    @pytest.fixture
    def target(self) -> dict:
        return {"gene": "EGFR", "total_score": 0.85, "disease": "lung cancer"}

    @pytest.fixture
    def context(self) -> dict:
        return {"experiment_type": "in_vitro", "budget": "medium"}

    def test_generate_full(self, gen, target, context):
        """测试完整方案生成。"""
        protocol = gen.generate(target, context)
        assert protocol["title"] == "EGFR 靶点验证方案"
        assert protocol["target_gene"] == "EGFR"
        assert len(protocol["research_objectives"]) == 4
        assert len(protocol["steps"]) > 0
        assert len(protocol["materials"]) > 0
        assert len(protocol["timeline"]) > 0
        assert protocol["status"] == "draft"

    def test_generate_in_vivo(self, gen, target):
        """测试体内实验方案。"""
        ctx = {"experiment_type": "in_vivo", "budget": "high"}
        protocol = gen.generate(target, ctx)
        assert protocol["experiment_type"] == "in_vivo"
        assert protocol["experimental_design"]["type"] == "in_vivo"

    def test_generate_molecular(self, gen, target):
        """测试分子生物学方案。"""
        ctx = {"experiment_type": "molecular"}
        protocol = gen.generate(target, ctx)
        assert protocol["experiment_type"] == "molecular"

    def test_generate_with_feedback(self, gen, target, context):
        """测试包含用户反馈。"""
        context["feedback"] = "请减少 Western blot 步骤"
        protocol = gen.generate(target, context)
        assert len(protocol["feedback_history"]) == 1
        assert "feedback_applied" in protocol["steps"][0]

    def test_generate_objectives(self, gen, target):
        """测试研究目标生成。"""
        objectives = gen._generate_objectives("TP53", "breast cancer", target)
        assert len(objectives) >= 3
        assert objectives[0]["priority"] == "high"

    def test_generate_timeline(self, gen):
        """测试时间表生成。"""
        timeline = gen._generate_timeline(30, "in_vitro")
        assert len(timeline) >= 3
        assert "start_date" in timeline[0]
        assert "end_date" in timeline[0]


# ═══════════════════════════════════════════════
# ResourceRecommender 测试
# ═══════════════════════════════════════════════

class TestResourceRecommender:
    @pytest.fixture
    def recommender(self) -> ResourceRecommender:
        with patch("src.modules.module_05_protocol.resource_recommender.get_config"):
            return ResourceRecommender(output_dir=str(Path.cwd()))

    def test_recommend_cell_lines(self, recommender):
        """测试细胞系推荐。"""
        lines = recommender._recommend_cell_lines("lung cancer")
        assert len(lines) > 0
        assert any("A549" in l["name"] for l in lines)

    def test_recommend_fallback_cell_lines(self, recommender):
        """测试无匹配疾病时返回通用细胞系。"""
        lines = recommender._recommend_cell_lines("unknown disease")
        assert len(lines) > 0
        assert any("HEK293T" in l["name"] for l in lines)

    def test_recommend_antibodies(self, recommender):
        """测试抗体推荐。"""
        abs_ = recommender._recommend_antibodies("EGFR")
        assert len(abs_) == 3
        assert all("EGFR" in a["target"] for a in abs_)

    def test_recommend_full(self, recommender):
        """测试完整推荐流程。"""
        protocol = {
            "target_gene": "TP53",
            "disease": "breast cancer",
            "experiment_type": "in_vitro",
        }
        result = recommender.recommend(protocol)
        assert "cell_lines" in result
        assert "antibodies" in result
        assert "detection_methods" in result
        assert "statistical_methods" in result
        assert len(result["notes"]) > 0


# ═══════════════════════════════════════════════
# FeasibilityAnalyzer 测试
# ═══════════════════════════════════════════════

class TestFeasibilityAnalyzer:
    @pytest.fixture
    def analyzer(self) -> FeasibilityAnalyzer:
        with patch("src.modules.module_05_protocol.feasibility_analyzer.get_config"):
            return FeasibilityAnalyzer(output_dir=str(Path.cwd()))

    @pytest.fixture
    def protocol(self) -> dict:
        return {
            "target_gene": "EGFR",
            "disease": "lung cancer",
            "experiment_type": "in_vitro",
            "steps": [
                {"step": 1, "name": "Cell viability (CCK-8)", "duration": "4 hours"},
                {"step": 2, "name": "Western blot", "duration": "2 days"},
                {"step": 3, "name": "qRT-PCR", "duration": "1 day"},
            ],
            "materials": [
                {"category": "Cell Lines", "items": [{"name": "A549", "vendor": "ATCC"}]},
                {"category": "Antibodies", "items": [
                    {"name": "Anti-EGFR", "vendor": "CST"},
                    {"name": "Anti-β-actin", "vendor": "Proteintech"},
                ]},
            ],
            "timeline": [{"phase": "Prep", "start_date": "2026-08-01",
                          "end_date": "2026-08-03", "activities": ["a"], "days": 3}],
        }

    def test_analyze_full(self, analyzer, protocol):
        """测试完整可行性分析。"""
        result = analyzer.analyze(protocol)
        assert "time_cost" in result
        assert "financial_cost" in result
        assert "technical_difficulty" in result
        assert "success_rate" in result
        assert "ethical_risk" in result
        assert "overall" in result
        assert "recommendation" in result

    def test_overall_score_range(self, analyzer, protocol):
        """测试综合评分在 0-1 范围。"""
        result = analyzer.analyze(protocol)
        assert 0 <= result["overall"]["score"] <= 1

    def test_risk_level_classification(self, analyzer, protocol):
        """测试风险等级分类。"""
        result = analyzer.analyze(protocol)
        assert result["overall"]["risk_level"] in ("low", "medium", "high")

    def test_assess_time(self, analyzer):
        """测试时间评估。"""
        timeline = [{"phase": "Test", "start_date": "2026-08-01",
                     "end_date": "2026-08-10", "activities": ["a"], "days": 10}]
        result = analyzer._assess_time(timeline, [], "in_vitro")
        assert result["total_days"] == 10
        assert result["level"] in ("low", "medium", "high")

    def test_assess_technical_difficulty(self, analyzer):
        """测试技术难度评估。"""
        steps = [{"name": "Western blot"}, {"name": "CCK-8"}]
        result = analyzer._assess_technical_difficulty(steps)
        assert 0 <= result["score"] <= 1

    def test_assess_ethical_risk(self, analyzer):
        """测试伦理风险评估。"""
        result = analyzer._assess_ethical_risk("in_vivo")
        assert "requires_irb" in result
        assert result["requires_irb"] is True
