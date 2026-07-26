"""
端到端集成测试 — 验证完整分析流水线。
"""
from __future__ import annotations

import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.module_01_understanding import IntentClassifier, TaskPlanner
from src.modules.module_02_retrieval import LiteratureRetriever
from src.modules.module_04_target import TargetScorer, MultiAgentReasoner, TargetPrioritizer
from src.modules.module_05_protocol import ProtocolGenerator
from src.modules.module_06_report import TraceabilityTracker, ReportGenerator, ReportExporter


class TestEndToEnd:
    """端到端集成测试（所有模块使用 mock，不调用真实 API）。"""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocks(self):
        """模拟完整流水线，确保模块间数据流正确。"""

        # ── Module 1 (patch get_config + _call_api) ──
        with (
            patch("src.modules.module_01_understanding.intent_classifier.get_config") as mc1,
            patch("src.modules.module_01_understanding.task_planner.get_config") as mc2,
            patch.object(IntentClassifier, "_call_api", new=AsyncMock(return_value=json.dumps({
                "disease_type": "breast cancer",
                "research_purpose": "drug_target_identification",
                "data_type_needed": ["gene_expression", "literature"],
            }))),
            patch.object(TaskPlanner, "_call_api", new=AsyncMock(return_value=json.dumps([
                "literature_search", "gene_expression_analysis", "target_prioritization",
            ]))),
        ):
            cfg = MagicMock()
            cfg.deepseek_api_key = "test-key"
            cfg.max_retries = 1
            cfg.request_timeout = 30
            cfg.app_version = "1.0.0"
            mc1.return_value = cfg
            mc2.return_value = cfg

            classifier = IntentClassifier()
            planner = TaskPlanner()

            intent = await classifier.classify("breast cancer target discovery")
            tasks = await planner.plan("breast cancer", intent)

            assert intent["disease_type"] == "breast cancer"
            assert "literature_search" in tasks

        # ── Module 2 (Mock retriever) ──
        with patch.object(LiteratureRetriever, "retrieve", new=AsyncMock(return_value={
            "literature": [{"pmid": "123", "title": "Test Article", "year": 2024,
                            "authors": ["Author A"], "journal": "Nature"}],
            "associated_genes": [{"gene_symbol": "BRCA1", "score": 0.9, "evidence": ["breast cancer"]}],
            "metadata": {"total_literature": 1, "total_genes": 1},
        })):
            retriever = LiteratureRetriever()
            qdata = {"disease": "breast cancer", "keywords": ["BRCA1"]}
            retrieval = await retriever.retrieve(qdata)

            assert len(retrieval["literature"]) == 1
            assert retrieval["literature"][0]["pmid"] == "123"
            assert len(retrieval["associated_genes"]) == 1

        # ── Module 4 (Target scoring + reasoning + prioritization) ──
        candidates = [{
            "gene": "BRCA1",
            "evidence_data": {
                "literature": {"pmid_count": 500, "co_occurrence": ["cancer"]},
                "expression": {"log2fc": 2.0, "padj": 0.001},
                "functional": {"go_terms": ["DNA repair"], "pathways": ["Homologous recombination"], "domains": []},
                "druggability": {"family": "enzyme", "known_drugs": ["Olaparib"], "pocket": "catalytic"},
                "novelty": {"total_publications": 3000, "clinical_trials": 50, "patents": 20},
                "safety": {"side_effects": ["nausea"], "tissue_specificity": 0.6, "off_targets": []},
            },
        }]

        scorer = TargetScorer()
        score_result = scorer.score("BRCA1", candidates[0]["evidence_data"])
        assert 0 <= score_result["total_score"] <= 1

        reasoner = MultiAgentReasoner()
        enriched = await reasoner.reason(candidates)
        assert len(enriched) == 1
        assert "agent_assessments" in enriched[0]

        prioritizer = TargetPrioritizer()
        ranked = prioritizer.prioritize(enriched, top_k=5)
        assert len(ranked) >= 1
        assert ranked[0]["ranking"] == 1

        # ── Module 5 (Protocol) ──
        gen = ProtocolGenerator(output_dir=str(Path.cwd()))
        protocol = gen.generate(ranked[0], {"experiment_type": "in_vitro", "budget": "medium"})
        assert protocol["title"]
        assert protocol["target_gene"] == "BRCA1"

        # ── Module 6 (Report & Export) ──
        tracker = TraceabilityTracker(workflow_id="E2E-TEST")
        tracker.log_step("e2e_test", {"status": "running"}, {"status": "passed"},
                         {"module": "EndToEndTest"})

        all_results = {
            "question": {"disease": "breast cancer"},
            "intent": intent,
            "tasks": tasks,
            "literature": retrieval["literature"],
            "associated_genes": retrieval["associated_genes"],
            "targets": ranked,
            "protocol": protocol,
            "traceability": tracker.export_traceability(),
        }

        report_gen = ReportGenerator(output_dir=str(Path.cwd()))
        html = report_gen.generate_html_report(all_results)
        assert "<html" in html

        exporter = ReportExporter(output_dir=str(Path.cwd()))
        path = exporter.export_html(html, "e2e_test.html")
        assert Path(path).exists()

        wf_path = exporter.export_workflow(tracker.generate_workflow_json(), "e2e_workflow.json")
        assert Path(wf_path).exists()

        print("端到端集成测试通过 ✅")
