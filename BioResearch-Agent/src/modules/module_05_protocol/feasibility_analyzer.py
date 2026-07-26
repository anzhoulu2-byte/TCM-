"""
可行性分析器 (FeasibilityAnalyzer)。

从时间成本、资金成本、技术难度、成功率和伦理风险五个维度
评估实验方案的可行性，生成风险评估矩阵可视化。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from loguru import logger

from src.config import get_config


class FeasibilityAnalyzer:
    """实验方案可行性分析器。

    对生成的实验方案进行多维度可行性评估，包括时间、资金、
    技术、成功率和伦理风险，生成可视化的风险评估矩阵。

    Attributes:
        output_dir: 分析结果输出目录
    """

    # ── 成本基准库 ────────────────────────────
    COST_BENCHMARKS = {
        "in_vitro": {
            "base": 2000,
            "per_sample": 50,
            "per_antibody": 400,
            "per_reagent_kit": 300,
            "personnel_per_day": 200,
        },
        "in_vivo": {
            "base": 5000,
            "per_animal": 100,
            "per_antibody": 400,
            "per_reagent_kit": 500,
            "personnel_per_day": 300,
        },
        "molecular": {
            "base": 1500,
            "per_sample": 30,
            "per_antibody": 350,
            "per_reagent_kit": 250,
            "personnel_per_day": 200,
        },
    }

    # ── 技术难度评估 ──────────────────────────
    TECH_DIFFICULTY = {
        "low": {"score": 0.2, "typical_methods": [
            "CCK-8", "MTT", "qPCR", "ELISA", "Western blot",
        ]},
        "medium": {"score": 0.5, "typical_methods": [
            "Flow cytometry", "IF", "Co-IP", "CRISPR knockin",
            "Primary cell culture", "IHC",
        ]},
        "high": {"score": 0.8, "typical_methods": [
            "Single-cell sequencing", "Spatial transcriptomics",
            "PDX model", "Crispr screening", "Proteomics",
        ]},
    }

    # ── 伦理风险 ──────────────────────────────
    ETHICAL_CONCERNS = {
        "human_samples": {"risk": "high", "requires_irb": True},
        "animal_models": {"risk": "medium", "requires_irb": True},
        "genetic_modification": {"risk": "medium", "requires_biosafety": True},
        "cell_lines": {"risk": "low", "requires_irb": False},
        "recombinant_protein": {"risk": "low", "requires_biosafety": True},
    }

    def __init__(self, output_dir: str | None = None) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "protocols" / "feasibility"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("FeasibilityAnalyzer 初始化完成")

    def analyze(self, protocol: dict[str, Any]) -> dict[str, Any]:
        """分析实验方案的可行性。

        Args:
            protocol: ProtocolGenerator.generate() 输出的方案字典

        Returns:
            dict 包含五维度评估结果和可视化图表路径
        """
        exp_type = protocol.get("experiment_type", "in_vitro")
        steps = protocol.get("steps", [])
        materials = protocol.get("materials", [])
        timeline = protocol.get("timeline", [])

        logger.info(f"可行性分析: type={exp_type}, steps={len(steps)}")

        # ── 时间成本 ──────────────────────────
        time_cost = self._assess_time(timeline, steps, exp_type)

        # ── 资金成本 ──────────────────────────
        financial_cost = self._assess_cost(materials, exp_type)

        # ── 技术难度 ──────────────────────────
        tech_difficulty = self._assess_technical_difficulty(steps)

        # ── 成功率 ──────────────────────────
        success_rate = self._assess_success_rate(
            exp_type, tech_difficulty["score"], steps
        )

        # ── 伦理风险 ──────────────────────────
        ethical_risk = self._assess_ethical_risk(exp_type)

        # ── 综合评估 ──────────────────────────
        overall_feasibility = self._calculate_overall(
            time_cost, financial_cost, tech_difficulty,
            success_rate, ethical_risk,
        )

        # ── 可视化 ──────────────────────────
        risk_matrix_path = self._plot_risk_matrix(
            time_cost, financial_cost, tech_difficulty,
            success_rate, ethical_risk,
        )
        radar_path = self._plot_radar(
            time_cost, financial_cost, tech_difficulty,
            success_rate, ethical_risk,
        )

        result = {
            "time_cost": time_cost,
            "financial_cost": financial_cost,
            "technical_difficulty": tech_difficulty,
            "success_rate": success_rate,
            "ethical_risk": ethical_risk,
            "overall": overall_feasibility,
            "recommendation": self._generate_recommendation(
                overall_feasibility, exp_type
            ),
            "visualization": {
                "risk_matrix": risk_matrix_path,
                "radar_chart": radar_path,
            },
        }

        logger.success(
            f"可行性分析完成: overall={overall_feasibility['score']:.2f}, "
            f"risk_level={overall_feasibility['risk_level']}"
        )
        return result

    # ── 各维度评估 ───────────────────────────

    def _assess_time(
        self, timeline: list[dict], steps: list[dict], exp_type: str
    ) -> dict[str, Any]:
        """评估时间可行性。"""
        total_days = 0
        for phase in timeline:
            if "start_date" in phase and "end_date" in phase:
                from datetime import datetime
                try:
                    s = datetime.strptime(phase["start_date"], "%Y-%m-%d")
                    e = datetime.strptime(phase["end_date"], "%Y-%m-%d")
                    total_days += (e - s).days + 1
                except (ValueError, TypeError):
                    total_days += 7  # 默认

        # 较长时间 = 更高的评分（1表示最短可行，0表示过⻓）
        max_acceptable = {"in_vitro": 30, "in_vivo": 90, "molecular": 45}
        max_days = max_acceptable.get(exp_type, 60)
        score = max(0, 1 - total_days / max_days)

        return {
            "total_days": total_days,
            "score": round(score, 4),
            "level": self._level_from_score(score),
            "breakdown": {p.get("phase", "?"): p.get("days", 0) for p in timeline},
        }

    def _assess_cost(
        self, materials: list[dict], exp_type: str
    ) -> dict[str, Any]:
        """评估资金成本。"""
        benchmarks = self.COST_BENCHMARKS.get(exp_type, self.COST_BENCHMARKS["in_vitro"])

        # 估算总成本
        total_reagents = 0
        for cat in materials:
            for item in cat.get("items", []):
                total_reagents += benchmarks.get("per_reagent_kit", 300)

        total_antibodies = 0
        for cat in materials:
            for item in cat.get("items", []):
                if "Antibod" in cat.get("category", ""):
                    total_antibodies += 1

        personnel_cost = benchmarks["personnel_per_day"] * 30  # 假设30天
        estimated_total = (
            benchmarks["base"]
            + total_reagents
            + total_antibodies * benchmarks["per_antibody"]
            + personnel_cost
        )

        # 相对评分（1表示低成本）
        budget_ranges = {"low": 5000, "medium": 20000, "high": 50000}
        score = max(0, 1 - estimated_total / list(budget_ranges.values())[1])

        return {
            "estimated_cost": round(estimated_total),
            "score": round(score, 4),
            "level": self._level_from_score(score),
            "breakdown": {
                "base": benchmarks["base"],
                "reagents": total_reagents,
                "antibodies": total_antibodies * benchmarks["per_antibody"],
                "personnel": personnel_cost,
            },
        }

    def _assess_technical_difficulty(
        self, steps: list[dict]
    ) -> dict[str, Any]:
        """评估技术难度。"""
        method_names = [s.get("name", "") for s in steps]

        # 计算各步骤难度
        max_difficulty = 0.0
        difficult_steps: list[str] = []

        for name in method_names:
            for level_key, level_data in self.TECH_DIFFICULTY.items():
                for tm in level_data["typical_methods"]:
                    if tm.lower() in name.lower():
                        if level_data["score"] > max_difficulty:
                            max_difficulty = level_data["score"]
                        if level_key in ("medium", "high"):
                            difficult_steps.append(name)

        score = 1 - max_difficulty  # 1表示最简单
        return {
            "score": round(score, 4),
            "level": self._level_from_score(score),
            "max_difficulty": max_difficulty,
            "difficult_steps": list(set(difficult_steps)),
        }

    def _assess_success_rate(
        self, exp_type: str, tech_score: float, steps: list[dict]
    ) -> dict[str, Any]:
        """评估成功率。"""
        # 基准成功率
        base_rate = {"in_vitro": 0.75, "in_vivo": 0.55, "molecular": 0.70}
        base = base_rate.get(exp_type, 0.65)

        # 技术难度调整
        tech_penalty = (1 - tech_score) * 0.3

        # 步骤复杂度调整
        step_penalty = min(len(steps) * 0.03, 0.2)

        rate = max(0.1, base - tech_penalty - step_penalty)
        return {
            "estimated_rate": round(rate, 4),
            "score": round(rate, 4),
            "level": self._level_from_score(rate),
            "factors": {
                "base_rate": base,
                "tech_penalty": round(tech_penalty, 3),
                "step_penalty": round(step_penalty, 3),
            },
        }

    def _assess_ethical_risk(self, exp_type: str) -> dict[str, Any]:
        """评估伦理风险（1=无风险，0=高风险）。"""
        concerns = []
        if exp_type == "in_vivo":
            concerns.append("animal_models")
        concerns.append("cell_lines")

        total_risk = 0
        for c in concerns:
            info = self.ETHICAL_CONCERNS.get(c, {})
            risk_map = {"low": 0.1, "medium": 0.4, "high": 0.8}
            total_risk += risk_map.get(info.get("risk", "low"), 0.1)

        avg_risk = total_risk / max(len(concerns), 1)
        score = 1 - avg_risk

        return {
            "score": round(score, 4),
            "level": self._level_from_score(score),
            "concerns": concerns,
            "requires_irb": any(
                self.ETHICAL_CONCERNS.get(c, {}).get("requires_irb", False)
                for c in concerns if c in self.ETHICAL_CONCERNS
            ),
            "details": {c: self.ETHICAL_CONCERNS.get(c, {}) for c in concerns if c in self.ETHICAL_CONCERNS},
        }

    # ── 综合评估 ──────────────────────────────

    def _calculate_overall(
        self,
        time: dict, cost: dict, tech: dict,
        success: dict, ethical: dict,
    ) -> dict[str, Any]:
        """加权计算综合可行性。"""
        weights = {"time": 0.15, "cost": 0.20, "tech": 0.25, "success": 0.25, "ethical": 0.15}
        scores = {
            "time": time["score"],
            "cost": cost["score"],
            "tech": tech["score"],
            "success": success["score"],
            "ethical": ethical["score"],
        }

        overall = sum(scores[k] * weights[k] for k in weights)

        if overall >= 0.7:
            risk = "low"
        elif overall >= 0.4:
            risk = "medium"
        else:
            risk = "high"

        return {
            "score": round(overall, 4),
            "risk_level": risk,
            "weights": weights,
            "component_scores": scores,
        }

    def _generate_recommendation(
        self, overall: dict, exp_type: str
    ) -> str:
        """生成建议。"""
        score = overall["score"]
        if score >= 0.7:
            return "方案可行性高，建议优先推进。注意伦理审批流程。"
        elif score >= 0.4:
            if exp_type == "in_vivo":
                return "方案可行性中等。建议优化动物实验设计，考虑逐步验证策略。"
            return "方案可行性中等。建议优化实验设计和成本控制。"
        return "方案可行性较低。建议重新设计或寻找替代方法。"

    # ── 可视化 ──────────────────────────────

    def _plot_risk_matrix(
        self, time: dict, cost: dict, tech: dict,
        success: dict, ethical: dict,
    ) -> str:
        """绘制风险矩阵热图。"""
        labels = ["Time", "Cost", "Technical", "Success Rate", "Ethical"]
        scores = [time["score"], cost["score"], tech["score"],
                  success["score"], ethical["score"]]
        levels = [time["level"], cost["level"], tech["level"],
                  success["level"], ethical["level"]]

        fig, ax = plt.subplots(figsize=(7, 4))

        # 颜色映射：绿 → 黄 → 红
        colors = ["#2ECC71" if s >= 0.7 else "#F39C12" if s >= 0.4 else "#E74C3C"
                  for s in scores]

        bars = ax.barh(labels, scores, color=colors, edgecolor="white", height=0.6)

        # 标注分值
        for bar, score, level in zip(bars, scores, levels):
            ax.text(
                bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{score:.2f} ({level})",
                va="center", fontsize=10,
            )

        ax.set_xlim(0, 1.2)
        ax.set_xlabel("Feasibility Score (higher = better)", fontsize=11)
        ax.set_title("Risk Assessment Matrix", fontsize=13, fontweight="bold")
        ax.axvline(0.7, color="green", linestyle="--", alpha=0.3, linewidth=0.8)
        ax.axvline(0.4, color="orange", linestyle="--", alpha=0.3, linewidth=0.8)

        # 图例
        legend_elements = [
            mpatches.Patch(color="#2ECC71", label="Low Risk (≥0.7)"),
            mpatches.Patch(color="#F39C12", label="Medium Risk (0.4-0.7)"),
            mpatches.Patch(color="#E74C3C", label="High Risk (<0.4)"),
        ]
        ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

        fig_path = str(self._output_dir / "risk_matrix.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return fig_path

    def _plot_radar(
        self, time: dict, cost: dict, tech: dict,
        success: dict, ethical: dict,
    ) -> str:
        """绘制雷达图。"""
        labels = ["Time\nCost", "Financial\nCost", "Technical\nDifficulty",
                  "Success\nRate", "Ethical\nRisk"]
        values = [time["score"], cost["score"], tech["score"],
                  success["score"], ethical["score"]]

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values += values[:1]
        # 移除 [:,1] 并确保长度匹配
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={"projection": "polar"})
        ax.plot(angles, values, "o-", linewidth=2, color="#3498DB", markersize=6)
        ax.fill(angles, values, alpha=0.15, color="#3498DB")

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=7)
        ax.set_title("Feasibility Radar", fontsize=12, fontweight="bold", pad=20)

        fig_path = str(self._output_dir / "feasibility_radar.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return fig_path

    @staticmethod
    def _level_from_score(score: float) -> str:
        if score >= 0.7:
            return "low"
        elif score >= 0.4:
            return "medium"
        return "high"
