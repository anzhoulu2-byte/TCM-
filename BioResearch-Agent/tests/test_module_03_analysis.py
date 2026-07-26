"""
Module 03: 生信分析核心层 — 单元测试。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from src.modules.module_03_analysis import (
    DifferentialExpression,
    SurvivalAnalyzer,
    AnalysisOrchestrator,
)


# ═══════════════════════════════════════════════
# DifferentialExpression 测试
# ═══════════════════════════════════════════════

class TestDifferentialExpression:
    @pytest.fixture
    def de(self) -> DifferentialExpression:
        with patch("src.modules.module_03_analysis.differential_expression.get_config"):
            return DifferentialExpression(output_dir=str(Path.cwd()))

    @pytest.fixture
    def expression_data(self) -> pd.DataFrame:
        """6 基因 x 4 样本：前两个 control，后两个 treatment。"""
        np.random.seed(42)
        data = {
            "S1": [10, 20, 5, 3, 15, 8],
            "S2": [12, 18, 6, 4, 14, 9],
            "S3": [2,  5,  10, 15, 1,  20],
            "S4": [3,  6,  8,  18, 2,  22],
        }
        return pd.DataFrame(data, index=["GeneA", "GeneB", "GeneC", "GeneD", "GeneE", "GeneF"])

    @pytest.fixture
    def metadata(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"group": ["control", "control", "treatment", "treatment"]},
            index=["S1", "S2", "S3", "S4"],
        )

    def test_analyze_basic(self, de, expression_data, metadata):
        """测试基本差异分析流程。"""
        result = de.analyze(expression_data, metadata)
        assert "results" in result
        assert "significant" in result
        assert "summary" in result
        assert result["summary"]["total_genes_tested"] == 6

    def test_analyze_empty_expression(self, de):
        """测试空表达矩阵。"""
        empty_expr = pd.DataFrame()
        meta = pd.DataFrame({"group": []})
        result = de.analyze(empty_expr, meta)
        assert result["summary"]["total_genes_tested"] == 0

    def test_analyze_too_few_samples(self, de):
        """测试样本不足。"""
        expr = pd.DataFrame({"S1": [1, 2], "S2": [3, 4]}, index=["G1", "G2"])
        meta = pd.DataFrame({"group": ["control", "control"]}, index=["S1", "S2"])
        result = de.analyze(expr, meta)
        assert result["summary"].get("error") == "样本数量不足"

    def test_multiple_test_correction_bh(self, de):
        """测试 BH 校正。"""
        pvals = np.array([0.001, 0.01, 0.1, 0.5, 0.8])
        corrected = de._multiple_test_correction(pvals)
        assert len(corrected) == 5
        assert all(corrected >= 0)
        assert all(corrected <= 1)

    def test_multiple_test_correction_bonferroni(self, de):
        """测试 Bonferroni 校正。"""
        de.multiple_test_method = "BONFERRONI"
        pvals = np.array([0.001, 0.01, 0.1])
        corrected = de._multiple_test_correction(pvals)
        assert corrected[0] == pytest.approx(0.003, abs=0.001)

    def test_validate_inputs(self, de, expression_data, metadata):
        """测试输入校验。"""
        expr, meta = de._validate_inputs(expression_data, metadata, "group")
        assert expr.shape[1] == 4
        assert len(meta) == 4


# ═══════════════════════════════════════════════
# SurvivalAnalyzer 测试
# ═══════════════════════════════════════════════

class TestSurvivalAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SurvivalAnalyzer:
        with patch("src.modules.module_03_analysis.survival_analysis.get_config"):
            return SurvivalAnalyzer(output_dir=str(Path.cwd()))

    @pytest.fixture
    def expression(self) -> pd.DataFrame:
        return pd.DataFrame({
            "S1": [10, 5],
            "S2": [2, 8],
            "S3": [8, 3],
            "S4": [1, 6],
        }, index=["GeneX", "GeneY"])

    @pytest.fixture
    def survival(self) -> pd.DataFrame:
        return pd.DataFrame({
            "survival_time": [12, 6, 24, 3],
            "event": [1, 1, 0, 1],
        }, index=["S1", "S2", "S3", "S4"])

    @pytest.mark.skip(reason="需要 lifelines 库")
    def test_kaplan_meier_basic(self, analyzer, expression, survival):
        """测试 KM 分析。"""
        result = analyzer.kaplan_meier(expression, survival, "GeneX")
        assert "summary" in result
        assert result["summary"]["gene"] == "GeneX"

    def test_kaplan_meier_missing_gene(self, analyzer, expression, survival):
        """测试不存在的基因（或 lifelines 未安装时的降级）。"""
        result = analyzer.kaplan_meier(expression, survival, "MissingGene")
        error = result["summary"].get("error", "")
        # lifelines 安装与否，报错信息不同但都表示失败
        assert error

    def test_empty_result(self, analyzer):
        """测试空结果。"""
        result = analyzer._empty_result("test error")
        assert result["summary"]["error"] == "test error"
        assert result["cox_model"] is None


# ═══════════════════════════════════════════════
# AnalysisOrchestrator 测试
# ═══════════════════════════════════════════════

class TestAnalysisOrchestrator:
    @pytest.fixture
    def orchestrator(self) -> AnalysisOrchestrator:
        with patch("src.modules.module_03_analysis.analysis_orchestrator.get_config"):
            return AnalysisOrchestrator(
                output_dir=str(Path.cwd()),
                run_go=False,
                run_kegg=False,
                run_survival=False,
            )

    @pytest.fixture
    def expression(self) -> pd.DataFrame:
        np.random.seed(42)
        return pd.DataFrame(
            np.random.randn(10, 6),
            index=[f"Gene{i}" for i in range(10)],
            columns=[f"S{i}" for i in range(6)],
        )

    @pytest.fixture
    def metadata(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"group": ["control"] * 3 + ["treatment"] * 3},
            index=[f"S{i}" for i in range(6)],
        )

    def test_run_full_analysis_basic(self, orchestrator, expression, metadata):
        """测试完整分析流程。"""
        result = orchestrator.run_full_analysis(expression, metadata)
        assert result["status"] == "completed"
        assert "summary" in result
        assert result["summary"]["n_genes_input"] == 10

    def test_run_full_analysis_no_metadata(self, orchestrator, expression):
        """测试无元数据。"""
        result = orchestrator.run_full_analysis(expression, metadata=None)
        assert result["status"] == "completed"
        # 应跳过差异分析步骤
        step1 = result["pipelines"][0]
        assert step1["status"] == "skipped"

    def test_get_genes_for_enrichment(self, orchestrator):
        """测试从结果中提取基因。"""
        results = {
            "differential_expression": {
                "significant": [
                    {"gene": "TP53"},
                    {"gene": "EGFR"},
                    {"gene": ""},
                    {},
                ]
            }
        }
        genes = orchestrator._get_genes_for_enrichment(results)
        assert genes == ["TP53", "EGFR"]
