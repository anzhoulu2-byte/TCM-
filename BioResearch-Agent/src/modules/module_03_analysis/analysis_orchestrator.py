"""
分析编排器 (AnalysisOrchestrator)。

串联差异表达分析、富集分析、生存分析和可视化，
提供一键式全流程分析入口。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.config import get_config
from src.modules.module_03_analysis.differential_expression import DifferentialExpression
from src.modules.module_03_analysis.enrichment_analysis import EnrichmentAnalyzer
from src.modules.module_03_analysis.survival_analysis import SurvivalAnalyzer
from src.modules.module_03_analysis.visualizer import AnalysisVisualizer


class AnalysisOrchestrator:
    """全流程分析编排器。

    一键串联差异表达 → 富集分析 → 生存分析 → 可视化，
    支持转录组和单细胞数据，结果自动保存为 JSON / CSV / PNG。

    Attributes:
        output_dir: 结果输出根目录
        data_type: 数据类型 ("bulk" / "sc")
        run_go: 是否执行 GO 富集分析
        run_kegg: 是否执行 KEGG 富集分析
        run_survival: 是否执行生存分析
    """

    def __init__(
        self,
        output_dir: str | None = None,
        data_type: str = "bulk",
        run_go: bool = True,
        run_kegg: bool = True,
        run_survival: bool = True,
    ) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "analysis"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self.data_type: str = data_type
        self.run_go: bool = run_go
        self.run_kegg: bool = run_kegg
        self.run_survival: bool = run_survival

        # 子模块
        self.de = DifferentialExpression(data_type=data_type)
        self.enrichment = EnrichmentAnalyzer()
        self.survival = SurvivalAnalyzer()
        self.viz = AnalysisVisualizer()

        logger.info(
            f"AnalysisOrchestrator 初始化: data_type={data_type}, "
            f"run_go={run_go}, run_kegg={run_kegg}, "
            f"run_survival={run_survival}"
        )

    def run_full_analysis(
        self,
        expression_data: pd.DataFrame,
        metadata: pd.DataFrame | None = None,
        survival_data: pd.DataFrame | None = None,
        question: dict[str, Any] | None = None,
        group_col: str = "group",
        control_label: str = "control",
        treatment_label: str = "treatment",
    ) -> dict[str, Any]:
        """执行全流程分析。

        Args:
            expression_data: 表达矩阵（行=基因，列=样本）
            metadata: 样本元数据（用于差异分析分组）
            survival_data: 生存数据（用于生存分析）
            question: 研究问题字典（可选，用于报告上下文）
            group_col: 分组列名
            control_label: 对照组标签
            treatment_label: 实验组标签

        Returns:
            dict 包含所有分析步骤的结果和摘要。

        Examples:
            >>> orchestrator = AnalysisOrchestrator()
            >>> expr = pd.DataFrame({"S1": [10, 5], "S2": [12, 6], "S3": [2, 8], "S4": [3, 9]},
            ...                      index=["GeneA", "GeneB"])
            >>> meta = pd.DataFrame({"group": ["control","control","treatment","treatment"]},
            ...                      index=["S1","S2","S3","S4"])
            >>> result = orchestrator.run_full_analysis(expr, meta)
            >>> result["status"]
            'completed'
        """
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("开始全流程生信分析")
        logger.info("=" * 50)

        results: dict[str, Any] = {
            "status": "running",
            "start_time": start_time.isoformat(),
            "data_type": self.data_type,
            "differential_expression": None,
            "enrichment_go": None,
            "enrichment_kegg": None,
            "survival": None,
            "visualizations": {},
            "summary": {},
            "pipelines": [],
            "question": question or {},
        }

        # ── 步骤 1: 差异表达分析 ──────────────
        logger.info("[步骤 1/4] 差异表达分析...")
        try:
            if metadata is not None:
                de_result = self.de.analyze(
                    expression_data=expression_data,
                    metadata=metadata,
                    group_col=group_col,
                    control_label=control_label,
                    treatment_label=treatment_label,
                )
                results["differential_expression"] = de_result
                results["pipelines"].append({
                    "step": 1,
                    "module": "DifferentialExpression",
                    "status": "success",
                    "summary": de_result.get("summary", {}),
                })

                # 火山图
                de_significant = de_result.get("significant", [])
                de_genes = [g.get("gene", "") for g in de_significant]

                fig_v = self.viz.volcano_plot(
                    de_result,
                    title=f"Volcano Plot ({self.data_type})",
                    filename="volcano.png",
                    log2fc_threshold=self.de.log2fc_threshold,
                    pvalue_threshold=self.de.pvalue_threshold,
                )
                results["visualizations"]["volcano"] = "figures/volcano.png"

                # 热图（top 50 差异基因）
                if de_genes:
                    top_50 = de_genes[:50]
                    top_expr = expression_data.loc[
                        expression_data.index.intersection(top_50)
                    ]
                    if not top_expr.empty:
                        self.viz.heatmap(
                            top_expr,
                            metadata=metadata,
                            title=f"Expression Heatmap - Top {len(top_expr)} DEGs",
                            filename="heatmap.png",
                            group_col=group_col,
                        )
                        results["visualizations"]["heatmap"] = "figures/heatmap.png"
            else:
                logger.warning("未提供 metadata，跳过差异分析")
                results["pipelines"].append({
                    "step": 1,
                    "module": "DifferentialExpression",
                    "status": "skipped",
                })
        except Exception as e:
            logger.error(f"差异表达分析失败: {e}")
            results["pipelines"].append({
                "step": 1, "module": "DifferentialExpression",
                "status": "failed", "error": str(e),
            })

        # ── 步骤 2: GO 富集分析 ──────────────
        if self.run_go:
            logger.info("[步骤 2/4] GO 富集分析...")
            try:
                go_genes = self._get_genes_for_enrichment(results)
                if go_genes:
                    go_result = self.enrichment.go_enrichment(go_genes)
                    results["enrichment_go"] = go_result
                    results["pipelines"].append({
                        "step": 2,
                        "module": "GO Enrichment",
                        "status": "success",
                    })

                    # GO 气泡图
                    self.viz.go_plot(
                        go_result,
                        title="GO Enrichment Analysis",
                        filename="go_enrichment.png",
                    )
                    results["visualizations"]["go_enrichment"] = "figures/go_enrichment.png"
                else:
                    logger.warning("无显著差异基因，跳过 GO 富集")
                    results["pipelines"].append({
                        "step": 2, "module": "GO Enrichment",
                        "status": "skipped",
                    })
            except Exception as e:
                logger.error(f"GO 富集分析失败: {e}")
                results["pipelines"].append({
                    "step": 2, "module": "GO Enrichment",
                    "status": "failed", "error": str(e),
                })

        # ── 步骤 3: KEGG 富集分析 ─────────────
        if self.run_kegg:
            logger.info("[步骤 3/4] KEGG 富集分析...")
            try:
                kegg_genes = self._get_genes_for_enrichment(results)
                if kegg_genes:
                    kegg_result = self.enrichment.kegg_enrichment(kegg_genes)
                    results["enrichment_kegg"] = kegg_result
                    results["pipelines"].append({
                        "step": 3,
                        "module": "KEGG Enrichment",
                        "status": "success",
                    })
                else:
                    results["pipelines"].append({
                        "step": 3, "module": "KEGG Enrichment",
                        "status": "skipped",
                    })
            except Exception as e:
                logger.error(f"KEGG 富集分析失败: {e}")
                results["pipelines"].append({
                    "step": 3, "module": "KEGG Enrichment",
                    "status": "failed", "error": str(e),
                })

        # ── 步骤 4: 生存分析 ─────────────────
        if self.run_survival and survival_data is not None:
            logger.info("[步骤 4/4] 生存分析...")
            try:
                # KM 分析：对 top 差异基因做 KM
                de_genes = self._get_genes_for_enrichment(results)
                km_results: dict[str, Any] = {}
                for gene in de_genes[:5]:  # 限制 top 5
                    km_res = self.survival.kaplan_meier(
                        expression_data, survival_data, gene
                    )
                    if km_res.get("km_high") is not None:
                        km_results[gene] = km_res
                        # KM 曲线
                        self.viz.km_plot(
                            km_res,
                            title=f"KM Curve - {gene}",
                            filename=f"km_{gene}.png",
                        )
                        results["visualizations"][f"km_{gene}"] = f"figures/km_{gene}.png"

                # Cox 回归
                cox_result = self.survival.cox_regression(
                    expression_data, survival_data, de_genes[:20]
                )

                results["survival"] = {
                    "kaplan_meier": km_results,
                    "cox_regression": cox_result,
                }
                results["pipelines"].append({
                    "step": 4,
                    "module": "Survival Analysis",
                    "status": "success",
                    "n_genes_km": len(km_results),
                })
            except Exception as e:
                logger.error(f"生存分析失败: {e}")
                results["pipelines"].append({
                    "step": 4, "module": "Survival Analysis",
                    "status": "failed", "error": str(e),
                })
        elif self.run_survival:
            logger.warning("未提供 survival_data，跳过生存分析")
            results["pipelines"].append({
                "step": 4, "module": "Survival Analysis",
                "status": "skipped",
            })

        # ── 汇总 ─────────────────────────────
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        total_steps = len(results["pipelines"])
        success_steps = sum(
            1 for p in results["pipelines"] if p["status"] == "success"
        )

        results["status"] = "completed"
        results["end_time"] = end_time.isoformat()
        results["elapsed_seconds"] = round(elapsed, 2)

        results["summary"] = {
            "data_type": self.data_type,
            "steps_total": total_steps,
            "steps_success": success_steps,
            "steps_failed": total_steps - success_steps,
            "elapsed_seconds": round(elapsed, 2),
            "n_genes_input": expression_data.shape[0],
            "n_samples": expression_data.shape[1],
            "de_genes": len(self._get_genes_for_enrichment(results)),
        }

        # 保存完整结果
        self._save_full_results(results)

        logger.info("=" * 50)
        logger.success(
            f"全流程分析完成: {success_steps}/{total_steps} 步骤成功, "
            f"耗时 {elapsed:.1f}s"
        )
        logger.info("=" * 50)

        return results

    # ── 辅助方法 ──────────────────────────────

    def _get_genes_for_enrichment(self, results: dict[str, Any]) -> list[str]:
        """从结果中提取用于富集分析的显著基因列表。"""
        de = results.get("differential_expression")
        if de is None:
            return []
        significant = de.get("significant", [])
        genes = [g.get("gene", "") for g in significant]
        return [g for g in genes if g]

    def _save_full_results(self, results: dict[str, Any]) -> None:
        """保存分析结果摘要为 JSON。"""
        # 构建可序列化的摘要版本
        serializable = {
            "status": results["status"],
            "data_type": results["data_type"],
            "start_time": results["start_time"],
            "end_time": results.get("end_time", ""),
            "elapsed_seconds": results.get("elapsed_seconds", 0),
            "pipelines": results["pipelines"],
            "summary": results["summary"],
            "visualizations": list(results.get("visualizations", {}).values()),
            "question": results.get("question", {}),
            # DE 摘要
            "de_summary": (
                results["differential_expression"].get("summary")
                if results.get("differential_expression") else None
            ),
            # GO 摘要
            "go_summary": (
                results["enrichment_go"].get("summary")
                if results.get("enrichment_go") else None
            ),
            # KEGG 摘要
            "kegg_summary": (
                results["enrichment_kegg"].get("summary")
                if results.get("enrichment_kegg") else None
            ),
            # 生存分析摘要
            "survival_summary": (
                results.get("survival", {}).get("cox_regression", {}).get("summary")
                if results.get("survival") else None
            ),
        }

        json_path = self._output_dir / "analysis_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"分析总览已保存: {json_path}")
