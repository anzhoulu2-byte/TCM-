"""
差异表达分析 (DifferentialExpression)。

基于 scipy.stats 实现 t-test 和 Wilcoxon 秩和检验，
计算 log2 Fold Change 和多重假设检验校正，
支持转录组和单细胞数据两种模式。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from loguru import logger

from src.config import get_config


class DifferentialExpression:
    """差异表达分析器。

    对表达谱数据进行差异分析，支持双分组比较（control vs treatment）。
    自动选择 t-test 或 Wilcoxon 检验，并进行多重假设校正。

    Attributes:
        log2fc_threshold: log2FC 显著性阈值（默认 1.0，即 2 倍变化）
        pvalue_threshold: p-value 显著性阈值（默认 0.05）
        multiple_test_method: 多重检验校正方法（BH / bonferroni）
        data_type: 数据类型 ("bulk" 转录组 / "sc" 单细胞)
        output_dir: 结果保存目录
    """

    def __init__(
        self,
        log2fc_threshold: float = 1.0,
        pvalue_threshold: float = 0.05,
        multiple_test_method: str = "BH",
        data_type: str = "bulk",
        output_dir: str | None = None,
    ) -> None:
        self.log2fc_threshold: float = log2fc_threshold
        self.pvalue_threshold: float = pvalue_threshold
        self.multiple_test_method: str = multiple_test_method.upper()
        self.data_type: str = data_type

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "analysis"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DifferentialExpression 初始化: method={self._method_name()}, "
            f"data_type={data_type}, "
            f"log2FC_threshold={log2fc_threshold}, "
            f"p_threshold={pvalue_threshold}"
        )

    def analyze(
        self,
        expression_data: pd.DataFrame,
        metadata: pd.DataFrame,
        group_col: str = "group",
        control_label: str = "control",
        treatment_label: str = "treatment",
    ) -> dict[str, Any]:
        """执行差异表达分析。

        Args:
            expression_data: 表达矩阵，行=基因，列=样本。
                列名需与 metadata 中的样本索引匹配。
            metadata: 样本元数据，包含分组信息。
                索引=样本名，包含 group_col 列。
            group_col: 分组列名（默认 "group"）
            control_label: 对照组标签（默认 "control"）
            treatment_label: 实验组标签（默认 "treatment"）

        Returns:
            dict 包含:
            - "results" (pd.DataFrame): 全部基因的差异分析结果表
            - "significant" (list[dict]): 显著差异基因列表
            - "summary" (dict): 分析摘要
            - "parameters" (dict): 分析参数
            - "output_files" (dict): 保存的文件路径

        Examples:
            >>> expr = pd.DataFrame(
            ...     {"S1": [10, 20, 5], "S2": [12, 18, 6], "S3": [2, 5, 10], "S4": [3, 6, 8]},
            ...     index=["GeneA", "GeneB", "GeneC"]
            ... )
            >>> meta = pd.DataFrame(
            ...     {"group": ["control", "control", "treatment", "treatment"]},
            ...     index=["S1", "S2", "S3", "S4"]
            ... )
            >>> de = DifferentialExpression()
            >>> result = de.analyze(expr, meta)
            >>> "significant" in result
            True
        """
        logger.info("开始差异表达分析...")

        # ── 数据校验 ──────────────────────────
        try:
            expression_data, metadata = self._validate_inputs(
                expression_data, metadata, group_col
            )
        except ValueError as e:
            logger.error(f"数据校验失败: {e}")
            return self._empty_result(str(e))

        # ── 分离分组 ──────────────────────────
        control_samples = metadata[metadata[group_col] == control_label].index
        treatment_samples = metadata[metadata[group_col] == treatment_label].index

        if len(control_samples) < 2 or len(treatment_samples) < 2:
            logger.error(
                f"样本数量不足: control={len(control_samples)}, "
                f"treatment={len(treatment_samples)} (至少各需 2 个)"
            )
            return self._empty_result("样本数量不足")

        logger.info(f"对照组: {len(control_samples)} 样本, "
                     f"实验组: {len(treatment_samples)} 样本")

        ctrl_data = expression_data[control_samples]
        treat_data = expression_data[treatment_samples]

        # ── 逐基因检验 ────────────────────────
        test_method = self._get_test_method()
        results_rows: list[dict[str, Any]] = []

        for gene in expression_data.index:
            try:
                ctrl_vals = ctrl_data.loc[gene].dropna().values.astype(float)
                treat_vals = treat_data.loc[gene].dropna().values.astype(float)

                if len(ctrl_vals) < 2 or len(treat_vals) < 2:
                    continue

                # 计算 log2 Fold Change
                ctrl_mean = np.mean(ctrl_vals)
                treat_mean = np.mean(treat_vals)
                # 伪计数避免 log(0)
                log2fc = np.log2(
                    (treat_mean + 1e-10) / (ctrl_mean + 1e-10)
                )

                # 统计检验
                if test_method == "ttest":
                    stat, pval = stats.ttest_ind(treat_vals, ctrl_vals)
                else:
                    stat, pval = stats.mannwhitneyu(
                        treat_vals, ctrl_vals, alternative="two-sided"
                    )

                results_rows.append({
                    "gene": gene,
                    "control_mean": float(f"{ctrl_mean:.4f}"),
                    "treatment_mean": float(f"{treat_mean:.4f}"),
                    "log2FC": float(f"{log2fc:.4f}"),
                    "statistic": float(f"{stat:.4f}"),
                    "pvalue": float(pval),
                    "-log10_pvalue": float(f"{-np.log10(max(pval, 1e-300)):.4f}"),
                })
            except Exception as e:
                logger.debug(f"基因 {gene} 分析跳过: {e}")
                continue

        if not results_rows:
            logger.warning("未计算出有效的差异表达结果")
            return self._empty_result("无有效分析结果")

        results_df = pd.DataFrame(results_rows)

        # ── 多重检验校正 ──────────────────────
        results_df["pvalue_adjusted"] = self._multiple_test_correction(
            results_df["pvalue"].values
        )
        results_df["-log10_padj"] = -np.log10(
            np.clip(results_df["pvalue_adjusted"], 1e-300, None)
        )

        # ── 标记显著基因 ──────────────────────
        results_df["significant"] = (
            (results_df["pvalue_adjusted"] < self.pvalue_threshold)
            & (results_df["log2FC"].abs() > self.log2fc_threshold)
        )

        # 按 p-adjusted 排序
        results_df = results_df.sort_values("pvalue_adjusted").reset_index(drop=True)

        # ── 输出 ─────────────────────────────
        sig_df = results_df[results_df["significant"] == True]
        significant_genes = sig_df.to_dict("records")

        # 保存文件
        output_files = self._save_results(results_df, sig_df)

        summary = {
            "total_genes_tested": len(results_df),
            "significant_genes": int(sig_df.shape[0]),
            "upregulated": int(np.sum(sig_df["log2FC"] > 0)),
            "downregulated": int(np.sum(sig_df["log2FC"] < 0)),
            "test_method": self._method_name(),
            "multiple_test_method": self.multiple_test_method,
            "pvalue_threshold": self.pvalue_threshold,
            "log2fc_threshold": self.log2fc_threshold,
        }

        logger.success(
            f"差异分析完成: {summary['total_genes_tested']} 基因, "
            f"{summary['significant_genes']} 显著 "
            f"(上调 {summary['upregulated']}, 下调 {summary['downregulated']})"
        )

        # 构建符合 schemas.py GeneResult 格式的显著基因列表
        gene_results = [
            {
                "gene_symbol": row["gene"],
                "gene_id": "",
                "score": abs(row["log2FC"]),
                "evidence": [
                    f"log2FC={row['log2FC']:.2f}",
                    f"p-adj={row['pvalue_adjusted']:.2e}",
                ],
            }
            for row in significant_genes
        ]

        return {
            "results": results_df,
            "significant": significant_genes,
            "gene_results": gene_results,
            "summary": summary,
            "parameters": {
                "log2fc_threshold": self.log2fc_threshold,
                "pvalue_threshold": self.pvalue_threshold,
                "multiple_test_method": self.multiple_test_method,
                "data_type": self.data_type,
                "test_method": self._method_name(),
            },
            "output_files": output_files,
        }

    # ── 内部方法 ──────────────────────────────

    def _validate_inputs(
        self,
        expression_data: pd.DataFrame,
        metadata: pd.DataFrame,
        group_col: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """校验并对齐输入数据。"""
        # 确保基因名不重复
        if expression_data.index.duplicated().any():
            logger.warning("基因索引存在重复，保留首次出现")
            expression_data = expression_data[~expression_data.index.duplicated(keep="first")]

        # 对齐样本
        common_samples = expression_data.columns.intersection(metadata.index)
        if len(common_samples) == 0:
            raise ValueError("expression_data 列名与 metadata 索引无交集")

        expression_data = expression_data[common_samples]
        metadata = metadata.loc[common_samples]

        # 确保数据为数值型
        expression_data = expression_data.apply(pd.to_numeric, errors="coerce")

        return expression_data, metadata

    def _get_test_method(self) -> str:
        """根据数据类型和样本量选择检验方法。

        - 单细胞数据 (sc) 优先使用 Wilcoxon
        - 样本量较小 (<30) 用 Wilcoxon，否则用 t-test
        """
        if self.data_type == "sc":
            return "wilcoxon"
        return "ttest"

    def _method_name(self) -> str:
        """返回当前使用的检验方法名称。"""
        methods = {"ttest": "Independent t-test", "wilcoxon": "Mann-Whitney U"}
        return methods.get(self._get_test_method(), self._get_test_method())

    def _multiple_test_correction(self, pvalues: np.ndarray) -> np.ndarray:
        """多重假设检验校正。

        Args:
            pvalues: 原始 p-values 数组

        Returns:
            校正后的 p-values
        """
        n = len(pvalues)
        if n == 0:
            return np.array([])

        if self.multiple_test_method == "BONFERRONI":
            return np.minimum(pvalues * n, 1.0)

        # Benjamini-Hochberg (BH / FDR)
        sorted_indices = np.argsort(pvalues, kind="mergesort")
        sorted_pvals = pvalues[sorted_indices]
        ranks = np.arange(1, n + 1)
        sorted_corrected = np.minimum(sorted_pvals * n / ranks, 1.0)

        # 保证单调性
        for i in range(n - 2, -1, -1):
            sorted_corrected[i] = min(sorted_corrected[i], sorted_corrected[i + 1])

        corrected = np.empty(n)
        corrected[sorted_indices] = sorted_corrected
        return corrected

    def _save_results(
        self, results_df: pd.DataFrame, sig_df: pd.DataFrame
    ) -> dict[str, str]:
        """保存结果为 CSV 和 JSON 格式。

        Returns:
            dict: {"csv": path, "json": path, "significant_csv": path}
        """
        output_files: dict[str, str] = {}

        # 全部结果 CSV
        csv_path = self._output_dir / "differential_expression.csv"
        results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        output_files["csv"] = str(csv_path)

        # 显著基因 CSV
        sig_csv_path = self._output_dir / "significant_genes.csv"
        sig_df.to_csv(sig_csv_path, index=False, encoding="utf-8-sig")
        output_files["significant_csv"] = str(sig_csv_path)

        # 显著基因 JSON
        json_path = self._output_dir / "significant_genes.json"
        sig_df.to_json(json_path, orient="records", force_ascii=False)
        output_files["json"] = str(json_path)

        logger.debug(f"差异分析结果保存至: {self._output_dir}")
        return output_files

    def _empty_result(self, reason: str) -> dict[str, Any]:
        """返回空结果。"""
        return {
            "results": pd.DataFrame(),
            "significant": [],
            "gene_results": [],
            "summary": {
                "total_genes_tested": 0,
                "significant_genes": 0,
                "upregulated": 0,
                "downregulated": 0,
                "error": reason,
            },
            "parameters": {},
            "output_files": {},
        }
