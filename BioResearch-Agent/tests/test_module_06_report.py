"""
Module 06: 溯源与报告生成层 — 单元测试。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.modules.module_06_report import (
    TraceabilityTracker,
    ReportGenerator,
    ReportExporter,
)


# ═══════════════════════════════════════════════
# TraceabilityTracker 测试
# ═══════════════════════════════════════════════

class TestTraceabilityTracker:
    @pytest.fixture
    def tracker(self) -> TraceabilityTracker:
        with patch("src.modules.module_06_report.traceability.get_config"):
            return TraceabilityTracker(workflow_id="TEST-WF-001")

    def test_log_step(self, tracker):
        """测试记录步骤。"""
        step = tracker.log_step(
            step_name="test_step",
            inputs={"query": "cancer"},
            outputs={"count": 10},
            metadata={"module": "TestModule", "version": "1.0"},
        )
        assert step["step_name"] == "test_step"
        assert step["inputs"]["query"] == "cancer"
        assert step["outputs"]["count"] == 10
        assert step["metadata"]["module"] == "TestModule"

    def test_init_creates_first_step(self, tracker):
        """测试初始化时自动记录第一步。"""
        assert len(tracker.steps) == 1
        assert tracker.steps[0]["step_name"] == "workflow_init"

    def test_get_traceability(self, tracker):
        """测试获取溯源记录。"""
        tracker.log_step("step_a", {}, {}, {})
        tracker.log_step("step_b", {}, {}, {})
        trace = tracker.get_traceability()
        assert len(trace) == 3  # init + step_a + step_b
        assert trace[1]["step_name"] == "step_a"
        assert trace[2]["step_name"] == "step_b"

    def test_get_step(self, tracker):
        """测试按名称查询步骤。"""
        tracker.log_step("unique_step", {"param": 42}, {"result": "ok"}, {})
        step = tracker.get_step("unique_step")
        assert step is not None
        assert step["inputs"]["param"] == 42

    def test_get_step_not_found(self, tracker):
        """测试查询不存在的步骤。"""
        assert tracker.get_step("nonexistent") is None

    def test_get_summary(self, tracker):
        """测试获取汇总信息。"""
        tracker.log_step("s1", {}, {}, {"module": "M1"})
        tracker.log_step("s2", {}, {}, {"module": "M2"})
        summary = tracker.get_summary()
        assert summary["workflow_id"] == "TEST-WF-001"
        assert summary["total_steps"] >= 3
        assert isinstance(summary["total_elapsed_seconds"], (int, float))

    def test_export_traceability(self, tracker):
        """测试导出溯源记录。"""
        tracker.log_step("export_test", {"x": 1}, {"y": 2}, {"module": "M"})
        exported = tracker.export_traceability()
        assert exported["workflow_id"] == "TEST-WF-001"
        assert len(exported["steps"]) >= 2
        assert "metadata" in exported
        assert "summary" in exported

    def test_generate_workflow_json(self, tracker):
        """测试生成可迁移工作流。"""
        tracker.log_step("literature_search", {"query": "cancer"}, {"count": 5},
                         {"module": "PubMedClient"})
        wf = tracker.generate_workflow_json()
        assert wf["workflow_id"] == "TEST-WF-001"
        assert "pipeline" in wf
        assert len(wf["pipeline"]) >= 1

    def test_sanitize_dataframe(self, tracker):
        """测试清理 DataFrame。"""
        import pandas as pd
        df = pd.DataFrame({"A": [1, 2, 3]})
        sanitized = tracker._sanitize(df)
        assert sanitized["_type"] == "DataFrame"
        assert sanitized["_shape"] == [3, 1]

    def test_save(self, tracker):
        """测试保存到文件。"""
        path = tracker.save("test_trace.json")
        assert Path(path).exists()
        with open(path) as f:
            data = json.load(f)
        assert data["workflow_id"] == "TEST-WF-001"


# ═══════════════════════════════════════════════
# ReportGenerator 测试
# ═══════════════════════════════════════════════

class TestReportGenerator:
    @pytest.fixture
    def gen(self) -> ReportGenerator:
        with patch("src.modules.module_06_report.report_generator.get_config"):
            return ReportGenerator(output_dir=str(Path.cwd()))

    @pytest.fixture
    def sample_results(self) -> dict:
        return {
            "question": {"disease": "lung cancer", "question_type": "mechanism",
                         "description": "Test analysis"},
            "differential_expression": {
                "summary": {"significant_genes": 5, "upregulated": 3,
                            "downregulated": 2, "total_genes_tested": 100},
                "significant": [
                    {"gene": "EGFR", "log2FC": 2.5, "pvalue_adjusted": 0.001,
                     "-log10_padj": 3.0},
                    {"gene": "TP53", "log2FC": -1.8, "pvalue_adjusted": 0.005,
                     "-log10_padj": 2.3},
                ],
            },
            "enrichment_go": {
                "summary": {"total_significant_terms": 8,
                            "top_terms": [{"term": "DNA repair", "pvalue": "1e-5",
                                           "padj": "1e-3", "ontology": "BP"}]},
            },
            "targets": [
                {"ranking": 1, "gene": "EGFR", "total_score": 0.85,
                 "dimensions": {"literature_support": {"score": 0.8},
                                "expression_foldchange": {"score": 0.7},
                                "druggability": {"score": 0.9},
                                "safety": {"score": 0.6}},
                 "evidence_chain": [{"dimension": "literature", "score": 0.8,
                                     "summary": "200 publications"}]},
            ],
            "visualizations": {},
            "traceability": {
                "workflow_id": "WF-TEST",
                "summary": {"total_steps": 5, "total_elapsed_seconds": 42},
                "steps": [
                    {"step_id": "STEP-001", "step_name": "search",
                     "metadata": {"module": "PubMedClient"},
                     "elapsed_from_start": 5},
                ],
            },
        }

    def test_generate_summary(self, gen, sample_results):
        """测试摘要生成。"""
        summary = gen.generate_summary(sample_results)
        assert "ABstract" in summary or "Abstract" in summary
        assert "lung cancer" in summary
        assert "5" in summary  # significant genes

    def test_generate_full_report(self, gen, sample_results):
        """测试完整报告生成。"""
        report = gen.generate_full_report(sample_results)
        assert "Background & Research Question" in report
        assert "Methods Overview" in report
        assert "Results" in report
        assert "Candidate Targets" in report
        assert "Experimental Protocol" in report or "Recommended" in report
        assert "Traceability" in report
        assert "Limitations" in report
        assert "References" in report

    def test_generate_html_report(self, gen, sample_results):
        """测试 HTML 报告生成。"""
        html = gen.generate_html_report(sample_results)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "Times New Roman" in html
        assert "lung cancer" in html


# ═══════════════════════════════════════════════
# ReportExporter 测试
# ═══════════════════════════════════════════════

class TestReportExporter:
    @pytest.fixture
    def exporter(self) -> ReportExporter:
        with patch("src.modules.module_06_report.exporter.get_config"):
            return ReportExporter(output_dir=str(Path.cwd()))

    def test_export_html(self, exporter):
        """测试 HTML 导出。"""
        path = exporter.export_html("<h1>Test</h1>", "test.html")
        assert Path(path).exists()
        with open(path) as f:
            content = f.read()
        assert "<h1>Test</h1>" in content

    def test_export_json(self, exporter):
        """测试 JSON 导出。"""
        data = {"key": "value", "number": 42}
        path = exporter.export_json(data, "test.json")
        assert Path(path).exists()
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["key"] == "value"
        assert loaded["number"] == 42

    def test_export_workflow(self, exporter):
        """测试工作流导出。"""
        workflow = {
            "workflow_id": "WF-001",
            "pipeline": [
                {"step_id": "STEP-001", "step_name": "search",
                 "module": "PubMedClient", "inputs": {"query": "cancer"}},
            ],
        }
        path = exporter.export_workflow(workflow, "wf.json")
        assert Path(path).exists()
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["workflow_id"] == "WF-001"
        assert len(loaded["pipeline"]) == 1

    def test_export_workflow_empty_pipeline(self, exporter):
        """测试空工作流导出。"""
        path = exporter.export_workflow({"workflow_id": "WF-002"}, "wf2.json")
        assert Path(path).exists()
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["pipeline"] == []

    def test_export_pdf_fallback(self, exporter):
        """测试 PDF 导出回退。"""
        path = exporter.export_pdf("<p>test</p>", "test.pdf")
        # 如果没有 PDF 引擎，会回退为 .pdf.html
        assert Path(path).exists()
