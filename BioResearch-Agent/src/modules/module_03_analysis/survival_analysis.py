"""
生存分析 (SurvivalAnalyzer)。

基于 lifelines 库实现 Kaplan-Meier 生存曲线和 Cox 比例风险回归，
评估基因表达对患者预后的影响。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.config import get_config


class SurvivalAnalyzer:
    """生存分析器。

    支持 Kaplan-Meier 分层分析和 Cox 比例风险回归模型，
    用于评估基因表达水平与患者生存时间的关联。

    Attributes:
        duration_col: 生存时间列名
        event_col: 事件列名（1=事件发生，0=删失）
        output_dir: 结果保存目录
    """

    def __init__(
        self,
        duration_col: str = "survival_time",
        event_col: str = "event",
        output_dir: str | None = None,
    ) -> None:
        self.duration_col: str = duration_col
        self.event_col: str = event_col

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "analysis" / "survival"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 延迟导入 lifelines
        self._lifelines = None

        logger.info(
            f"SurvivalAnalyzer 初始化: duration_col={duration_col}, "
            f"event_col={event_col}"
        )

    @property
    def _ll(self):
        if self._lifelines is None:
            try:
                import lifelines as ll
                self._lifelines = ll
            except ImportError:
                logger.warning("lifelines 未安装，生存分析功能不可用")
                return None
        return self._lifelines

    # ── Kaplan-Meier 分析 ─────────────────────

    def kaplan_meier(
        self,
        expression_data: pd.DataFrame,
        survival_data: pd.DataFrame,
        gene: str,
        high_low_percentile: float = 50.0,
    ) -> dict[str, Any]:
        """对单个基因执行 Kaplan-Meier 生存分析。

        根据基因表达值将患者分为高/低表达两组，
        比较两组间的生存差异。

        Args:
            expression_data: 表达矩阵，行=基因，列=样本
            survival_data: 生存数据，索引=样本，
                包含 duration_col 和 event_col 两列
            gene: 目标基因符号
            high_low_percentile: 分组百分位阈值（默认 50，即中位数分组）

        Returns:
            dict 包含：
            - "km_model": lifelines KaplanMeierFitter
            - "logrank_result" (dict): Log-rank 检验统计量
            - "summary" (dict): 分析摘要
            - "output_files" (dict): 保存的文件路径

        Examples:
            >>> analyzer = SurvivalAnalyzer()
            >>> expr = pd.DataFrame({"S1": [10], "S2": [2], "S3": [8], "S4": [1]}, index=["GeneX"])
            >>> surv = pd.DataFrame(
            ...     {"survival_time": [12, 6, 24, 3], "event": [1, 1, 0, 1]},
            ...     index=["S1", "S2", "S3", "S4"]
            ... )
            >>> result = analyzer.kaplan_meier(expr, surv, "GeneX")
            >>> "logrank_result" in result
            True
        """
        if not self._ll:
            return self._empty_result("lifelines 未安装")

        if gene not in expression_data.index:
            logger.error(f"基因 {gene} 不在表达矩阵中")
            return self._empty_result(f"基因 {gene} 未找到")

        logger.info(f"Kaplan-Meier 分析: gene={gene}, percentile={high_low_percentile}%")

        try:
            # 对齐数据
            common = expression_data.columns.intersection(survival_data.index)
            if len(common) == 0:
                return self._empty_result("数据无交集")

            gene_expr = expression_data.loc[gene, common]
            surv = survival_data.loc[common].copy()

            # 按表达值分组
            threshold = np.percentile(gene_expr, high_low_percentile)
            surv["group"] = np.where(gene_expr >= threshold, "high", "low")
            group_counts = surv["group"].value_counts().to_dict()

            logger.debug(f"分组: high={group_counts.get('high', 0)}, "
                         f"low={group_counts.get('low', 0)}")

            # Kaplan-Meier 拟合
            kmf = self._ll.KaplanMeierFitter()
            km_results: dict[str, Any] = {}

            for group_name in ["high", "low"]:
                mask = surv["group"] == group_name
                if mask.sum() < 2:
                    continue
                kmf.fit(
                    durations=surv.loc[mask, self.duration_col],
                    event_observed=surv.loc[mask, self.event_col],
                    label=group_name,
                )
                # 提取中位生存时间
                median_survival = kmf.median_survival_time_
                km_results[group_name] = {
                    "n": int(mask.sum()),
                    "median_survival": float(median_survival) if not np.isnan(median_survival) else None,
                }

            # Log-rank 检验
            from lifelines.statistics import multivariate_logrank_test

            logrank = multivariate_logrank_test(
                durations=surv[self.duration_col],
                groups=surv["group"],
                event_observed=surv[self.event_col],
            )

            logrank_result = {
                "test_statistic": float(f"{logrank.test_statistic:.4f}"),
                "pvalue": float(logrank.p_value),
                "-log10_pvalue": float(f"{-np.log10(max(logrank.p_value, 1e-300)):.4f}"),
            }

            # 分类 Kaplan-Meier 模型（用于绘图）
            # 创建两个独立的 KMF 模型
            km_high = self._ll.KaplanMeierFitter()
            km_low = self._ll.KaplanMeierFitter()

            high_mask = surv["group"] == "high"
            low_mask = surv["group"] == "low"

            if high_mask.sum() >= 2:
                km_high.fit(surv.loc[high_mask, self.duration_col],
                            surv.loc[high_mask, self.event_col], label="high")
            if low_mask.sum() >= 2:
                km_low.fit(surv.loc[low_mask, self.duration_col],
                           surv.loc[low_mask, self.event_col], label="low")

            # 保存结果
            output_files = self._save_km_results(gene, logrank_result, group_counts)

            summary = {
                "gene": gene,
                "threshold": float(f"{threshold:.4f}"),
                "percentile": high_low_percentile,
                "groups": km_results,
                "logrank_pvalue": logrank_result["pvalue"],
                "significant": logrank_result["pvalue"] < 0.05,
            }

            logger.success(
                f"KM 分析完成: gene={gene}, "
                f"logrank_p={logrank_result['pvalue']:.2e}"
            )

            return {
                "km_high": km_high,
                "km_low": km_low,
                "logrank_result": logrank_result,
                "summary": summary,
                "output_files": output_files,
            }

        except Exception as e:
            logger.error(f"Kaplan-Meier 分析失败: {e}")
            return self._empty_result(str(e))

    # ── Cox 回归分析 ──────────────────────────

    def cox_regression(
        self,
        expression_data: pd.DataFrame,
        survival_data: pd.DataFrame,
        genes: list[str],
    ) -> dict[str, Any]:
        """对多个基因执行 Cox 比例风险回归。

        Args:
            expression_data: 表达矩阵，行=基因，列=样本
            survival_data: 生存数据
            genes: 待分析的基因符号列表

        Returns:
            dict 包含：
            - "cox_model": lifelines CoxPHFitter
            - "results" (pd.DataFrame): 各基因的 HR、CI、p-value
            - "summary" (dict): 分析摘要
            - "output_files" (dict): 保存的文件路径

        Examples:
            >>> analyzer = SurvivalAnalyzer()
            >>> expr = pd.DataFrame({"S1": [10, 5], "S2": [2, 8]}, index=["GeneX", "GeneY"])
            >>> surv = pd.DataFrame(
            ...     {"survival_time": [12, 6], "event": [1, 1]},
            ...     index=["S1", "S2"]
            ... )
            >>> result = analyzer.cox_regression(expr, surv, ["GeneX", "GeneY"])
            >>> "results" in result
            True
        """
        if not self._ll:
            return self._empty_result("lifelines 未安装")

        valid_genes = [g for g in genes if g in expression_data.index]
        if not valid_genes:
            logger.warning("所有基因均不在表达矩阵中")
            return self._empty_result("基因未找到")

        logger.info(f"Cox 回归分析: {len(valid_genes)} 基因")

        try:
            # 构建分析 DataFrame
            common = expression_data.columns.intersection(survival_data.index)
            expr_subset = expression_data.loc[valid_genes, common].T
            expr_subset.columns.name = None

            # 合并表达 + 生存数据
            df = survival_data.loc[common].join(expr_subset, how="inner").dropna()

            if df.empty or df.shape[0] < 10:
                return self._empty_result(f"有效样本不足 (n={df.shape[0]}, 需要 ≥10)")

            # 单变量 Cox 回归
            cph = self._ll.CoxPHFitter()
            cox_data = df[[self.duration_col, self.event_col] + valid_genes]

            cph.fit(cox_data, duration_col=self.duration_col, event_col=self.event_col)

            # 提取结果
            summary_df = cph.summary
            results_list = []
            for gene_name in valid_genes:
                if gene_name in summary_df.index:
                    row = summary_df.loc[gene_name]
                    results_list.append({
                        "gene": gene_name,
                        "coef": float(f"{row['coef']:.4f}"),
                        "exp_coef_hr": float(f"{row['exp(coef)']:.4f}"),
                        "se_coef": float(f"{row['se(coef)']:.4f}"),
                        "pvalue": float(row["p"]),
                        "ci_lower": float(f"{row['exp(coef) lower 95%']:.4f}"),
                        "ci_upper": float(f"{row['exp(coef) upper 95%']:.4f}"),
                    })

            results_df = pd.DataFrame(results_list).sort_values("pvalue")

            # 保存
            output_files = self._save_cox_results(results_df)

            significant_genes = results_df[results_df["pvalue"] < 0.05]
            summary = {
                "n_samples": cph.data.shape[0],
                "n_genes": len(valid_genes),
                "n_events": int(cph.event_observed.sum()),
                "concordance_index": float(f"{cph.concordance_index_:.4f}"),
                "significant_genes": int(len(significant_genes)),
                "log_likelihood": float(f"{cph.log_likelihood_:.2f}"),
                "significant_results": significant_genes.to_dict("records"),
            }

            logger.success(
                f"Cox 回归完成: {summary['significant_genes']}/{summary['n_genes']} 显著, "
                f"C-index={summary['concordance_index']}"
            )

            return {
                "cox_model": cph,
                "results": results_df,
                "summary": summary,
                "output_files": output_files,
            }

        except Exception as e:
            logger.error(f"Cox 回归分析失败: {e}")
            return self._empty_result(str(e))

    # ── 内部方法 ──────────────────────────────

    def _save_km_results(
        self,
        gene: str,
        logrank: dict,
        group_counts: dict[str, int],
    ) -> dict[str, str]:
        """保存 KM 分析结果。"""
        files: dict[str, str] = {}
        data = {
            "gene": gene,
            "logrank_statistic": logrank["test_statistic"],
            "logrank_pvalue": logrank["pvalue"],
            "group_counts": group_counts,
        }
        json_path = self._output_dir / f"km_{gene}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        files["json"] = str(json_path)
        return files

    def _save_cox_results(self, results_df: pd.DataFrame) -> dict[str, str]:
        """保存 Cox 回归结果。"""
        files: dict[str, str] = {}
        csv_path = self._output_dir / "cox_regression.csv"
        results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        files["csv"] = str(csv_path)

        json_path = self._output_dir / "cox_regression.json"
        results_df.to_json(json_path, orient="records", force_ascii=False)
        files["json"] = str(json_path)
        return files

    def _empty_result(self, reason: str) -> dict[str, Any]:
        return {
            "km_high": None,
            "km_low": None,
            "cox_model": None,
            "logrank_result": {"test_statistic": 0, "pvalue": 1.0},
            "results": pd.DataFrame(),
            "summary": {"error": reason},
            "output_files": {},
        }
