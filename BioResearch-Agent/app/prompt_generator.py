"""
提示词生成器 (PromptGenerator)。

将用户在配置面板中设置的分析参数，自动拼接成标准化的自然语言提示词，
供 LLM 执行靶点发现分析。
"""

from __future__ import annotations

from typing import Any

# ── 字段映射表 ────────────────────────────────

SCREENING_MAP = {
    "strict": "严格筛选",
    "standard": "标准筛选",
    "relaxed": "宽松筛选",
    "custom": "自定义筛选",
}

FC_DESC = {
    "strict": "要求|log2FC| > 2 且 padj < 0.01",
    "standard": "要求|log2FC| > 1 且 padj < 0.05",
    "relaxed": "要求|log2FC| > 0.5 且 padj < 0.1",
}

ENRICH_DB_LABELS = {
    "GO_BP": "GO_BP (生物学过程)",
    "GO_CC": "GO_CC (细胞组分)",
    "GO_MF": "GO_MF (分子功能)",
    "KEGG": "KEGG (信号通路)",
    "Reactome": "Reactome (反应组)",
    "WikiPathways": "WikiPathways",
}

ENRICH_SIG_MAP = {
    "strict": "要求校正后p值小于0.01",
    "standard": "要求校正后p值小于0.05",
    "relaxed": "要求校正后p值小于0.1",
}

AREA_MAP = {
    "tumor_immunology": "肿瘤免疫",
    "metabolic_reprogramming": "代谢重编程",
    "apoptosis": "细胞凋亡",
    "autophagy": "自噬",
    "oxidative_stress": "氧化应激",
    "emt": "上皮间质转化",
    "drug_metabolism": "药物代谢",
    "dna_repair": "DNA损伤修复",
    "custom": "自定义",
}

EVIDENCE_LABELS = {
    "literature": "文献支持",
    "multi_omics": "多组学数据",
    "genetic": "遗传学证据",
    "drug_accessibility": "药物可及性",
    "clinical": "临床数据",
}

SORT_LABELS = {
    "comprehensive_score": "综合评分",
    "fold_change": "差异倍数",
    "literature_support": "文献支持度",
    "druggability": "可药性",
}


class PromptGenerator:
    """分析提示词生成器。

    将用户的配置选项拼接为结构化的自然语言提示词，
    可直接用于 LLM 分析或复制到其他 AI 对话中。
    """

    @staticmethod
    def generate_prompt(
        disease: str,
        config: dict[str, Any],
    ) -> str:
        """生成完整的分析提示词。

        Args:
            disease: 疾病名称或数据描述
            config: 配置字典（来自 config_panel）

        Returns:
            结构化的自然语言提示词文本
        """
        sections: list[str] = []
        sections.append(f"请帮我分析【{disease}】相关的生物医学数据，按照以下要求执行靶点发现分析：\n")

        # ── 1. 差异表达筛选 ──────────────────
        strictness = config.get("screening_strictness", "standard")
        log2fc = config.get("log2fc_threshold", 1.0)
        pval = config.get("pvalue_threshold", 0.05)

        if strictness == "custom":
            fc_desc = f"要求|log2FC| > {log2fc} 且 padj < {pval}"
        else:
            fc_desc = FC_DESC.get(strictness, FC_DESC["standard"])

        sections.append(
            f"【差异表达筛选】使用{SCREENING_MAP.get(strictness, '标准筛选')}"
            f"策略，{fc_desc}。"
        )

        # ── 2. 富集分析 ──────────────────────
        databases = config.get("enrichment_databases", ["GO_BP", "KEGG"])
        enrich_sig = config.get("enrichment_significance", "standard")
        min_genes = config.get("min_genes_per_pathway", 3)

        db_names = [ENRICH_DB_LABELS.get(d, d) for d in databases]
        sections.append(
            f"【富集分析】使用{'、'.join(db_names)}数据库进行富集分析，"
            f"{ENRICH_SIG_MAP.get(enrich_sig, ENRICH_SIG_MAP['standard'])}，"
            f"至少{min_genes}个基因富集到该通路。"
        )

        # ── 3. 通路/功能重点关注 ──────────────
        area = config.get("research_area", "")
        custom_pw = config.get("custom_pathways", "").strip()

        focus_items = []
        if area and area != "custom":
            focus_items.append(AREA_MAP.get(area, area))
        if custom_pw:
            focus_items.append(custom_pw)

        if focus_items:
            sections.append(
                f"【功能关注】重点关注{'、'.join(focus_items)}相关通路和功能。"
            )

        # ── 4. 基因列表筛选 ──────────────────
        focus_genes = config.get("focus_genes", "").strip()
        exclude_mito = config.get("exclude_mitochondrial", False)
        exclude_rbp = config.get("exclude_ribosomal", False)
        exclude_ig = config.get("exclude_immunoglobulin", False)

        gene_parts = []
        if focus_genes:
            gene_parts.append(f"重点关注以下基因：{focus_genes}")

        exclude_list = []
        if exclude_mito:
            exclude_list.append("线粒体基因")
        if exclude_rbp:
            exclude_list.append("核糖体蛋白")
        if exclude_ig:
            exclude_list.append("免疫球蛋白")
        if exclude_list:
            gene_parts.append(f"排除{'、'.join(exclude_list)}")

        if gene_parts:
            sections.append(f"【基因筛选】{'；'.join(gene_parts)}。")

        # ── 5. 证据整合 ──────────────────────
        evidence = config.get("evidence_sources", ["literature", "multi_omics"])
        confidence = config.get("evidence_confidence", 6)

        ev_names = [EVIDENCE_LABELS.get(e, e) for e in evidence]
        sections.append(
            f"【证据要求】需要{'、'.join(ev_names)}交叉验证，"
            f"综合可信度需达到{confidence}分以上。"
        )

        # ── 6. 靶点输出 ──────────────────────
        output_count = config.get("output_count", 5)
        sort_by = config.get("sort_by", "comprehensive_score")
        sort_label = SORT_LABELS.get(sort_by, "综合评分")

        sections.append(
            f"【输出要求】输出排名前{output_count}的候选靶点，"
            f"按{sort_label}排序，并附上关键证据支持。"
        )

        return "\n\n".join(sections)

    @staticmethod
    def summarize_config(config: dict[str, Any]) -> str:
        """生成配置摘要（用于界面显示）。"""
        parts = []
        strictness = config.get("screening_strictness", "standard")
        log2fc = config.get("log2fc_threshold", 1.0)
        pval = config.get("pvalue_threshold", 0.05)

        parts.append(
            f"差异表达: {'严格' if strictness == 'strict' else '标准' if strictness == 'standard' else '宽松'}"
            f" (|log2FC|>{log2fc}, padj<{pval})"
        )

        dbs = config.get("enrichment_databases", [])
        parts.append(f"富集: {len(dbs)}库")

        evidence = config.get("evidence_sources", [])
        parts.append(f"证据: {len(evidence)}源")

        count = config.get("output_count", 5)
        parts.append(f"输出: Top {count}")

        return " | ".join(parts)
