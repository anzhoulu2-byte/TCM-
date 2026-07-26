"""
生信分析模块单元测试 (DifferentialExpression, SurvivalAnalyzer)。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.modules.module_03_analysis.differential_expression import DifferentialExpression
from src.modules.module_03_analysis.survival_analysis import SurvivalAnalyzer


class TestDifferentialExpression:
    @pytest.fixture
    def de(self) -> DifferentialExpression:
        with patch("src.modules.module_03_analysis.differential_expression.get_config"):
            return DifferentialExpression(output_dir=str(Path.cwd()))

    def test_analyze_basic(self, de):
        expr = pd.DataFrame({"S1": [10, 20], "S2": [12, 18],
                             "S3": [2, 5], "S4": [3, 6]},
                            index=["GeneA", "GeneB"])
        meta = pd.DataFrame({"group": ["control", "control", "treatment", "treatment"]},
                            index=["S1", "S2", "S3", "S4"])
        result = de.analyze(expr, meta)
        assert result["summary"]["total_genes_tested"] == 2

    def test_analyze_few_samples(self, de):
        expr = pd.DataFrame({"S1": [1]}, index=["G1"])
        meta = pd.DataFrame({"group": ["control"]}, index=["S1"])
        result = de.analyze(expr, meta)
        assert "error" in result["summary"]

    def test_analyze_empty(self, de):
        result = de.analyze(pd.DataFrame(), pd.DataFrame({"group": []}))
        assert result["summary"]["total_genes_tested"] == 0

    def test_bh_correction(self, de):
        corrected = de._multiple_test_correction(np.array([0.001, 0.01, 0.5]))
        assert len(corrected) == 3
        assert all(corrected <= 1) and all(corrected >= 0)

    def test_bonferroni_correction(self, de):
        de.multiple_test_method = "BONFERRONI"
        corrected = de._multiple_test_correction(np.array([0.001, 0.01]))
        assert corrected[0] > 0.001


class TestSurvivalAnalyzer:
    @pytest.fixture
    def sa(self) -> SurvivalAnalyzer:
        with patch("src.modules.module_03_analysis.survival_analysis.get_config"):
            return SurvivalAnalyzer(output_dir=str(Path.cwd()))

    def test_missing_gene(self, sa):
        expr = pd.DataFrame({"S1": [1]}, index=["GeneX"])
        surv = pd.DataFrame({"survival_time": [12], "event": [1]}, index=["S1"])
        result = sa.kaplan_meier(expr, surv, "MissingGene")
        assert result["summary"].get("error", "")
