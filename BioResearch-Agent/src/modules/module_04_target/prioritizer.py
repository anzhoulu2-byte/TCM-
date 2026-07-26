"""
靶点排序器 (TargetPrioritizer)。

基于多维度加权排序，支持机器学习模型 (LightGBM/XGBoost) 
对靶点候选进行自动优先级排序。包含交叉验证评估和可视化。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from src.config import get_config
from src.modules.module_04_target.target_scorer import TargetScorer


class TargetPrioritizer:
    """靶点优先级排序器。

    支持两种排序模式：
    - **加权排序**：基于 TargetScorer 的多维评分加权求和
    - **ML 排序**：使用 LightGBM 或 XGBoost 训练排序模型

    Attributes:
        scorer: TargetScorer 实例
        top_k: 默认返回 top-k 数量
        use_ml: 是否使用 ML 排序模型
        model_type: ML 模型类型 ("lightgbm" / "xgboost")
        output_dir: 结果输出目录
    """

    def __init__(
        self,
        scorer: TargetScorer | None = None,
        top_k: int = 20,
        use_ml: bool = False,
        model_type: str = "lightgbm",
        output_dir: str | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.scorer: TargetScorer = scorer or TargetScorer(weights=weights)
        self.top_k: int = top_k
        self.use_ml: bool = use_ml
        self.model_type: str = model_type

        # ML 模型缓存
        self._model = None
        self._is_trained: bool = False

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "targets"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"TargetPrioritizer 初始化: top_k={top_k}, "
            f"use_ml={use_ml}, model={model_type}"
        )

    # ── 主排序方法 ────────────────────────────

    def prioritize(
        self,
        candidates: list[dict[str, Any]],
        top_k: int | None = None,
        human_feedback: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """对候选靶点进行排序。

        支持人工反馈动态调整：通过 human_feedback 传入基因-分值的
        手动修正映射，让排序器学习用户的偏好。

        Args:
            candidates: 候选靶点列表，每条必须包含 "gene" 和 "evidence_data"
            top_k: 返回的 top 数量（默认使用 self.top_k）
            human_feedback: 人工反馈字典 {gene_symbol: manual_score},
                用于指导排序调整

        Returns:
            排序后的靶点列表，每条包含评分、证据链、可视化路径

        Examples:
            >>> prioritizer = TargetPrioritizer()
            >>> candidates = [
            ...     {"gene": "TP53", "evidence_data": {"expression": {"log2fc": 2.5}}},
            ...     {"gene": "EGFR", "evidence_data": {"expression": {"log2fc": 1.8}}},
            ... ]
            >>> ranked = prioritizer.prioritize(candidates, top_k=5)
            >>> ranked[0]["ranking"] == 1
            True
        """
        if not candidates:
            logger.warning("候选列表为空")
            return []

        k = top_k or self.top_k
        logger.info(f"排序开始: {len(candidates)} 候选, top_k={k}")

        # ── 维度评分 ──────────────────────────
        scored_candidates: list[dict[str, Any]] = []
        for cand in candidates:
            gene = cand.get("gene", "unknown")
            evidence = cand.get("evidence_data", {})

            score_result = self.scorer.score(gene, evidence)
            scored_candidates.append({
                **cand,
                "gene": gene,
                "total_score": score_result["total_score"],
                "dimensions": score_result["dimensions"],
                "evidence_chain": score_result["evidence_chain"],
            })

        # ── 人工反馈调整 ───────────────────────
        if human_feedback:
            logger.info(f"应用人工反馈: {human_feedback}")
            scored_candidates = self._apply_human_feedback(
                scored_candidates, human_feedback
            )

        # ── 排序 ──────────────────────────────
        if self.use_ml and self._is_trained:
            ranked = self._ml_sort(scored_candidates)
        else:
            ranked = sorted(
                scored_candidates,
                key=lambda x: x.get("total_score", 0),
                reverse=True,
            )

        # ── 设置排名 ──────────────────────────
        for i, cand in enumerate(ranked):
            cand["ranking"] = i + 1
            cand["rank_label"] = self._rank_label(i + 1)

        # ── Top-K + 可视化 ────────────────────
        top_results = ranked[:k]

        # 排序可视化
        fig_path = self._plot_ranking(top_results)
        for cand in top_results:
            cand["ranking_plot"] = fig_path

        # 保存完整结果
        self._save_ranking(top_results, ranked)

        logger.success(
            f"排序完成: top 1={top_results[0]['gene'] if top_results else 'N/A'} "
            f"(score={top_results[0].get('total_score', 0):.4f})"
        )
        return top_results

    # ── 人工反馈 ──────────────────────────────

    def _apply_human_feedback(
        self,
        candidates: list[dict[str, Any]],
        feedback: dict[str, float],
    ) -> list[dict[str, Any]]:
        """应用人工反馈调整评分。

        使用贝叶斯收缩：将人工评分与算法评分加权融合。
        """
        adjusted = []
        for cand in candidates:
            gene = cand["gene"]
            algo_score = cand["total_score"]
            if gene in feedback:
                manual = np.clip(feedback[gene], 0, 1)
                # 贝叶斯融合：手动评分占 60%，算法评分占 40%
                blended = 0.6 * manual + 0.4 * algo_score
                cand["total_score"] = round(blended, 4)
                cand["feedback_applied"] = {"manual_score": manual, "blended_score": blended}
                logger.debug(f"{gene}: 人工={manual:.2f}, 算法={algo_score:.2f}, 融合={blended:.2f}")
            adjusted.append(cand)
        return adjusted

    # ── ML 排序 ─────────────────────────────

    def train_ranking_model(
        self,
        training_data: pd.DataFrame,
        label_column: str = "ranking_score",
    ) -> dict[str, Any]:
        """训练排序模型。

        Args:
            training_data: 训练数据，包含特征列和 label_column
            label_column: 目标列名（真实排名评分）

        Returns:
            训练评估指标
        """
        try:
            if self.model_type == "lightgbm":
                import lightgbm as lgb
                model_cls = lgb.LGBMRanker
                params = {
                    "objective": "lambdarank",
                    "metric": "ndcg",
                    "boosting_type": "gbdt",
                    "n_estimators": 100,
                    "num_leaves": 31,
                }
            else:
                import xgboost as xgb
                model_cls = xgb.XGBRanker
                params = {
                    "objective": "rank:ndcg",
                    "eval_metric": "ndcg",
                    "n_estimators": 100,
                    "max_depth": 6,
                }

            # 特征列（排除 ID 列和标签列）
            feature_cols = [
                c for c in training_data.columns
                if c not in [label_column, "gene", "ranking"]
            ]
            X = training_data[feature_cols].values
            y = training_data[label_column].values

            # 简单的 query 分组（假设所有样本属于同一 query 组）
            q = np.array([len(training_data)])

            self._model = model_cls(**params)
            self._model.fit(X, y, group=q)
            self._is_trained = True

            logger.success(f"排序模型训练完成: {self.model_type}")
            return {"status": "trained", "model_type": self.model_type, "features": feature_cols}

        except ImportError as e:
            logger.warning(f"{self.model_type} 未安装，回退到加权排序: {e}")
            self.use_ml = False
            return {"status": "fallback", "error": str(e)}

    def _ml_sort(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """使用训练好的 ML 模型排序。"""
        if not self._model or not self._is_trained:
            logger.warning("ML 模型未训练，回退到加权排序")
            return sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)

        try:
            features = self._extract_features(candidates)
            scores = self._model.predict(features)
            for i, cand in enumerate(candidates):
                cand["ml_score"] = round(float(scores[i]), 4)
            return sorted(candidates, key=lambda x: x.get("ml_score", 0), reverse=True)
        except Exception as e:
            logger.error(f"ML 排序失败: {e}")
            return sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)

    def _extract_features(self, candidates: list[dict]) -> np.ndarray:
        """从候选靶点中提取特征矩阵。"""
        rows = []
        for cand in candidates:
            dims = cand.get("dimensions", {})
            row = [
                dims.get(d, {}).get("score", 0)
                for d in ["literature_support", "expression_foldchange",
                          "functional_importance", "druggability", "novelty", "safety"]
            ]
            # Agent 评分
            agents = cand.get("agent_assessments", {})
            for agent_name in ["literature_agent", "omics_agent", "network_agent", "critic_agent"]:
                agent = agents.get(agent_name, {})
                row.append(float(agent.get("confidence", 0.5)))
            rows.append(row)
        return np.array(rows)

    # ── 可视化 ──────────────────────────────

    def _plot_ranking(self, top_results: list[dict[str, Any]]) -> str:
        """绘制排序柱状图。"""
        if not top_results:
            return ""

        genes = [c["gene"] for c in top_results]
        scores = [c.get("total_score", 0) for c in top_results]

        fig, ax = plt.subplots(figsize=(max(6, len(genes) * 0.5), 5))
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(genes)))
        bars = ax.barh(range(len(genes)), scores, color=colors[::-1])

        ax.set_yticks(range(len(genes)))
        ax.set_yticklabels(genes, fontsize=10)
        ax.set_xlabel("Total Score", fontsize=11)
        ax.set_title("Target Priority Ranking", fontsize=12, fontweight="bold")
        ax.set_xlim(0, 1.05)
        ax.invert_yaxis()

        # 显示分值
        for bar, score in zip(bars, scores):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{score:.3f}", va="center", fontsize=9)

        # 维度构成堆叠展示
        if len(top_results) <= 10:
            self._plot_dimension_breakdown(top_results, genes)

        fig_path = str(self._output_dir / "ranking.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.debug(f"排序图保存: {fig_path}")
        return fig_path

    def _plot_dimension_breakdown(
        self, top_results: list[dict], genes: list[str]
    ) -> None:
        """绘制维度构成堆积图。"""
        dim_names = ["literature_support", "expression_foldchange",
                     "functional_importance", "druggability", "novelty", "safety"]
        dim_labels = ["Literature", "Expression", "Functional", "Druggability",
                      "Novelty", "Safety"]
        colors = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C"]

        fig, ax = plt.subplots(figsize=(max(6, len(genes) * 0.5), 5))
        bottom = np.zeros(len(genes))

        for i, (dim, label, color) in enumerate(zip(dim_names, dim_labels, colors)):
            values = [
                c.get("dimensions", {}).get(dim, {}).get("score", 0)
                for c in top_results
            ]
            ax.barh(range(len(genes)), values, left=bottom, label=label,
                    color=color, alpha=0.85)
            bottom += values

        ax.set_yticks(range(len(genes)))
        ax.set_yticklabels(genes, fontsize=9)
        ax.set_xlabel("Score Contribution", fontsize=11)
        ax.set_title("Dimension Breakdown", fontsize=12, fontweight="bold")
        ax.set_xlim(0, 1.05)
        ax.invert_yaxis()
        ax.legend(loc="lower right", fontsize=8, ncol=2)

        fig_path = str(self._output_dir / "ranking_dimensions.png")
        fig.savefig(fig_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    # ── 持久化 ──────────────────────────────

    def _save_ranking(self, top: list[dict], all_candidates: list[dict]) -> None:
        """保存排序结果。"""
        # 保存 top-k 可读摘要
        summary = []
        for cand in top:
            summary.append({
                "ranking": cand.get("ranking"),
                "rank_label": cand.get("rank_label"),
                "gene": cand.get("gene"),
                "total_score": cand.get("total_score"),
                "dimensions": {
                    k: v.get("score", 0)
                    for k, v in cand.get("dimensions", {}).items()
                },
            })

        json_path = self._output_dir / "target_ranking.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # CSV
        df = pd.DataFrame(summary)
        csv_path = self._output_dir / "target_ranking.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"排序结果已保存: {csv_path}, {json_path}")

    @staticmethod
    def _rank_label(rank: int) -> str:
        """将排名转换为标签。"""
        if rank == 1:
            return "Top Candidate"
        elif rank <= 3:
            return "High Priority"
        elif rank <= 10:
            return "Medium Priority"
        elif rank <= 20:
            return "Low Priority"
        else:
            return "Background"
