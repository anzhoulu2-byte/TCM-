"""
报告生成器 (ReportGenerator)。

整合所有模块的分析结果，生成结构化研究报告。
支持摘要模式、完整 Markdown 模式和 HTML 模式，
图表自动内嵌，格式符合学术期刊投稿标准。

报告结构：
1. 研究背景与问题
2. 方法概述
3. 结果展示（含图表）
4. 候选靶点列表
5. 推荐实验方案
6. 溯源记录
7. 局限性分析
8. 参考文献
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.config import get_config


class ReportGenerator:
    """结构化研究报告生成器。

    整合全流程分析结果，生成摘要 / 完整 Markdown / HTML 三种格式报告。
    HTML 报告内嵌图表，样式符合学术出版标准。

    Attributes:
        output_dir: 报告输出目录
    """

    # ── CSS 样式（学术期刊风格） ──────────────
    HTML_STYLE = """
    <style>
        @page { size: A4; margin: 2.5cm; }
        body {
            font-family: 'Times New Roman', Times, serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #000;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { font-size: 20pt; text-align: center; margin-top: 30px; margin-bottom: 10px; }
        h2 { font-size: 16pt; border-bottom: 1px solid #333; padding-bottom: 5px;
             margin-top: 30px; color: #1a1a1a; }
        h3 { font-size: 14pt; margin-top: 20px; color: #333; }
        table {
            width: 100%; border-collapse: collapse; margin: 15px 0;
            font-size: 10pt;
        }
        th, td { border: 1px solid #999; padding: 8px; text-align: left; }
        th { background-color: #f0f0f0; font-weight: bold; }
        tr:nth-child(even) { background-color: #fafafa; }
        .header-meta { text-align: center; color: #666; font-size: 10pt; margin-top: 5px; }
        .figure { text-align: center; margin: 20px 0; }
        .figure img { max-width: 90%; height: auto; border: 1px solid #ddd; border-radius: 4px; }
        .figure-caption { font-size: 10pt; color: #555; margin-top: 5px; }
        .abstract {
            background: #f9f9f9; padding: 15px; border-left: 4px solid #3498DB;
            margin: 20px 0; font-style: italic;
        }
        .evidence-chain { background: #fefefe; padding: 10px; border: 1px solid #e0e0e0;
                          margin: 10px 0; font-size: 10pt; }
        .limitation { background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107;
                      margin: 10px 0; }
        .recommendation { background: #d4edda; padding: 10px; border-left: 4px solid #28a745;
                          margin: 10px 0; }
        .toc { background: #fff; padding: 15px; border: 1px solid #ddd; margin: 20px 0; }
        .toc a { color: #333; text-decoration: none; }
        .toc a:hover { text-decoration: underline; }
        .ref { font-size: 10pt; padding-left: 20px; text-indent: -20px; margin: 5px 0; }
        @media print {
            body { padding: 0; }
            .page-break { page-break-before: always; }
        }
    </style>
    """

    def __init__(self, output_dir: str | None = None) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "reports"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ReportGenerator 初始化完成")

    # ── 摘要模式 ──────────────────────────────

    def generate_summary(self, results: dict[str, Any]) -> str:
        """生成研究摘要（Markdown 格式，约 300-500 词）。

        Args:
            results: 从模块 1-5 收集的结果字典

        Returns:
            学术风格的研究摘要 Markdown 文本
        """
        question = results.get("question", {})
        disease = question.get("disease", "target disease")
        de = results.get("differential_expression", {})
        de_summary = de.get("summary", {}) if isinstance(de, dict) else {}
        go_result = results.get("enrichment_go", {})
        go_summary = go_result.get("summary", {}) if isinstance(go_result, dict) else {}
        targets = results.get("targets", {})
        targets_summary = targets.get("summary", {}) if isinstance(targets, dict) else {}

        return (
            f"## Abstract\n\n"
            f"**Background:** This study aims to identify and prioritize therapeutic "
            f"targets for {disease} using an integrated multi-omics and "
            f"AI-driven approach.\n\n"
            f"**Methods:** We employed differential expression analysis, "
            f"pathway enrichment (GO/KEGG), multi-agent reasoning, and "
            f"multi-dimensional target scoring to systematically evaluate "
            f"candidate genes.\n\n"
            f"**Results:** "
            f"{de_summary.get('significant_genes', 'N/A')} significantly "
            f"differentially expressed genes were identified "
            f"({de_summary.get('upregulated', 'N/A')} up, "
            f"{de_summary.get('downregulated', 'N/A')} down). "
            f"GO enrichment revealed "
            f"{go_summary.get('total_significant_terms', 'N/A')} significant terms. "
            f"{targets_summary.get('top_candidates', 'N/A')} top target "
            f"candidates were prioritized.\n\n"
            f"**Conclusion:** Our integrated analysis provides a comprehensive "
            f"landscape of potential therapeutic targets for {disease}, "
            f"with top candidates warranting further experimental validation.\n\n"
            f"**Keywords:** {disease}, biomarker discovery, drug target, "
            f"multi-omics, AI-driven analysis\n"
            f"---\n"
        )

    # ── 完整 Markdown 报告 ────────────────────

    def generate_full_report(self, results: dict[str, Any]) -> str:
        """生成完整的研究报告（Markdown 格式）。

        Args:
            results: 全流程分析结果字典

        Returns:
            Markdown 格式的完整报告文本
        """
        sections = []

        # ── 标题页 ──────────────────────────
        question = results.get("question", {})
        disease = question.get("disease", "Target Disease")
        sections.append(self._format_title(disease, results))

        # ── 目录 ────────────────────────────
        sections.append(self._format_toc())

        # ── 1. 研究背景与问题 ──────────────────
        sections.append(self._format_background(question))

        # ── 2. 方法概述 ──────────────────────
        sections.append(self._format_methods(results))

        # ── 3. 结果展示 ──────────────────────
        sections.append(self._format_results(results))

        # ── 4. 候选靶点列表 ────────────────────
        sections.append(self._format_targets(results))

        # ── 5. 推荐实验方案 ────────────────────
        sections.append(self._format_protocol(results))

        # ── 6. 溯源记录 ──────────────────────
        sections.append(self._format_traceability(results))

        # ── 7. 局限性分析 ────────────────────
        sections.append(self._format_limitations())

        # ── 8. 参考文献 ──────────────────────
        sections.append(self._format_references(results))

        # ── 附录 ────────────────────────────
        sections.append(self._format_appendix(results))

        full_report = "\n\n".join(sections)
        return full_report

    # ── HTML 报告 ──────────────────────────────

    def generate_html_report(self, results: dict[str, Any]) -> str:
        """生成 HTML 格式的研究报告。

        包含完整的学术期刊风格 CSS 样式和内嵌图表。

        Args:
            results: 全流程分析结果字典

        Returns:
            HTML 格式的完整报告
        """
        md_content = self.generate_full_report(results)

        # 将 Markdown 转换为 HTML
        html_body = self._md_to_html(md_content)

        # 嵌入图表
        figures_html = self._embed_figures(results)

        # 插入图表到对应位置
        if figures_html:
            html_body = html_body.replace("<!--FIGURES-->", figures_html)

        html = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>BioResearch-Agent Research Report</title>\n"
            f"{self.HTML_STYLE}\n"
            "</head>\n<body>\n"
            f"{html_body}\n"
            "</body>\n</html>"
        )
        return html

    # ── 各章节格式化 ──────────────────────────

    def _format_title(self, disease: str, results: dict) -> str:
        """格式化标题页。"""
        now = datetime.now().strftime("%Y-%m-%d")
        return (
            f"# Integrated Multi-Omics Analysis and Target Prioritization "
            f"for {disease}\n\n"
            f"**Generated by BioResearch-Agent**  \n"
            f"**Date:** {now}  \n"
            f"**Version:** 1.0  \n"
            f"**Workflow ID:** {results.get('traceability', {}).get('workflow_id', 'N/A')}\n\n"
            "---\n\n"
        )

    def _format_toc(self) -> str:
        return (
            "## Table of Contents\n\n"
            "1. [Background & Research Question](#1-background--research-question)\n"
            "2. [Methods Overview](#2-methods-overview)\n"
            "3. [Results](#3-results)\n"
            "4. [Candidate Targets](#4-candidate-targets)\n"
            "5. [Recommended Protocol](#5-recommended-protocol)\n"
            "6. [Traceability](#6-traceability)\n"
            "7. [Limitations](#7-limitations)\n"
            "8. [References](#8-references)\n\n"
            "<!--FIGURES-->\n\n"
        )

    def _format_background(self, question: dict) -> str:
        disease = question.get("disease", "the disease")
        desc = question.get("description", "")
        qtype = question.get("question_type", "mechanism")
        return (
            "## 1. Background & Research Question\n\n"
            f"### 1.1 Research Context\n\n"
            f"{disease} represents a significant challenge in precision medicine. "
            f"Despite advances in therapeutic strategies, there remains an urgent "
            f"need for the identification of novel molecular targets.\n\n"
            f"### 1.2 Research Question\n\n"
            f"- **Disease:** {disease}\n"
            f"- **Question Type:** {qtype}\n"
            f"- **Description:** {desc or 'Comprehensive multi-omics analysis to identify and prioritize therapeutic targets'}\n\n"
            f"### 1.3 Key Objectives\n\n"
            f"1. Identify differentially expressed genes associated with {disease}\n"
            f"2. Characterize functional pathways and biological processes\n"
            f"3. Prioritize drug targets using multi-dimensional scoring\n"
            f"4. Generate evidence-based experimental validation protocols\n\n"
        )

    def _format_methods(self, results: dict) -> str:
        pipelines = results.get("pipelines", results.get("traceability", {}).get("summary", {}))
        steps_desc = {
            "intent_classification": "Intent classification using LLM",
            "literature_search": "PubMed literature retrieval via NCBI E-utilities",
            "differential_expression": "Differential expression analysis (t-test/Wilcoxon)",
            "go_enrichment": "GO biological process enrichment (gseapy)",
            "kegg_enrichment": "KEGG pathway enrichment analysis",
            "target_scoring": "Multi-dimensional target scoring (6 dimensions)",
            "multi_agent_reasoning": "Multi-agent reasoning with LLM",
            "target_prioritization": "Weighted ranking and prioritization",
        }
        methods_used = []
        if isinstance(pipelines, dict):
            modules = pipelines.get("modules_used", [])
            for mod in modules:
                desc = steps_desc.get(mod.lower(), mod)
                methods_used.append(f"- **{mod}**: {desc}")

        return (
            "## 2. Methods Overview\n\n"
            "### 2.1 Analysis Pipeline\n\n"
            "The analysis was performed using BioResearch-Agent, an AI-driven "
            "biomedical research automation platform. The following steps were executed:\n\n"
            + ("\n".join(methods_used) if methods_used else "- Multi-step analysis pipeline\n") +
            "\n\n"
            "### 2.2 Statistical Methods\n\n"
            "- Differential expression: Independent t-test / Mann-Whitney U test\n"
            "- Multiple testing correction: Benjamini-Hochberg (FDR)\n"
            "- Survival analysis: Kaplan-Meier + Log-rank test / Cox regression\n"
            "- Target prioritization: Weighted multi-dimensional scoring\n\n"
        )

    def _format_results(self, results: dict) -> str:
        de = results.get("differential_expression", {})
        de_s = de.get("summary", {}) if isinstance(de, dict) else {}
        go = results.get("enrichment_go", {})
        go_s = go.get("summary", {}) if isinstance(go, dict) else {}
        kegg = results.get("enrichment_kegg", {})
        kegg_s = kegg.get("summary", {}) if isinstance(kegg, dict) else {}
        surv = results.get("survival", {})
        surv_s = surv.get("cox_regression", {}).get("summary", {}) if isinstance(surv, dict) else {}

        sections = ["## 3. Results\n\n### 3.1 Differential Expression Analysis\n\n"]

        de_genes = de_s.get("significant_genes", 0)
        up = de_s.get("upregulated", 0)
        down = de_s.get("downregulated", 0)
        sections.append(
            f"A total of **{de_genes}** significantly differentially expressed genes "
            f"were identified (**{up}** upregulated, **{down}** downregulated) "
            f"at |log2FC| > {de_s.get('log2fc_threshold', 1)} and "
            f"adjusted p-value < {de_s.get('pvalue_threshold', 0.05)}.\n\n"
        )

        # Top DEGs table
        sig_genes = de.get("significant", [])
        if sig_genes:
            sections.append("**Table 1: Top differentially expressed genes**\n\n")
            sections.append(
                "| Gene | log2FC | p-value | -log10(p) |\n"
                "|------|--------|---------|-----------|\n"
            )
            for g in sig_genes[:10]:
                sections.append(
                    f"| {g.get('gene', '')} | {g.get('log2FC', 0):.2f} | "
                    f"{g.get('pvalue_adjusted', 1):.2e} | "
                    f"{g.get('-log10_padj', 0):.2f} |\n"
                )
            sections.append("\n")

        # GO enrichment
        sections.append("### 3.2 Gene Ontology Enrichment\n\n")
        go_terms = go_s.get("total_significant_terms", 0)
        sections.append(
            f"GO enrichment analysis revealed **{go_terms}** significantly enriched "
            f"terms across Biological Process, Cellular Component, and "
            f"Molecular Function ontologies.\n\n"
        )
        top_terms = go_s.get("top_terms", [])
        if top_terms:
            sections.append("**Table 2: Top enriched GO terms**\n\n")
            sections.append(
                "| Term | p-value | Adjusted p-value | Ontology |\n"
                "|------|---------|-----------------|----------|\n"
            )
            for t in top_terms[:10]:
                sections.append(
                    f"| {t.get('term', '')[:50]} | {t.get('pvalue', '')} | "
                    f"{t.get('padj', '')} | {t.get('ontology', '')} |\n"
                )
            sections.append("\n")

        # KEGG
        sections.append("### 3.3 KEGG Pathway Enrichment\n\n")
        kegg_path = kegg_s.get("total_significant_pathways", 0)
        sections.append(
            f"KEGG pathway analysis identified **{kegg_path}** significantly "
            f"enriched pathways relevant to the disease mechanism.\n\n"
        )
        top_paths = kegg_s.get("top_pathways", [])
        if top_paths:
            sections.append("**Table 3: Top enriched KEGG pathways**\n\n")
            sections.append("| Pathway | p-value | Adjusted p-value |\n|--------|---------|-----------------|\n")
            for p in top_paths[:8]:
                sections.append(f"| {p.get('term', '')[:50]} | {p.get('pvalue', '')} | {p.get('padj', '')} |\n")
            sections.append("\n")

        # Survival
        sections.append("### 3.4 Survival Analysis\n\n")
        cs = surv_s.get("significant_genes", 0)
        ci = surv_s.get("concordance_index", "N/A")
        sections.append(
            f"Cox regression identified **{cs}** genes with significant prognostic "
            f"value (concordance index = {ci}). "
            f"Kaplan-Meier analysis confirmed survival stratification for key targets.\n\n"
        )

        # Figures
        sections.append("### 3.5 Visualization\n\n")
        vis = results.get("visualizations", {})
        if isinstance(vis, dict) and vis:
            sections.append("The following figures were generated:\n\n")
            for name, path in vis.items():
                sections.append(f"- **{name}**: `{path}`\n")
        sections.append("\n")
        return "".join(sections)

    def _format_targets(self, results: dict) -> str:
        targets = results.get("targets", results.get("target_ranking", []))
        if isinstance(targets, dict):
            targets = targets.get("results", targets.get("targets", []))

        sections = ["## 4. Candidate Targets\n\n"]
        if not targets:
            sections.append("No target candidates were generated.\n\n")
            return "".join(sections)

        sections.append("**Table 4: Prioritized target candidates**\n\n")
        sections.append(
            "| Rank | Gene | Total Score | Literature | Expression | Druggability | Safety |\n"
            "|------|------|-------------|------------|------------|--------------|--------|\n"
        )
        for t in targets[:15] if isinstance(targets, list) else []:
            dims = t.get("dimensions", {})
            if isinstance(dims, dict):
                lit = dims.get("literature_support", {}).get("score", "N/A")
                expr = dims.get("expression_foldchange", {}).get("score", "N/A")
                drug = dims.get("druggability", {}).get("score", "N/A")
                safe = dims.get("safety", {}).get("score", "N/A")
            else:
                lit = expr = drug = safe = "N/A"
            sections.append(
                f"| {t.get('ranking', '')} | {t.get('gene', '')} | "
                f"{t.get('total_score', 0):.3f} | {lit} | {expr} | "
                f"{drug} | {safe} |\n"
            )
        sections.append("\n")

        # 证据链
        sections.append("### 4.1 Evidence Chain for Top Candidate\n\n")
        if targets:
            top = targets[0] if isinstance(targets, list) else {}
            chain = top.get("evidence_chain", top.get("agent_assessments", {}))
            if chain:
                sections.append("```\n")
                if isinstance(chain, list):
                    for entry in chain[:8]:
                        sections.append(
                            f"  • {entry.get('dimension', entry.get('agent', '?'))}: "
                            f"score={entry.get('score', 'N/A')}, "
                            f"{entry.get('summary', entry.get('reasoning', ''))[:100]}\n"
                        )
                elif isinstance(chain, dict):
                    for agent, result in list(chain.items())[:4]:
                        sections.append(
                            f"  • {agent}: confidence={result.get('confidence', 'N/A')}\n"
                        )
                sections.append("```\n\n")
        return "".join(sections)

    def _format_protocol(self, results: dict) -> str:
        protocol = results.get("protocol", results.get("experimental_protocol", {}))
        sections = ["## 5. Recommended Experimental Protocol\n\n"]
        if not protocol:
            sections.append("No experimental protocol was generated.\n\n")
            return "".join(sections)

        sections.append(f"**Title:** {protocol.get('title', 'Experimental Validation Protocol')}\n\n")
        sections.append(f"**Objective:** {protocol.get('objective', 'Validate top targets')}\n\n")

        if protocol.get("steps"):
            sections.append("### 5.1 Experimental Steps\n\n")
            sections.append(
                "| Step | Method | Duration |\n|------|--------|----------|\n"
            )
            for s in protocol["steps"]:
                sections.append(
                    f"| {s.get('step', '')} | {s.get('name', '')} | "
                    f"{s.get('duration', '')} |\n"
                )
            sections.append("\n")

        if protocol.get("timeline"):
            sections.append("### 5.2 Timeline\n\n")
            for phase in protocol["timeline"]:
                sections.append(
                    f"- **{phase.get('phase', '')}**: "
                    f"{phase.get('start_date', '')} → {phase.get('end_date', '')}\n"
                )
            sections.append("\n")

        return "".join(sections)

    def _format_traceability(self, results: dict) -> str:
        trace = results.get("traceability", {})
        steps_list = trace.get("steps", []) if isinstance(trace, dict) else []
        summary = trace.get("summary", {}) if isinstance(trace, dict) else {}

        sections = ["## 6. Traceability\n\n"]
        sections.append(
            "This report was generated using BioResearch-Agent with full "
            "step-level traceability to ensure reproducibility.\n\n"
        )

        sections.append("**Table 5: Analysis step log**\n\n")
        sections.append(
            "| Step ID | Module | Duration (s) |\n"
            "|---------|--------|-------------|\n"
        )
        for step in steps_list:
            meta = step.get("metadata", {})
            sections.append(
                f"| {step.get('step_id', '')} | "
                f"{meta.get('module', step.get('step_name', ''))} | "
                f"{step.get('elapsed_from_start', 0)} |\n"
            )
        sections.append("\n")
        sections.append(
            f"**Workflow ID:** {trace.get('workflow_id', 'N/A')}  \n"
            f"**Total steps:** {summary.get('total_steps', len(steps_list))}  \n"
            f"**Total elapsed:** {summary.get('total_elapsed_seconds', 'N/A')} seconds\n\n"
        )

        sections.append("*Full traceability data available in JSON format.*\n\n")
        return "".join(sections)

    def _format_limitations(self) -> str:
        return (
            "## 7. Limitations\n\n"
            "1. **Data Source Bias**: The analysis is limited by the quality and "
            "completeness of available public databases.\n"
            "2. **Computational Predictions**: All findings are in silico predictions "
            "and require experimental validation.\n"
            "3. **Model Limitations**: The AI models may not capture all biological "
            "complexities and context-specific interactions.\n"
            "4. **Sample Size**: The statistical power depends on the input data "
            "quality and sample size.\n"
            "5. **Publication Bias**: Literature-based scores may be influenced by "
            "publication bias towards well-studied genes.\n\n"
            "### Recommendations\n\n"
            "- Validate top targets using independent cohorts\n"
            "- Perform experimental validation (in vitro / in vivo)\n"
            "- Consider tissue-specific and context-dependent effects\n"
            "- Review results in conjunction with domain expertise\n\n"
        )

    def _format_references(self, results: dict) -> str:
        refs = results.get("references", [])
        sections = ["## 8. References\n\n"]
        sections.append("1. BioResearch-Agent Platform (2024). AI-driven Biomedical Research Automation.\n")
        sections.append("2. NCBI Resource Coordinators. (2024). Database resources of the National Center for Biotechnology Information. *Nucleic Acids Res*.\n")
        sections.append("3. Subramanian, A., et al. (2005). Gene set enrichment analysis. *PNAS*.\n")
        sections.append("4. Szklarczyk, D., et al. (2023). STRING database: protein-protein networks. *Nucleic Acids Res*.\n")
        if refs and isinstance(refs, list):
            for i, ref in enumerate(refs, 5):
                if isinstance(ref, dict):
                    sections.append(
                        f"{i}. {ref.get('topic', '')} "
                        f"(PMID: {ref.get('pmid', 'N/A')}).\n"
                    )
        sections.append("\n")
        return "".join(sections)

    def _format_appendix(self, results: dict) -> str:
        return (
            "## Appendix: Configuration & Parameters\n\n"
            "```json\n"
            f"{{\n  \"app\": \"BioResearch-Agent\",\n  \"version\": \"1.0.0\",\n  "
            f"\"workflow_id\": \"{results.get('traceability', {}).get('workflow_id', 'N/A')}\"\n}}\n"
            "```\n\n---\n\n"
            "*Report generated by BioResearch-Agent. All analyses are computational "
            "predictions and require experimental validation.*\n"
        )

    # ── HTML 辅助 ──────────────────────────────

    def _md_to_html(self, md: str) -> str:
        """简单的 Markdown 到 HTML 转换（覆盖报告中的基本格式）。"""
        import re

        lines = md.split("\n")
        html_lines = []
        in_table = False
        in_code = False

        for line in lines:
            # Headings
            if line.startswith("##### "):
                line = f"<h5>{line[6:]}</h5>"
            elif line.startswith("#### "):
                line = f"<h4>{line[5:]}</h4>"
            elif line.startswith("### "):
                line = f"<h3>{line[4:]}</h3>"
            elif line.startswith("## "):
                line = f"<h2>{line[3:]}</h2>"
            elif line.startswith("# "):
                line = f"<h1>{line[2:]}</h1>"
            # Code block
            elif line.strip().startswith("```"):
                if in_code:
                    line = "</code></pre>"
                    in_code = False
                else:
                    line = "<pre><code>"
                    in_code = True
            # Table
            elif "|" in line and ("---" in line or "|" in line):
                if line.strip().startswith("|") and line.strip().endswith("|"):
                    if in_table:
                        cells = [c.strip() for c in line.split("|")[1:-1]]
                        line = "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
                    else:
                        # check if header row
                        if "---" not in line:
                            cells = [c.strip() for c in line.split("|")[1:-1]]
                            line = "<table><thead><tr>" + \
                                   "".join(f"<th>{c}</th>" for c in cells) + \
                                   "</tr></thead><tbody>"
                            in_table = True
                continue
            # Bold
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            # Italic
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            # Code inline
            line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)
            # Links
            line = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', line)

            if line.strip() == "---":
                html_lines.append("<hr>")
            elif line.strip() == "":
                if in_table:
                    html_lines.append("</tbody></table>")
                    in_table = False
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p>{line}</p>" if not line.startswith(("<", "http")) else line)

        return "\n".join(html_lines)

    def _embed_figures(self, results: dict) -> str:
        """将生成的图表嵌入为 base64 HTML。"""
        vis = results.get("visualizations", {})
        if not vis:
            return ""

        html = '<div class="page-break"></div>\n<h2>Figures</h2>\n'
        for name, rel_path in vis.items():
            # 尝试从 output 目录查找
            full_path = self._output_dir.parent / rel_path
            if isinstance(full_path, Path) and full_path.exists():
                try:
                    with open(full_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    html += (
                        f'<div class="figure">\n'
                        f'<img src="data:image/png;base64,{b64}" '
                        f'alt="{name}">\n'
                        f'<div class="figure-caption">Figure: {name}</div>\n'
                        f'</div>\n'
                    )
                except Exception as e:
                    logger.debug(f"图表嵌入失败 {name}: {e}")
            # 也尝试扫描子目录
            else:
                for subdir in ["figures", "analysis", "targets", "protocols"]:
                    p = self._output_dir.parent / subdir / f"{name}.png"
                    if p.exists():
                        try:
                            with open(p, "rb") as f:
                                b64 = base64.b64encode(f.read()).decode()
                            html += (
                                f'<div class="figure">\n'
                                f'<img src="data:image/png;base64,{b64}" '
                                f'alt="{name}">\n'
                                f'<div class="figure-caption">Figure: {name}</div>\n'
                                f'</div>\n'
                            )
                        except Exception:
                            pass
                        break
        return html
