"""
IntentClassifier 单元测试。
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.module_01_understanding.intent_classifier import IntentClassifier


class TestIntentClassifier:
    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        with patch("src.modules.module_01_understanding.intent_classifier.get_config") as m:
            cfg = MagicMock()
            cfg.deepseek_api_key = "test-key"
            cfg.max_retries = 1
            cfg.request_timeout = 30
            m.return_value = cfg
            return IntentClassifier()

    @pytest.mark.asyncio
    async def test_classify_success(self, classifier):
        mock_resp = json.dumps({"disease_type": "breast cancer",
                                "research_purpose": "drug_target_identification",
                                "data_type_needed": ["gene_expression"]})
        classifier._call_api = AsyncMock(return_value=mock_resp)
        result = await classifier.classify("乳腺癌靶点研究")
        assert result["disease_type"] == "breast cancer"
        assert result["research_purpose"] == "drug_target_identification"

    @pytest.mark.asyncio
    async def test_classify_empty_returns_default(self, classifier):
        result = await classifier.classify("")
        assert result["disease_type"] == "general"

    @pytest.mark.asyncio
    async def test_classify_no_api_key(self):
        with patch("src.modules.module_01_understanding.intent_classifier.get_config") as m:
            m.return_value.deepseek_api_key = ""
            c = IntentClassifier()
            result = await c.classify("test")
            assert result == c._default_intent()

    def test_parse_response_clean_json(self, classifier):
        raw = '{"disease_type": "COVID-19", "research_purpose": "mechanism_study", "data_type_needed": ["literature"]}'
        result = classifier._parse_response(raw)
        assert result["disease_type"] == "covid-19"

    def test_parse_response_markdown_fence(self, classifier):
        raw = '```json\n{"disease_type": "Lung Cancer", "research_purpose": "therapeutic_evaluation", "data_type_needed": ["clinical_data"]}\n```'
        result = classifier._parse_response(raw)
        assert result["disease_type"] == "lung cancer"
