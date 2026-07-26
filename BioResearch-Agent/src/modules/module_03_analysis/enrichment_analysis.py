"""
通路富集分析 (EnrichmentAnalyzer)。

基于 gseapy 库执行基因集富集分析，
支持 GO (BP/CC/MF) 和 KEGG 通路富集。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.config import get_config


class EnrichmentAnalyzer:
    """通路富集分析器。

    对差异基因列表执行 GO 和 KEGG 富集分析，
    支持多个 GO 子本体（BP / CC / MF）。

    Attributes:
        organism: 物种（默认 "human"）
        background: 背景基因列表（None 则使用全基因组背景）
        pvalue_cutoff: p-value 阈值（默认 0.05）
        output_dir: 结果输出目录
    """

    # 常见物种的 gseapy 基因集库名
    ORGANISM_MAP = {
        "human": "human",
        "mouse": "mouse",
        "rat": "rat",
        "zebrafish": "zebrafish",
    }

    # GO 子本体
    GO_ONTOLOGIES = ["BP", "CC", "MF"]

    def __init__(
        self,
        organism: str = "human",
        background: list[str] | None = None,
        pvalue_cutoff: float = 0.05,
        output_dir: str | None = None,
    ) -> None:
        self.organism: str = self.ORGANISM_MAP.get(organism.lower(), organism)
        self.background: list[str] | None = background
        self.pvalue_cutoff: float = pvalue_cutoff

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "analysis" / "enrichment"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 延迟导入 gseapy（它可能在部分环境中不可用）
        self._gseapy = None

        logger.info(
            f"EnrichmentAnalyzer 初始化: organism={self.organism}, "
            f"pvalue_cutoff={pvalue_cutoff}"
        )

    @property
    def _gs(self):
        """延迟加载 gseapy 模块。"""
        if self._gseapy is None:
            try:
                import gseapy as gs
                self._gseapy = gs
            except ImportError:
                logger.warning("gseapy 未安装，富集分析功能不可用")
                return None
        return self._gseapy

    # ── GO 富集分析 ──────────────────────────

    def go_enrichment(
        self,
        genes: list[str],
        ontologies: list[str] | None = None,
    ) -> dict[str, Any]:
        """执行 GO 富集分析。

        Args:
            genes: 待分析的基因符号列表
            ontologies: GO 子本体列表，默认 BP / CC / MF 全部

        Returns:
            dict 包含:
            - "BP" / "CC" / "MF" (pd.DataFrame): 各本体富集结果
            - "combined" (pd.DataFrame): 合并结果
            - "summary" (dict): 分析摘要
            - "output_files" (dict): 保存的文件路径

        Examples:
            >>> analyzer = EnrichmentAnalyzer()
            >>> genes = ["TP53", "EGFR", "BRCA1", "MYC", "VEGFA"]
            >>> result = analyzer.go_enrichment(genes)
            >>> "summary" in result
            True
        """
        if not self._gs:
            return self._empty_result("gseapy 未安装")

        genes = self._deduplicate(genes)
        onts = ontologies or self.GO_ONTOLOGIES

        logger.info(f"GO 富集分析: {len(genes)} 基因, ontologies={onts}")

        results: dict[str, pd.DataFrame] = {}
        all_results: list[pd.DataFrame] = []

        for ont in onts:
            try:
                logger.debug(f"运行 GO-{ont} 富集...")
                enr = self._gs.enrichr(
                    gene_list=genes,
                    gene_sets=f"GO_{ont}_2023",
                    organism=self.organism,
                    outdir=None,  # 不自动保存
                    no_plot=True,
                    cutoff=self.pvalue_cutoff,
                )

                if enr.results is not None and not enr.results.empty:
                    df = enr.results.copy()
                    df["Ontology"] = ont
                    df = df.sort_values("Adjusted P-value")
                    results[ont] = df
                    all_results.append(df)
                    logger.debug(f"GO-{ont}: {len(df)} 条显著通路")
                else:
                    results[ont] = pd.DataFrame()
                    logger.debug(f"GO-{ont}: 无显著结果")

            except Exception as e:
                logger.warning(f"GO-{ont} 富集失败: {e}")
                results[ont] = pd.DataFrame()

        # 合并结果
        combined = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        if not combined.empty:
            combined = combined.sort_values("Adjusted P-value")

        # 保存
        output_files = self._save_results(results, combined, "GO")

        top_terms = (
            combined.head(20).to_dict("records")
            if not combined.empty
            else []
        )

        summary = {
            "ontology": onts,
            "total_genes_input": len(genes),
            "total_significant_terms": len(combined),
            "top_terms": [
                {
                    "term": t.get("Term", ""),
                    "pvalue": f"{t.get('P-value', 1):.2e}",
                    "padj": f"{t.get('Adjusted P-value', 1):.2e}",
                    "overlap": t.get("Overlap", ""),
                    "ontology": t.get("Ontology", ""),
                }
                for t in top_terms[:10]
            ],
        }

        logger.success(
            f"GO 富集完成: {summary['total_significant_terms']} 条显著通路"
        )

        return {
            "BP": results.get("BP", pd.DataFrame()),
            "CC": results.get("CC", pd.DataFrame()),
            "MF": results.get("MF", pd.DataFrame()),
            "combined": combined,
            "summary": summary,
            "output_files": output_files,
        }

    # ── KEGG 富集分析 ────────────────────────

    def kegg_enrichment(
        self,
        genes: list[str],
    ) -> dict[str, Any]:
        """执行 KEGG 通路富集分析。

        Args:
            genes: 待分析的基因符号列表

        Returns:
            dict 包含:
            - "results" (pd.DataFrame): 富集结果
            - "summary" (dict): 分析摘要
            - "output_files" (dict): 保存的文件路径

        Examples:
            >>> analyzer = EnrichmentAnalyzer()
            >>> genes = ["TP53", "EGFR", "BRCA1"]
            >>> result = analyzer.kegg_enrichment(genes)
            >>> "summary" in result
            True
        """
        if not self._gs:
            return self._empty_result("gseapy 未安装")

        genes = self._deduplicate(genes)
        logger.info(f"KEGG 富集分析: {len(genes)} 基因")

        try:
            enr = self._gs.enrichr(
                gene_list=genes,
                gene_sets="KEGG_2021_Human",
                organism=self.organism,
                outdir=None,
                no_plot=True,
                cutoff=self.pvalue_cutoff,
            )

            if enr.results is not None and not enr.results.empty:
                results_df = enr.results.sort_values("Adjusted P-value")

                # 为兼容新旧版本 gseapy，标准化列名
                if "Genes" in results_df.columns:
                    results_df.rename(columns={"Genes": "Genes_List"}, inplace=True)
            else:
                results_df = pd.DataFrame()

        except Exception as e:
            logger.error(f"KEGG 富集失败: {e}")
            return self._empty_result(str(e))

        output_files = self._save_results(
            {"KEGG": results_df} if not results_df.empty else {},
            results_df,
            "KEGG",
        )

        top_pathways = (
            results_df.head(20).to_dict("records") if not results_df.empty else []
        )

        summary = {
            "total_genes_input": len(genes),
            "total_significant_pathways": len(results_df),
            "top_pathways": [
                {
                    "term": p.get("Term", ""),
                    "pvalue": f"{p.get('P-value', 1):.2e}",
                    "padj": f"{p.get('Adjusted P-value', 1):.2e}",
                    "overlap": p.get("Overlap", ""),
                }
                for p in top_pathways[:10]
            ],
        }

        logger.success(
            f"KEGG 富集完成: {summary['total_significant_pathways']} 条显著通路"
        )

        return {
            "results": results_df,
            "summary": summary,
            "output_files": output_files,
        }

    # ── 内部方法 ──────────────────────────────

    def _deduplicate(self, genes: list[str]) -> list[str]:
        """去重并过滤空值。"""
        return list(dict.fromkeys([g.strip().upper() for g in genes if g and g.strip()]))

    def _save_results(
        self,
        ont_results: dict[str, pd.DataFrame],
        combined: pd.DataFrame,
        prefix: str,
    ) -> dict[str, str]:
        """保存富集结果为 CSV 和 JSON。"""
        files: dict[str, str] = {}

        if not combined.empty:
            csv_path = self._output_dir / f"{prefix.lower()}_enrichment.csv"
            combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
            files["csv"] = str(csv_path)

            # 也可以用 orient="records" 保存 JSON 摘要
            top = combined.head(50).to_dict("records")
            json_path = self._output_dir / f"{prefix.lower()}_enrichment.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(top, f, ensure_ascii=False, indent=2)
            files["json"] = str(json_path)

        # 各子本体分别保存
        for ont, df in ont_results.items():
            if not df.empty:
                ont_csv = self._output_dir / f"go_{ont.lower()}.csv"
                df.to_csv(ont_csv, index=False, encoding="utf-8-sig")
                files[f"{ont}_csv"] = str(ont_csv)

        return files

    def _empty_result(self, reason: str) -> dict[str, Any]:
        return {
            "BP": pd.DataFrame(),
            "CC": pd.DataFrame(),
            "MF": pd.DataFrame(),
            "combined": pd.DataFrame(),
            "results": pd.DataFrame(),
            "summary": {"error": reason, "total_significant_terms": 0},
            "output_files": {},
        }
