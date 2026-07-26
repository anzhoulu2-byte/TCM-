"""
资源推荐器 (ResourceRecommender)。

基于靶点和实验上下文，推荐适用的细胞系、抗体试剂（含品牌货号）、
检测方法和统计分析方法。内置知识库覆盖常用生物医学资源。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from src.config import get_config


class ResourceRecommender:
    """生物医学资源推荐器。

    根据靶点特征和实验需求，推荐最适的细胞/动物模型、
    商业化抗体与试剂、检测方法和统计分析方法。

    Attributes:
        output_dir: 推荐结果输出目录
    """

    # ── 细胞系推荐库 ────────────────────────
    CELL_LINE_DB = {
        "breast": [
            {"name": "MCF-7", "type": "ER+", "origin": "Breast adenocarcinoma",
             "features": ["hormone responsive", "well-characterized"],
             "recommended_for": ["proliferation", "apoptosis", "hormone therapy"]},
            {"name": "MDA-MB-231", "type": "Triple negative",
             "origin": "Breast adenocarcinoma",
             "features": ["highly invasive", "KRAS mutant"],
             "recommended_for": ["migration", "invasion", "metastasis"]},
            {"name": "SK-BR-3", "type": "HER2+", "origin": "Breast adenocarcinoma",
             "features": ["HER2 amplified"],
             "recommended_for": ["HER2 targeting", "signaling"]},
        ],
        "lung": [
            {"name": "A549", "type": "NSCLC", "origin": "Lung adenocarcinoma",
             "features": ["KRAS mutant", "easy to culture"],
             "recommended_for": ["proliferation", "drug screening"]},
            {"name": "H1299", "type": "NSCLC", "origin": "Lung carcinoma",
             "features": ["p53 null"],
             "recommended_for": ["p53 studies", "apoptosis"]},
            {"name": "H460", "type": "Large cell", "origin": "Lung carcinoma",
             "features": ["fast growing"],
             "recommended_for": ["xenograft", "high-throughput"]},
        ],
        "brain": [
            {"name": "U87MG", "type": "Glioblastoma", "origin": "Brain",
             "features": ["well-characterized"],
             "recommended_for": ["glioma", "migration"]},
            {"name": "SH-SY5Y", "type": "Neuroblastoma", "origin": "Brain",
             "features": ["neuronal differentiation"],
             "recommended_for": ["neurodegeneration", "differentiation"]},
        ],
        "general": [
            {"name": "HEK293T", "type": "Embryonic kidney", "origin": "Human",
             "features": ["high transfection efficiency", "easy to culture"],
             "recommended_for": ["overexpression", "protein production", "Co-IP"]},
            {"name": "HeLa", "type": "Cervical cancer", "origin": "Human",
             "features": ["immortal", "well-characterized"],
             "recommended_for": ["general cell biology", "cell cycle"]},
        ],
    }

    # ── 抗体品牌推荐 ─────────────────────────
    ANTIBODY_VENDORS = [
        {"vendor": "Cell Signaling Technology (CST)", "quality": "premium",
         "applications": ["WB", "IHC", "IF", "IP"], "price_range": "$300-500"},
        {"vendor": "Abcam", "quality": "high",
         "applications": ["WB", "IHC", "IF", "IP", "FC"], "price_range": "$200-400"},
        {"vendor": "Proteintech", "quality": "high",
         "applications": ["WB", "IHC", "IF"], "price_range": "$150-300"},
        {"vendor": "Santa Cruz Biotechnology", "quality": "medium",
         "applications": ["WB", "IP"], "price_range": "$100-250"},
        {"vendor": "Invitrogen (Thermo)", "quality": "high",
         "applications": ["WB", "IHC", "IF", "FC"], "price_range": "$200-450"},
        {"vendor": "R&D Systems", "quality": "premium",
         "applications": ["ELISA", "FC", "WB"], "price_range": "$350-600"},
    ]

    # ── 统计分析推荐 ─────────────────────────
    STATISTICAL_METHODS = {
        "two_group_comparison": [
            {"method": "Student's t-test (unpaired, two-tailed)",
             "assumptions": "正态分布 + 方差齐性", "software": "GraphPad / Python scipy"},
            {"method": "Mann-Whitney U test",
             "assumptions": "非参数，无正态假设", "software": "GraphPad / Python scipy"},
        ],
        "multi_group": [
            {"method": "One-way ANOVA + Tukey post-hoc",
             "assumptions": "正态分布 + 方差齐性", "software": "GraphPad / Python statsmodels"},
            {"method": "Kruskal-Wallis + Dunn post-hoc",
             "assumptions": "非参数替代", "software": "GraphPad / Python scipy"},
        ],
        "two_factor": [
            {"method": "Two-way ANOVA + Sidak post-hoc",
             "assumptions": "正态分布", "software": "GraphPad / R"},
            {"method": "Mixed-effects model",
             "assumptions": "处理缺失值更好", "software": "R (lme4) / Python statsmodels"},
        ],
        "survival": [
            {"method": "Log-rank (Mantel-Cox) test",
             "assumptions": "比例风险", "software": "GraphPad / Python lifelines"},
            {"method": "Cox proportional hazards regression",
             "assumptions": "多变量分析", "software": "R (survival) / Python lifelines"},
        ],
        "correlation": [
            {"method": "Pearson correlation",
             "assumptions": "线性关系 + 正态分布", "software": "GraphPad / Python scipy"},
            {"method": "Spearman rank correlation",
             "assumptions": "单调关系，无正态假设", "software": "GraphPad / Python scipy"},
        ],
    }

    def __init__(self, output_dir: str | None = None) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "protocols"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ResourceRecommender 初始化完成")

    def recommend(self, protocol: dict[str, Any]) -> dict[str, Any]:
        """根据实验方案推荐资源。

        Args:
            protocol: ProtocolGenerator.generate() 输出的方案字典

        Returns:
            dict 包含推荐的细胞系、抗体、检测方法、统计方法
        """
        target_gene = protocol.get("target_gene", "gene")
        disease = protocol.get("disease", "")
        exp_type = protocol.get("experiment_type", "in_vitro")

        logger.info(f"资源推荐: target={target_gene}, disease={disease}")

        # ── 细胞系 / 动物模型 ──────────────────
        cell_lines = self._recommend_cell_lines(disease)

        # ── 抗体 ──────────────────────────────
        antibodies = self._recommend_antibodies(target_gene)

        # ── 检测方法 ──────────────────────────
        detection_methods = self._recommend_detection(exp_type)

        # ── 统计方法 ──────────────────────────
        statistical = self._recommend_statistics(exp_type)

        result = {
            "target_gene": target_gene,
            "cell_lines": cell_lines,
            "antibodies": antibodies,
            "detection_methods": detection_methods,
            "statistical_methods": statistical,
            "notes": self._generate_notes(target_gene, disease),
        }

        logger.success(
            f"推荐完成: {len(cell_lines)} 细胞系, "
            f"{len(antibodies)} 抗体, {len(detection_methods)} 检测方法"
        )
        return result

    def _recommend_cell_lines(self, disease: str) -> list[dict]:
        """推荐细胞系。"""
        disease_lower = disease.lower()
        candidates = []

        # 按疾病匹配
        for key, lines in self.CELL_LINE_DB.items():
            if key in disease_lower or disease_lower in key:
                candidates.extend(lines)

        # 补充通用细胞系
        if not candidates:
            candidates.extend(self.CELL_LINE_DB["general"])

        # 加入通用推荐作为备选
        candidates += [
            c for c in self.CELL_LINE_DB["general"]
            if c["name"] not in {x["name"] for x in candidates}
        ]

        # 标记优先级
        for i, c in enumerate(candidates):
            c["priority"] = "primary" if i == 0 else "secondary"
        return candidates[:5]

    def _recommend_antibodies(self, gene: str) -> list[dict]:
        """推荐抗体。"""
        return [
            {
                "target": f"{gene}",
                "application": "Western blot",
                "recommended_vendor": "Cell Signaling Technology (CST)",
                "recommended_catalog": f"CST-XXXX (anti-{gene})",
                "alternative": f"Abcam ab-XXXXX",
                "dilution": "1:1000",
                "notes": "验证物种反应性: Human/Mouse/Rat",
            },
            {
                "target": f"{gene}",
                "application": "Immunohistochemistry (IHC)",
                "recommended_vendor": "Abcam",
                "recommended_catalog": f"ab-XXXXX (anti-{gene})",
                "alternative": "CST-YYYY",
                "dilution": "1:200",
                "notes": "推荐柠檬酸热修复抗原",
            },
            {
                "target": f"{gene}",
                "application": "Flow Cytometry",
                "recommended_vendor": "Invitrogen",
                "recommended_catalog": f"12-{gene}-42 (conjugated)",
                "alternative": "BioLegend",
                "dilution": "1:100",
                "notes": "选择与仪器匹配的荧光通道",
            },
        ]

    def _recommend_detection(self, exp_type: str) -> list[dict]:
        """推荐检测方法。"""
        from .protocol_generator import ProtocolGenerator

        methods = ProtocolGenerator.DETECTION_METHODS
        if exp_type == "in_vitro":
            return [
                {"name": "Cell viability (CCK-8)", "sensitivity": "High",
                 "quantification": "OD 450nm", "timeline": "1-4 hours"},
                {"name": "Apoptosis (Annexin V/PI)", "sensitivity": "High",
                 "quantification": "Flow cytometry %", "timeline": "2 hours"},
                {"name": "Protein expression (WB)", "sensitivity": "Medium",
                 "quantification": "Densitometry", "timeline": "2 days"},
                {"name": "Gene expression (qPCR)", "sensitivity": "High",
                 "quantification": "ΔΔCt", "timeline": "1 day"},
            ]
        elif exp_type == "in_vivo":
            return [
                {"name": "Tumor volume (caliper)", "sensitivity": "Low",
                 "quantification": "V = L×W²/2", "timeline": "Every 3 days"},
                {"name": "Bioluminescence imaging", "sensitivity": "High",
                 "quantification": "Radiance (p/s/cm²/sr)", "timeline": "Weekly"},
                {"name": "IHC / IF staining", "sensitivity": "Medium",
                 "quantification": "H-score / % positive", "timeline": "3 days"},
            ]
        return methods[:4]

    def _recommend_statistics(self, exp_type: str) -> list[dict]:
        """推荐统计方法。"""
        stats_map = {
            "in_vitro": "two_group_comparison",
            "molecular": "two_group_comparison",
            "in_vivo": "multi_group",
        }
        key = stats_map.get(exp_type, "two_group_comparison")
        return self.STATISTICAL_METHODS.get(key, [])

    def _generate_notes(self, gene: str, disease: str) -> list[str]:
        """生成推荐说明。"""
        return [
            f"{gene} 的可靠商业化抗体较多，建议优先选择 CST 或 Abcam 已验证的克隆号",
            f"如进行 {disease} 相关研究，建议使用对应的肿瘤细胞系或基因工程小鼠模型",
            "所有关键实验建议独立重复至少3次 (n≥3 independent experiments)",
            "统计学显著性阈值: *P<0.05, **P<0.01, ***P<0.001",
        ]
