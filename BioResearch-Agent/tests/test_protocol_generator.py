"""
ProtocolGenerator 单元测试。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.modules.module_05_protocol.protocol_generator import ProtocolGenerator


class TestProtocolGenerator:
    @pytest.fixture
    def gen(self) -> ProtocolGenerator:
        with patch("src.modules.module_05_protocol.protocol_generator.get_config"):
            return ProtocolGenerator(output_dir=str(Path.cwd()))

    @pytest.fixture
    def target(self) -> dict:
        return {"gene": "EGFR", "total_score": 0.85, "disease": "lung cancer"}

    def test_generate_in_vitro(self, gen, target):
        protocol = gen.generate(target, {"experiment_type": "in_vitro", "budget": "medium"})
        assert protocol["title"] == "EGFR 靶点验证方案"
        assert len(protocol["research_objectives"]) == 4
        assert len(protocol["steps"]) > 0
        assert len(protocol["materials"]) > 0
        assert protocol["status"] == "draft"

    def test_generate_in_vivo(self, gen, target):
        ctx = {"experiment_type": "in_vivo", "budget": "high"}
        protocol = gen.generate(target, ctx)
        assert protocol["experimental_design"]["type"] == "in_vivo"

    def test_generate_molecular(self, gen, target):
        protocol = gen.generate(target, {"experiment_type": "molecular"})
        assert protocol["experiment_type"] == "molecular"

    def test_generate_with_feedback(self, gen, target):
        ctx = {"experiment_type": "in_vitro", "feedback": "减少检测步骤"}
        protocol = gen.generate(target, ctx)
        assert len(protocol["feedback_history"]) == 1
        assert protocol.get("steps", [{}])[0].get("feedback_applied")

    def test_objectives_generated(self, gen, target):
        objs = gen._generate_objectives("TP53", "breast cancer", target)
        assert len(objs) >= 3
        assert objs[0]["priority"] == "high"
