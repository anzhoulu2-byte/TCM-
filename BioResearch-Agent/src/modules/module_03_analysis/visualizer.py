"""
分析可视化器 (AnalysisVisualizer)。

基于 matplotlib 和 seaborn 生成高分辨率出版级图表：
火山图、表达热图、富集气泡图、KM 生存曲线。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
# 非交互式后端，避免 GUI 弹出
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from loguru import logger

from src.config import get_config

# 全局样式
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.figsize": (8, 6),
})


class AnalysisVisualizer:
    """分析结果可视化器。

    提供火山图、热图、GO 富集图、KM 生存曲线等出版级图表，
    自动保存为 300 DPI 的 PNG 文件。

    Attributes:
        output_dir: 图片保存目录
        style: seaborn 样式（默认 "whitegrid"）
        palette: 配色方案
    """

    def __init__(
        self,
        output_dir: str | None = None,
        style: str = "whitegrid",
        palette: str = "Set2",
    ) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "figures"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        sns.set_theme(style=style, palette=palette)
        self._palette = palette

        logger.info(f"AnalysisVisualizer 初始化: output_dir={self._output_dir}")

    # ── 火山图 ──────────────────────────────

    def volcano_plot(
        self,
        results: dict[str, Any],
        title: str = "Volcano Plot",
        filename: str = "volcano.png",
        log2fc_threshold: float = 1.0,
        pvalue_threshold: float = 0.05,
    ) -> plt.Figure:
        """绘制火山图。

        Args:
            results: DifferentialExpression.analyze() 的输出
            title: 图表标题
            filename: 保存文件名
            log2fc_threshold: log2FC 阈值（虚线标注）
            pvalue_threshold: p-value 阈值（虚线标注）

        Returns:
            matplotlib.figure.Figure
        """
        df = results.get("results")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            logger.warning("火山图数据为空，返回空白图")
            return self._blank_figure("No data for volcano plot")

        fig, ax = plt.subplots(figsize=(8, 6))

        # 确保必要的列存在
        if "log2FC" not in df.columns or "-log10_pvalue" not in df.columns:
            logger.error("数据缺少 log2FC 或 -log10_pvalue 列")
            plt.close()
            return self._blank_figure("Missing required columns")

        log2fc = df["log2FC"].values
        neg_log10p = df["-log10_pvalue"].values
        significant = df.get("significant", pd.Series([False] * len(df))).values

        # 分类绘图
        colors = []
        for sig in significant:
            if sig:
                colors.append("#E74C3C")  # 红色=显著
            else:
                colors.append("#95A5A6")  # 灰色=不显著

        ax.scatter(
            log2fc, neg_log10p, c=colors, alpha=0.6, s=15, edgecolors="none",
        )

        # 阈值线
        ax.axhline(-np.log10(pvalue_threshold), color="blue", linestyle="--",
                    linewidth=0.8, alpha=0.5)
        ax.axvline(-log2fc_threshold, color="blue", linestyle="--",
                    linewidth=0.8, alpha=0.5)
        ax.axvline(log2fc_threshold, color="blue", linestyle="--",
                    linewidth=0.8, alpha=0.5)

        # 标注 top 基因
        if significant.any():
            sig_df = df[significant].head(10)
            for _, row in sig_df.iterrows():
                ax.annotate(
                    row.get("gene", ""),
                    (row["log2FC"], row["-log10_pvalue"]),
                    fontsize=7,
                    alpha=0.8,
                    arrowprops=dict(arrowstyle="-", color="gray", alpha=0.3),
                )

        ax.set_xlabel("log2(Fold Change)", fontsize=11)
        ax.set_ylabel("-log10(p-value)", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")

        # 统计信息
        n_up = int(np.sum((log2fc > log2fc_threshold) & significant))
        n_down = int(np.sum((log2fc < -log2fc_threshold) & significant))
        stats_text = (
            f"Total: {len(df)} | Up: {n_up} | Down: {n_down}"
        )
        ax.text(0.98, 0.95, stats_text, transform=ax.transAxes,
                fontsize=9, ha="right", va="top",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

        self._save_figure(fig, filename)
        logger.info(f"火山图已保存: {filename} (up={n_up}, down={n_down})")
        return fig

    # ── 表达热图 ──────────────────────────────

    def heatmap(
        self,
        expression_data: pd.DataFrame,
        metadata: pd.DataFrame | None = None,
        title: str = "Expression Heatmap",
        filename: str = "heatmap.png",
        top_n: int = 50,
        group_col: str = "group",
        cmap: str = "RdBu_r",
    ) -> plt.Figure:
        """绘制基因表达热图。

        Args:
            expression_data: 表达矩阵（行=基因，列=样本）
            metadata: 样本元数据（用于顶部分组注释条）
            title: 图表标题
            filename: 保存文件名
            top_n: 显示的 top 基因数（按方差排序）
            group_col: 分组列名
            cmap: 颜色映射

        Returns:
            matplotlib.figure.Figure
        """
        if expression_data.empty:
            logger.warning("热图数据为空")
            return self._blank_figure("No data for heatmap")

        # 选择方差最大的 top_n 基因
        gene_vars = expression_data.var(axis=1).sort_values(ascending=False)
        selected_genes = gene_vars.head(min(top_n, len(gene_vars))).index
        plot_data = expression_data.loc[selected_genes]

        # 标准化（Z-score）
        plot_data = plot_data.apply(
            lambda x: (x - x.mean()) / x.std(), axis=1
        ).fillna(0)

        n_genes = len(plot_data)
        n_samples = len(plot_data.columns)
        height = max(4, n_genes * 0.25)
        width = max(6, n_samples * 0.4)

        fig, ax = plt.subplots(figsize=(width, height))

        # 准备颜色注释
        if metadata is not None and group_col in metadata.columns:
            common = plot_data.columns.intersection(metadata.index)
            plot_data = plot_data[common]
            meta = metadata.loc[common]

            # 列注释条
            unique_groups = meta[group_col].unique()
            group_colors = sns.color_palette(self._palette, len(unique_groups))
            lut = dict(zip(unique_groups, group_colors))
            row_colors = meta[group_col].map(lut)

            # 行注释条（基因表达水平示意）
            g = sns.clustermap(
                plot_data,
                cmap=cmap,
                col_cluster=True,
                row_cluster=True,
                col_colors=row_colors,
                figsize=(width, height),
                xticklabels=True,
                yticklabels=True,
                vmin=-3, vmax=3,
                linewidths=0,
                dendrogram_ratio=(0.1, 0.05),
                cbar_pos=(0.02, 0.85, 0.03, 0.12),
            )
            g.ax_heatmap.set_xlabel("Samples")
            g.ax_heatmap.set_ylabel("Genes")
            g.fig.suptitle(title, fontsize=12, fontweight="bold", y=1.02)
            fig = g.fig
        else:
            sns.heatmap(
                plot_data,
                cmap=cmap,
                center=0,
                vmin=-3, vmax=3,
                xticklabels=True,
                yticklabels=True,
                linewidths=0,
                ax=ax,
                cbar_kws={"shrink": 0.6},
            )
            ax.set_xlabel("Samples")
            ax.set_ylabel("Genes")
            ax.set_title(title, fontsize=12, fontweight="bold")

        self._save_figure(fig, filename)
        logger.info(f"热图已保存: {filename} ({n_genes} genes x {n_samples} samples)")
        return fig

    # ── GO 富集气泡图 ─────────────────────────

    def go_plot(
        self,
        enrichment_results: dict[str, Any],
        title: str = "GO Enrichment",
        filename: str = "go_enrichment.png",
        top_n: int = 15,
    ) -> plt.Figure:
        """绘制 GO 富集分析气泡图。

        Args:
            enrichment_results: EnrichmentAnalyzer.go_enrichment() 的输出
            title: 图表标题
            filename: 保存文件名
            top_n: 显示 top N 条通路

        Returns:
            matplotlib.figure.Figure
        """
        combined = enrichment_results.get("combined")
        if combined is None or (isinstance(combined, pd.DataFrame) and combined.empty):
            logger.warning("GO 富集数据为空，返回空白图")
            return self._blank_figure("No enrichment results")

        df = combined.head(top_n).copy()
        if df.empty:
            return self._blank_figure("No enrichment results")

        # 提取 overlap 比例
        def parse_overlap(overlap: str) -> float:
            try:
                parts = str(overlap).split("/")
                return float(parts[0]) / float(parts[1]) if len(parts) == 2 else 0
            except (ValueError, ZeroDivisionError, IndexError):
                return 0

        df["ratio"] = df["Overlap"].apply(parse_overlap)
        df["-log10_padj"] = -np.log10(
            df["Adjusted P-value"].clip(lower=1e-300)
        )
        # 截断 Term 显示
        df["Term_short"] = df["Term"].apply(lambda x: x[:60] + "..." if len(str(x)) > 60 else x)

        # 按 ontology 着色
        fig, ax = plt.subplots(figsize=(9, max(4, len(df) * 0.35)))

        ontology_colors = {"BP": "#E74C3C", "CC": "#3498DB", "MF": "#2ECC71"}
        if "Ontology" in df.columns:
            colors = [ontology_colors.get(o, "#95A5A6") for o in df["Ontology"]]
        else:
            colors = "#3498DB"

        scatter = ax.scatter(
            df["ratio"],
            range(len(df)),
            s=df["-log10_padj"] * 30,
            c=colors,
            alpha=0.7,
            edgecolors="gray",
            linewidth=0.5,
        )

        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df["Term_short"].values, fontsize=8)
        ax.set_xlabel("Gene Ratio (Overlap / Background)", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.invert_yaxis()

        # 图例
        if "Ontology" in df.columns:
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
                       markersize=8, label=ont)
                for ont, c in ontology_colors.items()
                if ont in df["Ontology"].values
            ]
            ax.legend(handles=legend_elements, title="Ontology", loc="lower right")

        self._save_figure(fig, filename)
        logger.info(f"GO 富集图已保存: {filename}")
        return fig

    # ── 生存曲线图 ──────────────────────────

    def km_plot(
        self,
        km_result: dict[str, Any],
        title: str = "Kaplan-Meier Survival Curve",
        filename: str = "km_curve.png",
    ) -> plt.Figure:
        """绘制 Kaplan-Meier 生存曲线。

        Args:
            km_result: SurvivalAnalyzer.kaplan_meier() 的输出
            title: 图表标题
            filename: 保存文件名

        Returns:
            matplotlib.figure.Figure
        """
        fig, ax = plt.subplots(figsize=(7, 5))

        km_high = km_result.get("km_high")
        km_low = km_result.get("km_low")
        logrank = km_result.get("logrank_result", {})

        has_data = False

        if km_high is not None:
            try:
                km_high.plot(ax=ax, color="#E74C3C", label="High expression")
                has_data = True
            except Exception:
                pass

        if km_low is not None:
            try:
                km_low.plot(ax=ax, color="#3498DB", label="Low expression")
                has_data = True
            except Exception:
                pass

        if not has_data:
            plt.close()
            return self._blank_figure("No KM data")

        pval = logrank.get("pvalue", 1.0)
        pval_text = f"Log-rank p = {pval:.2e}" if pval >= 1e-4 else f"Log-rank p < 1e-4"
        ax.text(0.95, 0.95, pval_text, transform=ax.transAxes,
                fontsize=10, ha="right", va="top",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

        ax.set_xlabel("Time (months)", fontsize=11)
        ax.set_ylabel("Survival Probability", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower left", fontsize=10)

        # 在 x 轴底部添加风险人数表（简化版）
        ax.grid(True, alpha=0.3)

        self._save_figure(fig, filename)
        logger.info(f"KM 生存曲线已保存: {filename}")
        return fig

    # ── 内部方法 ──────────────────────────────

    def _save_figure(self, fig: plt.Figure, filename: str) -> None:
        """保存图表为高分辨率 PNG。"""
        output_path = self._output_dir / filename
        fig.savefig(
            str(output_path),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close(fig)

    def _blank_figure(self, message: str) -> plt.Figure:
        """返回带提示信息的空白图。"""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, message, ha="center", va="center",
                fontsize=12, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])
        return fig
