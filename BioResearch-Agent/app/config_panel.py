"""
配置面板模块 (ConfigPanel)。

提供 Streamlit 侧边栏中的靶点发现参数配置 UI，
包括预设方案加载、参数调整、配置历史管理和提示词导出。
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import streamlit as st

from app.prompt_generator import PromptGenerator

# ── 常量 ──────────────────────────────────────

PRESETS_PATH = Path(__file__).resolve().parent / "presets.json"

HISTORY_KEY = "config_history"
MAX_HISTORY = 5

# ── 默认配置 ──────────────────────────────────

DEFAULT_CONFIG: dict[str, Any] = {
    "screening_strictness": "standard",
    "log2fc_threshold": 1.0,
    "pvalue_threshold": 0.05,
    "enrichment_databases": ["GO_BP", "KEGG"],
    "enrichment_significance": "standard",
    "min_genes_per_pathway": 3,
    "research_area": "tumor_immunology",
    "custom_pathways": "",
    "focus_genes": "",
    "exclude_mitochondrial": False,
    "exclude_ribosomal": False,
    "exclude_immunoglobulin": False,
    "evidence_sources": ["literature", "multi_omics"],
    "evidence_confidence": 6,
    "output_count": 5,
    "sort_by": "comprehensive_score",
}

# ── 预设加载 ──────────────────────────────────

@st.cache_data
def load_presets() -> dict[str, Any]:
    """加载预设方案。"""
    if PRESETS_PATH.exists():
        with open(PRESETS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ── 配置历史管理 ──────────────────────────────

def init_history() -> None:
    """初始化配置历史。"""
    if HISTORY_KEY not in st.session_state:
        st.session_state[HISTORY_KEY] = []


def save_to_history(config: dict[str, Any], label: str) -> None:
    """保存配置到历史记录。"""
    entry = {
        "label": label,
        "config": deepcopy(config),
    }
    history = st.session_state.get(HISTORY_KEY, [])
    # 去重：相同配置不重复保存
    for h in history:
        if h["config"] == config:
            return
    history.insert(0, entry)
    st.session_state[HISTORY_KEY] = history[:MAX_HISTORY]


# ── 配置面板 UI ──────────────────────────────

def render_config_panel() -> dict[str, Any]:
    """在侧边栏渲染配置面板，返回当前配置。

    Returns:
        当前有效的配置字典
    """
    init_history()
    presets = load_presets()

    # 初始化 session state 中的配置
    if "analysis_config" not in st.session_state:
        st.session_state.analysis_config = deepcopy(DEFAULT_CONFIG)

    config = st.session_state.analysis_config

    # ── 预设方案选择 ──────────────────────────
    with st.expander("⚙️ 分析参数设置", expanded=True):
        preset_options = {
            "": "— 手动配置 —",
        }
        for key, preset in presets.items():
            preset_options[key] = f"{preset['name']}"

        selected_preset = st.selectbox(
            "预设方案",
            options=list(preset_options.keys()),
            format_func=lambda x: preset_options.get(x, x),
            key="preset_selector",
            help="选择预设方案自动填充所有参数",
        )

        if selected_preset and selected_preset in presets:
            preset_config = presets[selected_preset]["config"]
            if st.session_state.get("_last_preset") != selected_preset:
                st.session_state.analysis_config = deepcopy(preset_config)
                st.session_state["_last_preset"] = selected_preset
                config = st.session_state.analysis_config
                save_to_history(config, presets[selected_preset]["name"])

        st.divider()

        # ── 1. 差异表达筛选 ──────────────────
        st.markdown("**📊 差异表达筛选**")
        screening_labels = {
            "strict": "① 严格筛选 (高置信度)",
            "standard": "② 标准筛选 (推荐)",
            "relaxed": "③ 宽松筛选 (广覆盖)",
            "custom": "④ 自定义",
        }
        config["screening_strictness"] = st.selectbox(
            "筛选严格程度",
            options=list(screening_labels.keys()),
            format_func=lambda x: screening_labels.get(x, x),
            index=["strict", "standard", "relaxed", "custom"].index(
                config.get("screening_strictness", "standard")
            ),
            key="strictness",
        )
        config["log2fc_threshold"] = st.slider(
            "log2FC 阈值", 0.5, 3.0, config.get("log2fc_threshold", 1.0), 0.1,
            key="log2fc",
        )
        config["pvalue_threshold"] = st.slider(
            "padj 阈值", 0.001, 0.1, config.get("pvalue_threshold", 0.05), 0.001,
            format="%.3f", key="pval",
        )

        st.divider()

        # ── 2. 富集分析配置 ──────────────────
        st.markdown("**🔬 富集分析配置**")
        all_dbs = ["GO_BP", "GO_CC", "GO_MF", "KEGG", "Reactome", "WikiPathways"]
        db_labels = {
            "GO_BP": "GO_BP (生物学过程)",
            "GO_CC": "GO_CC (细胞组分)",
            "GO_MF": "GO_MF (分子功能)",
            "KEGG": "KEGG (信号通路)",
            "Reactome": "Reactome (反应组)",
            "WikiPathways": "WikiPathways",
        }
        config["enrichment_databases"] = st.multiselect(
            "富集数据库",
            options=all_dbs,
            default=config.get("enrichment_databases", ["GO_BP", "KEGG"]),
            format_func=lambda x: db_labels.get(x, x),
            key="enrich_db",
        )
        sig_labels = {"strict": "严格 (p<0.01)", "standard": "标准 (p<0.05)", "relaxed": "宽松 (p<0.1)"}
        config["enrichment_significance"] = st.selectbox(
            "富集显著性",
            options=list(sig_labels.keys()),
            format_func=lambda x: sig_labels.get(x, x),
            index=["strict", "standard", "relaxed"].index(
                config.get("enrichment_significance", "standard")
            ),
            key="enrich_sig",
        )
        config["min_genes_per_pathway"] = st.number_input(
            "最小基因数", 1, 10, config.get("min_genes_per_pathway", 3), 1,
            key="min_genes",
        )

        st.divider()

        # ── 3. 通路关注 ──────────────────────
        st.markdown("**🎯 通路/功能重点关注**")
        area_options = {
            "": "— 不限 —",
            "tumor_immunology": "肿瘤免疫",
            "metabolic_reprogramming": "代谢重编程",
            "apoptosis": "细胞凋亡",
            "autophagy": "自噬",
            "oxidative_stress": "氧化应激",
            "emt": "上皮间质转化",
            "drug_metabolism": "药物代谢",
            "dna_repair": "DNA损伤修复",
            "custom": "自定义输入",
        }
        area_keys = list(area_options.keys())
        current_area = config.get("research_area", "")
        area_index = area_keys.index(current_area) if current_area in area_keys else 0
        config["research_area"] = st.selectbox(
            "研究领域",
            options=area_keys,
            format_func=lambda x: area_options.get(x, x),
            index=area_index,
            key="research_area",
        )
        config["custom_pathways"] = st.text_input(
            "自定义通路/关键词",
            value=config.get("custom_pathways", ""),
            placeholder="例: PI3K-AKT, MAPK, Wnt/β-catenin",
            key="custom_pw",
        )

        st.divider()

        # ── 4. 基因列表筛选 ──────────────────
        st.markdown("**🧬 基因列表筛选**")
        config["focus_genes"] = st.text_area(
            "重点关注基因 (逗号分隔)",
            value=config.get("focus_genes", ""),
            placeholder="例: TP53, MYC, EGFR, KRAS",
            height=60,
            key="focus_genes",
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            config["exclude_mitochondrial"] = st.checkbox(
                "排除线粒体基因", config.get("exclude_mitochondrial", False),
                key="ex_mito",
            )
        with col2:
            config["exclude_ribosomal"] = st.checkbox(
                "排除核糖体蛋白", config.get("exclude_ribosomal", False),
                key="ex_rbp",
            )
        with col3:
            config["exclude_immunoglobulin"] = st.checkbox(
                "排除免疫球蛋白", config.get("exclude_immunoglobulin", False),
                key="ex_ig",
            )

        st.divider()

        # ── 5. 证据整合 ──────────────────────
        st.markdown("**🔗 证据整合配置**")
        evidence_opts = ["literature", "multi_omics", "genetic", "drug_accessibility", "clinical"]
        ev_labels = {
            "literature": "文献支持",
            "multi_omics": "多组学数据",
            "genetic": "遗传学证据",
            "drug_accessibility": "药物可及性",
            "clinical": "临床数据",
        }
        config["evidence_sources"] = st.multiselect(
            "证据来源",
            options=evidence_opts,
            default=config.get("evidence_sources", ["literature", "multi_omics"]),
            format_func=lambda x: ev_labels.get(x, x),
            key="evidence",
        )
        config["evidence_confidence"] = st.slider(
            "证据综合可信度", 0, 10, config.get("evidence_confidence", 6), 1,
            key="confidence",
        )

        st.divider()

        # ── 6. 靶点输出 ──────────────────────
        st.markdown("**📋 靶点输出配置**")
        config["output_count"] = st.number_input(
            "输出数量", 1, 20, config.get("output_count", 5), 1,
            key="output_count",
        )
        sort_opts = ["comprehensive_score", "fold_change", "literature_support", "druggability"]
        sort_labels = {
            "comprehensive_score": "综合评分",
            "fold_change": "差异倍数",
            "literature_support": "文献支持度",
            "druggability": "可药性",
        }
        config["sort_by"] = st.selectbox(
            "排序依据",
            options=sort_opts,
            format_func=lambda x: sort_labels.get(x, x),
            index=sort_opts.index(config.get("sort_by", "comprehensive_score")),
            key="sort_by",
        )

    # ── 配置历史 ──────────────────────────────
    history = st.session_state.get(HISTORY_KEY, [])
    if history:
        with st.expander("📚 配置历史", expanded=False):
            for i, entry in enumerate(history):
                label = entry["label"]
                summary = PromptGenerator.summarize_config(entry["config"])
                if st.button(
                    f"{i+1}. {label}",
                    help=summary,
                    use_container_width=True,
                    key=f"hist_{i}",
                ):
                    st.session_state.analysis_config = deepcopy(entry["config"])
                    st.rerun()

    # ── 提示词预览与导出 ──────────────────────
    with st.expander("📋 提示词预览", expanded=False):
        disease = st.session_state.get("research_question", "目标疾病")
        prompt = PromptGenerator.generate_prompt(disease, config)
        st.text_area("生成的提示词", prompt, height=200, key="prompt_preview")

        st.download_button(
            "📋 复制提示词",
            data=prompt,
            file_name="analysis_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.caption("提示词可直接用于 AI 对话或复制到其他 LLM 平台。")

    return config
