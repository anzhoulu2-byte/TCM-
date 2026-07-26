"""
Module 01: 问题理解与规划层 — 单元测试。

使用 pytest 和 pytest-asyncio 测试 IntentClassifier 和 TaskPlanner。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.module_01_understanding import IntentClassifier, TaskPlanner


# ═══════════════════════════════════════════════
# IntentClassifier 测试
# ═══════════════════════════════════════════════

class TestIntentClassifier:
    """IntentClassifier 单元测试。"""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        with patch("src.modules.module_01_understanding.intent_classifier.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.deepseek_api_key = "test-key"
            mock_cfg.max_retries = 1
            mock_cfg.request_timeout = 30
            mock_config.return_value = mock_cfg
            return IntentClassifier()

    @pytest.mark.asyncio
    async def test_classify_success(self, classifier: IntentClassifier):
        """测试正常分类流程。"""
        mock_response = json.dumps({
            "disease_type": "breast cancer",
            "research_purpose": "drug_target_identification",
            "data_type_needed": ["gene_expression", "clinical_data"],
        })

        classifier._call_api = AsyncMock(return_value=mock_response)
        result = await classifier.classify("乳腺癌新靶点研究")

        assert result["disease_type"] == "breast cancer"
        assert result["research_purpose"] == "drug_target_identification"
        assert "gene_expression" in result["data_type_needed"]

    @pytest.mark.asyncio
    async def test_classify_empty_question(self, classifier: IntentClassifier):
        """测试空问题场景返回默认值。"""
        result = await classifier.classify("")
        assert result["disease_type"] == "general"
        assert result["research_purpose"] == "literature_review"
        assert result["data_type_needed"] == ["literature"]

    @pytest.mark.asyncio
    async def test_classify_whitespace_question(self, classifier: IntentClassifier):
        """测试纯空白问题返回默认值。"""
        result = await classifier.classify("   ")
        assert result["disease_type"] == "general"

    @pytest.mark.asyncio
    async def test_classify_no_api_key(self):
        """测试无 API Key 时返回默认值。"""
        with patch("src.modules.module_01_understanding.intent_classifier.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.deepseek_api_key = ""
            mock_cfg.max_retries = 1
            mock_cfg.request_timeout = 30
            mock_config.return_value = mock_cfg

            classifier = IntentClassifier()
            result = await classifier.classify("some question")
            assert result == classifier._default_intent()

    @pytest.mark.asyncio
    async def test_classify_retry_on_timeout(self, classifier: IntentClassifier):
        """测试超时后重试并成功恢复。"""
        classifier._api_key = "test-key"
        classifier._max_retries = 3

        call_count = 0

        async def mock_call_with_retry(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                import httpx
                raise httpx.TimeoutException("timeout")
            return json.dumps({
                "disease_type": "alzheimer",
                "research_purpose": "biomarker_discovery",
                "data_type_needed": ["proteomics"],
            })

        classifier._call_api = mock_call_with_retry
        result = await classifier.classify("阿尔茨海默病生物标志物")

        assert result["disease_type"] == "alzheimer"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_classify_all_retries_fail(self, classifier: IntentClassifier):
        """测试全部重试失败后返回默认值。"""
        classifier._api_key = "test-key"
        classifier._max_retries = 2

        async def mock_call_fail(messages):
            import httpx
            raise httpx.TimeoutException("timeout")

        classifier._call_api = mock_call_fail
        result = await classifier.classify("some question")

        assert result == classifier._default_intent()

    @pytest.mark.parametrize(
        "raw_input, expected_disease",
        [
            ('{"disease_type": "COVID-19", "research_purpose": "mechanism_study", "data_type_needed": ["literature"]}', "covid-19"),
            ('```json\n{"disease_type": "Lung Cancer", "research_purpose": "therapeutic_evaluation", "data_type_needed": ["clinical_data"]}\n```', "lung cancer"),
        ],
    )
    def test_parse_response(self, classifier: IntentClassifier, raw_input: str, expected_disease: str):
        """测试不同格式的 LLM 响应解析。"""
        result = classifier._parse_response(raw_input)
        assert result["disease_type"] == expected_disease


# ═══════════════════════════════════════════════
# TaskPlanner 测试
# ═══════════════════════════════════════════════

class TestTaskPlanner:
    """TaskPlanner 单元测试。"""

    @pytest.fixture
    def planner(self) -> TaskPlanner:
        with patch("src.modules.module_01_understanding.task_planner.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.deepseek_api_key = "test-key"
            mock_cfg.max_retries = 1
            mock_cfg.request_timeout = 30
            mock_config.return_value = mock_cfg
            return TaskPlanner()

    @pytest.mark.asyncio
    async def test_plan_success(self, planner: TaskPlanner):
        """测试正常规划流程。"""
        mock_response = json.dumps([
            "literature_search",
            "gene_expression_analysis",
            "pathway_enrichment",
            "target_prioritization",
            "report_generation",
        ])

        planner._call_api = AsyncMock(return_value=mock_response)
        intent = {"disease_type": "breast cancer", "research_purpose": "drug_target_identification"}
        tasks = await planner.plan("乳腺癌靶点研究", intent)

        assert "literature_search" in tasks
        assert "target_prioritization" in tasks
        assert tasks[-1] == "report_generation"

    @pytest.mark.asyncio
    async def test_plan_no_api_key(self):
        """测试无 API Key 时返回默认流水线。"""
        with patch("src.modules.module_01_understanding.task_planner.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.deepseek_api_key = ""
            mock_cfg.max_retries = 1
            mock_cfg.request_timeout = 30
            mock_config.return_value = mock_cfg

            planner = TaskPlanner()
            tasks = await planner.plan("question", {"disease_type": "general"})
            assert tasks == planner._default_pipeline

    @pytest.mark.asyncio
    async def test_plan_retry_and_fallback(self, planner: TaskPlanner):
        """测试重试失败后返回默认流水线。"""
        planner._api_key = "test-key"
        planner._max_retries = 2

        async def mock_call_fail(messages):
            import httpx
            raise httpx.TimeoutException("timeout")

        planner._call_api = mock_call_fail
        tasks = await planner.plan("question", {"disease_type": "general"})

        assert tasks == planner._default_pipeline

    def test_deduplicate_and_validate_valid(self, planner: TaskPlanner):
        """测试去重和校验功能。"""
        tasks = ["literature_search", "gene_expression_analysis",
                 "literature_search", "invalid_task", "report_generation"]
        result = planner._deduplicate_and_validate(tasks)

        assert result == ["literature_search", "gene_expression_analysis", "report_generation"]

    def test_deduplicate_and_validate_empty(self, planner: TaskPlanner):
        """测试全部无效时返回默认流水线。"""
        result = planner._deduplicate_and_validate(["invalid_1", "invalid_2"])
        assert result == planner._default_pipeline

    @pytest.mark.parametrize(
        "raw_input, expected_first",
        [
            ('["literature_search", "target_prioritization"]', "literature_search"),
            ('```json\n["gene_expression_analysis"]\n```', "gene_expression_analysis"),
        ],
    )
    def test_parse_response(self, planner: TaskPlanner, raw_input: str, expected_first: str):
        """测试不同格式的 LLM 响应解析。"""
        result = planner._parse_response(raw_input)
        assert result[0] == expected_first
