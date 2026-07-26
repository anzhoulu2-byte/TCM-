"""
BioResearch-Agent Streamlit Web 界面。

在网页上完成整个生物医学研究分析流程：
配置 API Key → 上传表达数据 → 输入研究问题 → 一键分析 → 查看结果。
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import get_config
from app.prompt_generator import PromptGenerator
from app.config_panel import render_config_panel, load_presets
from src.modules.module_01_understanding import IntentClassifier, TaskPlanner
from src.modules.module_02_retrieval import LiteratureRetriever, LiteratureAnalyzer
from src.modules.module_03_analysis import AnalysisOrchestrator
from src.modules.module_04_target import TargetScorer, MultiAgentReasoner, TargetPrioritizer
from src.modules.module_05_protocol import (
    ProtocolGenerator, ResourceRecommender, FeasibilityAnalyzer,
)
from src.modules.module_06_report import TraceabilityTracker, ReportGenerator, ReportExporter


# ═══════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════

st.set_page_config(
    page_title="自动化生物医学研究平台",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自定义 CSS（蓝白现代风格） ────────────────

st.markdown("""
<style>
    /* 全局 */
    .main > div { padding: 0 1rem 1rem 1rem; }
    .stApp { background: #f4f7fc; }
    h1, h2, h3 { color: #1a3a5c; font-family: 'Segoe UI', sans-serif; }
    h1 { border-bottom: 2px solid #2b6cb0; padding-bottom: 8px; }

    /* 欢迎卡片 */
    .welcome-card {
        background: white; border-radius: 16px; padding: 40px;
        box-shadow: 0 8px 30px rgba(43,108,176,0.10);
        text-align: center; max-width: 650px; margin: 60px auto;
    }
    .welcome-card h2 { color: #2b6cb0; margin-bottom: 12px; }
    .welcome-card p { color: #4a5568; font-size: 1.05em; line-height: 1.6; }
    .welcome-card .hint {
        background: #ebf4ff; border-radius: 10px; padding: 16px;
        margin-top: 20px; text-align: left; font-size: 0.9em;
    }
    .welcome-card .hint code {
        background: #c3d9f0; padding: 2px 8px; border-radius: 4px;
        font-size: 0.85em;
    }

    /* 结果卡片 */
    .result-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05); margin-bottom: 16px;
        border: 1px solid #e8edf4;
    }
    .result-card h4 { color: #2b6cb0; margin-bottom: 8px; }

    /* 指标 */
    .metric-box {
        background: white; border-radius: 10px; padding: 16px;
        text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border-top: 3px solid #2b6cb0;
    }
    .metric-box .value { font-size: 1.8em; font-weight: 700; color: #1a3a5c; }
    .metric-box .label { font-size: 0.85em; color: #718096; margin-top: 4px; }

    /* 溯源条目 */
    .trace-step {
        background: white; border-left: 3px solid #2b6cb0;
        border-radius: 0 8px 8px 0; padding: 10px 16px; margin: 6px 0;
        font-size: 0.9em;
    }
    .trace-step .step-id { color: #2b6cb0; font-weight: 600; }

    /* 进度 */
    .stProgress > div > div { background-color: #2b6cb0; }

    /* 按钮 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2b6cb0, #2c5282);
        border: none; font-weight: 600;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2c5282, #1a365d);
    }

    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background: #ffffff; border-right: 1px solid #e8edf4;
    }
    section[data-testid="stSidebar"] .stTextInput label {
        font-weight: 600; color: #1a3a5c;
    }

    /* 标签页 */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0; padding: 8px 18px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #2b6cb0 !important; color: white !important;
    }

    /* 数据框 */
    .stDataFrame { border: 1px solid #e8edf4; border-radius: 8px; }

    /* 展开器 */
    .streamlit-expanderHeader {
        background: #f7faff; border-radius: 8px; font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 会话状态
# ═══════════════════════════════════════════════

def init_state() -> None:
    keys = {
        "results": None,
        "running": False,
        "progress": 0,
        "status_text": "",
        "expression_df": None,
        "metadata_df": None,
        "analyzer": None,
        "chat_messages": [],
        "chat_analyzing": False,
    }
    for k, v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ═══════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧬 自动化生物医学研究平台")
    st.caption("AI 驱动的科研全流程自动化")

    st.divider()

    # ── API 密钥配置 ──────────────────────────
    with st.expander("🔑 API 密钥配置", expanded=False):
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            placeholder="sk-...",
            help="必填，用于 LLM 推理",
        )
        openai_key = st.text_input(
            "OpenAI API Key（可选）",
            type="password",
            placeholder="sk-...",
        )
        pubmed_email = st.text_input(
            "PubMed 邮箱",
            placeholder="your@email.com",
            help="NCBI E-utilities 要求提供",
        )

    st.divider()

    # ── 研究问题输入 ──────────────────────────
    st.markdown("### 📝 研究问题")
    question = st.text_area(
        label="输入研究问题",
        label_visibility="collapsed",
        placeholder="例如：寻找肝癌耐药性的新靶点",
        height=90,
    )

    # ── 数据上传 ──────────────────────────────
    with st.expander("📂 上传表达数据（可选）", expanded=False):
        st.caption("上传后可进行差异表达和生存分析")
        expr_file = st.file_uploader(
            "表达矩阵 (CSV, 行=基因, 列=样本)",
            type="csv",
            key="expr_upload",
        )
        meta_file = st.file_uploader(
            "样本元数据 (CSV, 列: group 等)",
            type="csv",
            key="meta_upload",
        )

    # ── 分析参数配置面板 ────────────────────────
    analysis_config = render_config_panel()

    # ── 开始按钮 ──────────────────────────────
    btn_disabled = st.session_state.running or not question.strip()
    start_btn = st.button(
        "🚀 开始分析",
        type="primary",
        use_container_width=True,
        disabled=btn_disabled,
    )

    st.divider()

    # ── 导出 / 溯源按钮 ───────────────────────
    export_disabled = st.session_state.results is None
    st.download_button(
        "📥 导出结果 (JSON)",
        data=json.dumps(st.session_state.results or {}, indent=2, default=str),
        file_name=f"results_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
        disabled=export_disabled,
    )
    if st.button("📜 查看溯源", use_container_width=True, disabled=export_disabled):
        st.session_state.show_trace = True

    st.divider()
    st.caption("v1.0.0 · BioResearch-Agent")


# ═══════════════════════════════════════════════
# 进度展示区域
# ═══════════════════════════════════════════════

progress_bar = st.empty()
status_text = st.empty()


def update_progress(pct: int, msg: str) -> None:
    st.session_state.progress = pct
    st.session_state.status_text = msg
    with progress_bar.container():
        st.progress(pct / 100, text=msg)


# ═══════════════════════════════════════════════
# 核心分析函数
# ═══════════════════════════════════════════════

async def run_research(
    question_text: str,
    api_keys: dict[str, str],
    expression_df: pd.DataFrame | None,
    metadata_df: pd.DataFrame | None,
    enhanced_prompt: str = "",
) -> dict[str, Any]:
    """完整的分析流水线，供 Streamlit 调用。

    Args:
        question_text: 研究问题
        api_keys: API 密钥字典
        expression_df: 表达数据
        metadata_df: 样本元数据
        enhanced_prompt: 配置面板生成的增强提示词（可选）
    """

    # 临时写入 .env 使配置生效
    if api_keys.get("deepseek"):
        os.environ["DEEPSEEK_API_KEY"] = api_keys["deepseek"]
    if api_keys.get("openai"):
        os.environ["OPENAI_API_KEY"] = api_keys["openai"]
    if api_keys.get("email"):
        os.environ["PUBMED_EMAIL"] = api_keys["email"]

    tracker = TraceabilityTracker()

    # ── 模块 1: 问题理解 ──────────────────────
    update_progress(5, "🧠 正在理解研究问题...")
    classifier = IntentClassifier()
    intent = await classifier.classify(question_text)
    tracker.log_step("intent_classification", {"question": question_text}, intent,
                     {"module": "IntentClassifier"})

    await asyncio.sleep(0.2)

    update_progress(12, "📋 正在规划分析任务...")
    planner = TaskPlanner()
    tasks = await planner.plan(question_text, intent)
    tracker.log_step("task_planning", {"intent": intent}, {"tasks": tasks},
                     {"module": "TaskPlanner"})

    # ── 模块 2: 文献检索 ──────────────────────
    update_progress(20, "📚 正在检索 PubMed 文献...")
    qdata = {
        "disease": question_text,
        "keywords": intent.get("keywords", []),
        "question_type": intent.get("research_purpose", "mechanism"),
        "description": question_text,
        "enhanced_prompt": enhanced_prompt,
    }
    retriever = LiteratureRetriever()
    retrieval = await retriever.retrieve(qdata)
    tracker.log_step("literature_search",
                     {"query": question_text},
                     {"lit": len(retrieval.get("literature", [])),
                      "genes": len(retrieval.get("associated_genes", []))},
                     {"module": "LiteratureRetriever"})

    # ── 模块 3: 生信分析 ──────────────────────
    update_progress(40, "🔬 正在进行生物信息学分析...")
    orchestrator = AnalysisOrchestrator(
        run_go=True, run_kegg=False, run_survival=False,
    )
    analysis_result = orchestrator.run_full_analysis(
        expression_data=expression_df or pd.DataFrame(),
        metadata=metadata_df,
        question=qdata,
    )
    tracker.log_step("bioinformatics_analysis", {}, {"status": analysis_result.get("status")},
                     {"module": "AnalysisOrchestrator"})

    # ── 模块 4: 靶点发现 ──────────────────────
    update_progress(60, "🎯 正在发现候选靶点...")
    candidates = []
    for gd in retrieval.get("associated_genes", [])[:30]:
        gene = gd.get("gene_symbol", "")
        if gene:
            evidence = {
                "literature": {"pmid_count": int(gd.get("score", 0.5) * 200), "co_occurrence": []},
                "expression": {"log2fc": gd.get("score", 1.0) * 2, "pvalue": 0.001, "padj": 0.005},
                "functional": {"go_terms": [], "pathways": [], "domains": []},
                "druggability": {"family": "enzyme", "known_drugs": [], "pocket": ""},
                "novelty": {"total_publications": int(gd.get("score", 0.5) * 300),
                            "clinical_trials": 0, "patents": 0},
                "safety": {"side_effects": [], "tissue_specificity": 0.7, "off_targets": []},
            }
            candidates.append({"gene": gene, "evidence_data": evidence})

    ranked_targets = []
    if candidates:
        reasoner = MultiAgentReasoner()
        enriched = await reasoner.reason(candidates)
        tracker.log_step("multi_agent_reasoning",
                         {"count": len(candidates)}, {"count": len(enriched)},
                         {"module": "MultiAgentReasoner"})

        prioritizer = TargetPrioritizer()
        ranked_targets = prioritizer.prioritize(enriched, top_k=10)
        tracker.log_step("target_prioritization",
                         {"count": len(candidates)},
                         {"top": [t.get("gene") for t in ranked_targets[:5]]},
                         {"module": "TargetPrioritizer"})

    # ── 模块 5: 实验方案 ──────────────────────
    update_progress(80, "🧪 正在生成实验方案...")
    protocol = {}
    if ranked_targets:
        gen = ProtocolGenerator()
        protocol = gen.generate(
            ranked_targets[0],
            {"experiment_type": "in_vitro", "budget": "medium", "disease": question_text},
        )
        tracker.log_step("protocol_generation",
                         {"target": ranked_targets[0].get("gene")},
                         {"id": protocol.get("protocol_id")},
                         {"module": "ProtocolGenerator"})

    # ── 模块 6: 报告生成 ──────────────────────
    update_progress(92, "📝 正在生成综合报告...")
    all_data = {
        "question": qdata,
        "intent": intent,
        "tasks": tasks,
        "literature": retrieval.get("literature", []),
        "associated_genes": retrieval.get("associated_genes", []),
        "differential_expression": analysis_result,
        "targets": ranked_targets,
        "protocol": protocol,
        "traceability": tracker.export_traceability(),
    }

    report_gen = ReportGenerator()
    html_report = report_gen.generate_html_report(all_data)

    exporter = ReportExporter()
    export_files = exporter.export_all(html_report, all_data, tracker.generate_workflow_json())

    update_progress(100, "✅ 分析完成！")
    return {
        **all_data,
        "html_report": html_report,
        "export_files": export_files,
        "tracker": tracker,
        "protocol": protocol,
    }


# ═══════════════════════════════════════════════
# 点击事件处理
# ═══════════════════════════════════════════════

if start_btn:
    if not question.strip():
        st.error("请输入研究问题")
        st.stop()

    st.session_state.running = True
    st.session_state.results = None
    st.session_state.show_trace = False

    # 读取上传文件
    expr_df = None
    meta_df = None
    if expr_file is not None:
        expr_df = pd.read_csv(expr_file, index_col=0)
    if meta_file is not None:
        meta_df = pd.read_csv(meta_file, index_col=0)

    api_keys = {
        "deepseek": deepseek_key,
        "openai": openai_key,
        "email": pubmed_email,
    }

    # 使用配置面板生成增强提示词
    enhanced_prompt = PromptGenerator.generate_prompt(question, analysis_config)
    st.session_state.enhanced_prompt = enhanced_prompt

    try:
        results = asyncio.run(
            run_research(question, api_keys, expr_df, meta_df, enhanced_prompt)
        )
        st.session_state.results = results
        st.rerun()
    except Exception as e:
        st.error(f"分析失败: {e}")
        import traceback
        st.exception(e)
    finally:
        st.session_state.running = False


# ═══════════════════════════════════════════════
# 主界面展示
# ═══════════════════════════════════════════════

results = st.session_state.results

# ── 未开始：欢迎界面 ──────────────────────────

if results is None and not st.session_state.running:
    st.markdown("""
    <div class="welcome-card">
        <h2>🧬 欢迎使用自动化生物医学研究平台</h2>
        <p>
            输入研究问题，AI 将自动完成从文献检索、生信分析、
            靶点发现到实验方案生成的全流程分析。
        </p>
        <div class="hint">
            <strong>💡 快速开始</strong><br>
            ① 在左侧栏配置 API 密钥（可选）<br>
            ② 输入研究问题，例如：<code>寻找肝癌耐药性的新靶点</code><br>
            ③ 可选上传表达数据 CSV，获得差异表达分析<br>
            ④ 点击「开始分析」按钮
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── 进行中：进度条 ──────────────────────────

if st.session_state.running:
    p = st.session_state.progress
    msg = st.session_state.status_text
    if p > 0:
        st.progress(p / 100, text=msg)
    else:
        st.info("⏳ 正在初始化...")

# ── 完成：结果展示 ──────────────────────────

if results is not None:
    st.markdown("## 📊 分析结果")

    # 顶部指标卡
    intent = results.get("intent", {})
    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            f'<div class="metric-box"><div class="value">{intent.get("disease_type","N/A").title()}</div>'
            f'<div class="label">目标疾病</div></div>', unsafe_allow_html=True)
    with cols[1]:
        lit_count = len(results.get("literature", []))
        st.markdown(
            f'<div class="metric-box"><div class="value">{lit_count}</div>'
            f'<div class="label">检索文献</div></div>', unsafe_allow_html=True)
    with cols[2]:
        gene_count = len(results.get("associated_genes", []))
        st.markdown(
            f'<div class="metric-box"><div class="value">{gene_count}</div>'
            f'<div class="label">关联基因</div></div>', unsafe_allow_html=True)
    with cols[3]:
        tgt_count = len(results.get("targets", []))
        st.markdown(
            f'<div class="metric-box"><div class="value">{tgt_count}</div>'
            f'<div class="label">候选靶点</div></div>', unsafe_allow_html=True)

    st.divider()

    # ── 标签页 ──────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 生信分析结果", "🎯 候选靶点", "🧪 实验方案", "📜 溯源与报告", "💬 学术对话",
    ])

    # ── Tab 1: 生信分析结果 ────────────────────
    with tab1:
        de = results.get("differential_expression", {})
        de_s = de.get("summary", {}) if isinstance(de, dict) else {}

        if de_s.get("total_genes_tested", 0) > 0:
            sig = de_s.get("significant_genes", 0)
            up = de_s.get("upregulated", 0)
            down = de_s.get("downregulated", 0)
            st.markdown(
                f'<div class="result-card">'
                f'<h4>差异表达分析</h4>'
                f'<p>检测 <strong>{de_s["total_genes_tested"]}</strong> 个基因，'
                f'其中 <strong>{sig}</strong> 个显著差异表达 '
                f'（上调 {up}，下调 {down}）</p></div>',
                unsafe_allow_html=True,
            )

            # 火山图
            df = de.get("results")
            if isinstance(df, pd.DataFrame) and not df.empty:
                fig = px.scatter(
                    df, x="log2FC", y="-log10_pvalue",
                    color="significant", color_discrete_map={True: "#E53E3E", False: "#A0AEC0"},
                    hover_data=["gene"], title="差异表达火山图",
                    labels={"log2FC": "log2(Fold Change)", "-log10_pvalue": "-log10(p-value)"},
                )
                fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="blue", opacity=0.4)
                fig.add_vline(x=-1, line_dash="dash", line_color="blue", opacity=0.4)
                fig.add_vline(x=1, line_dash="dash", line_color="blue", opacity=0.4)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("未传入表达数据或无差异分析结果。上传表达矩阵后可在此查看火山图和热图。")

        # 关联基因
        genes = results.get("associated_genes", [])
        if genes:
            st.markdown("### 关联基因")
            gdf = pd.DataFrame([
                {"基因": g.get("gene_symbol", ""), "评分": f"{g.get('score',0):.3f}",
                 "证据": "; ".join(g.get("evidence", [])[:2])}
                for g in genes
            ])
            st.dataframe(gdf, use_container_width=True, hide_index=True)

            fig = px.bar(
                gdf.head(15), x="基因", y="评分", title="Top 关联基因",
                color="评分", color_continuous_scale="Blues",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: 候选靶点 ────────────────────────
    with tab2:
        targets = results.get("targets", [])
        if targets:
            rows = []
            for t in targets:
                d = t.get("dimensions", {})
                row = {"排名": t.get("ranking", ""), "基因": t.get("gene", ""),
                       "总分": f"{t.get('total_score',0):.4f}"}
                if isinstance(d, dict):
                    for k in ["literature_support", "expression_foldchange",
                              "druggability", "safety"]:
                        row[k] = f"{d.get(k, {}).get('score', 0):.2f}"
                rows.append(row)

            df = pd.DataFrame(rows)
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_order=["排名", "基因", "总分", "literature_support",
                              "expression_foldchange", "druggability", "safety"],
            )

            # 排序图
            fig = px.bar(
                df.head(10), x="基因", y="总分", title="Top 候选靶点排序",
                color="总分", color_continuous_scale="RdYlGn", text="总分",
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            # 证据链
            with st.expander("🔍 查看 Top 候选证据链", expanded=False):
                top = targets[0]
                chain = top.get("evidence_chain", [])
                if chain:
                    for entry in chain[:6]:
                        st.markdown(
                            f'<div style="background:#f7faff;padding:8px 12px;'
                            f'border-left:3px solid #2b6cb0;border-radius:4px;'
                            f'margin:4px 0;font-size:0.9em">'
                            f'<strong>{entry.get("dimension","")}</strong>: '
                            f'score={entry.get("score","")} — '
                            f'{entry.get("summary","")}</div>',
                            unsafe_allow_html=True,
                        )
        else:
            st.info("未检索到关联基因，无候选靶点。配置 API Key 后可获得完整结果。")

    # ── Tab 3: 实验方案 ────────────────────────
    with tab3:
        protocol = results.get("protocol", {})
        if protocol:
            st.markdown(
                f'<div class="result-card">'
                f'<h4>{protocol.get("title","实验方案")}</h4>'
                f'<p><strong>方案 ID:</strong> {protocol.get("protocol_id","")}</p>'
                f'</div>', unsafe_allow_html=True,
            )

            st.markdown("#### 研究目标")
            for obj in protocol.get("research_objectives", []):
                st.markdown(
                    f'- **[{obj.get("priority","").upper()}]** {obj.get("objective","")}')

            st.markdown("#### 实验步骤")
            for step in protocol.get("steps", []):
                with st.expander(f"Step {step.get('step','')}: {step.get('name','')}"):
                    st.markdown(
                        f"**时长:** {step.get('duration','N/A')}  \n"
                        f"**描述:** {step.get('description','N/A')}")
                    if step.get("critical_notes"):
                        st.warning(step["critical_notes"])

            st.markdown("#### 时间线")
            for phase in protocol.get("timeline", []):
                st.markdown(
                    f'- **{phase.get("phase","")}**: {phase.get("start_date","")} → '
                    f'{phase.get("end_date","")}')
        else:
            st.info("无靶点候选，未生成实验方案。")

    # ── Tab 4: 溯源与报告 ─────────────────────
    with tab4:
        # 报告下载
        html_report = results.get("html_report", "")
        if html_report:
            st.download_button(
                "📥 下载完整报告 (HTML)",
                data=html_report,
                file_name=f"report_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=False,
            )

        st.divider()

        # 溯源展示
        tracker = results.get("tracker")
        if tracker:
            trace = tracker.export_traceability()
            steps = trace.get("steps", [])
            summary = trace.get("summary", {})

            st.markdown("### 执行日志")
            st.markdown(
                f'工作流 ID: `{trace.get("workflow_id","")}` — '
                f'总 {summary.get("total_steps",0)} 步, '
                f'耗时 {summary.get("total_elapsed_seconds",0):.1f}s'
            )

            for step in steps:
                meta = step.get("metadata", {})
                module = meta.get("module", step.get("step_name", ""))
                ts = step.get("timestamp", "")[11:19] if step.get("timestamp") else ""
                st.markdown(
                    f'<div class="trace-step">'
                    f'<span class="step-id">{step.get("step_id","")}</span> '
                    f'<strong>{module}</strong> '
                    f'<span style="color:#718096;float:right">{ts}</span><br>'
                    f'<span style="color:#4a5568;font-size:0.85em">'
                    f'输入: {json.dumps(step.get("inputs",{}),ensure_ascii=False)[:80]}...</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # 工作流下载
            wf = tracker.generate_workflow_json()
            st.download_button(
                "📦 下载可迁移工作流 (JSON)",
                data=json.dumps(wf, indent=2, default=str),
                file_name=f"workflow_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )
        else:
            st.info("无溯源记录。")

    # ── Tab 5: 学术对话 ─────────────────────────
    with tab5:
        st.markdown("### 💬 学术文献对话助手")
        st.caption(
            "输入研究问题，AI 自动搜索 PubMed、阅读文献摘要、"
            "综合分析观点，并与你互动讨论。你可以追问、质疑、"
            "调整方向，Agent 会根据对话上下文持续深入。"
        )

        # 初始化分析器
        if st.session_state.analyzer is None:
            st.session_state.analyzer = LiteratureAnalyzer()

        analyzer: LiteratureAnalyzer = st.session_state.analyzer

        # 重置按钮
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🔄 重置对话", use_container_width=True):
                analyzer.reset_conversation()
                st.session_state.chat_messages = []
                st.rerun()

        # 聊天记录展示
        chat_container = st.container()
        with chat_container:
            messages = st.session_state.chat_messages
            if not messages:
                st.info(
                    "💡 **开始探索吧！**\n\n"
                    "例如:\n"
                    "- *肝癌耐药性的分子机制是什么?*\n"
                    "- *PD-1 抑制剂在三阴性乳腺癌的最新进展*\n"
                    "- *APOE4 在阿尔茨海默病中的作用机制*\n\n"
                    "Agent 会自动搜索 PubMed，阅读相关文献，"
                    "然后给你一份结构化的文献综合分析报告。"
                )

            for msg in messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 输入框
        chat_input = st.chat_input(
            "输入研究问题或对上次回答的反馈...",
            disabled=st.session_state.chat_analyzing,
        )

        if chat_input and not st.session_state.chat_analyzing:
            # 显示用户消息
            st.session_state.chat_messages.append({"role": "user", "content": chat_input})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(chat_input)

            # 执行研究迭代
            st.session_state.chat_analyzing = True
            with chat_container:
                with st.chat_message("assistant"):
                    status_placeholder = st.empty()
                    status_placeholder.info("🔍 正在搜索 PubMed 文献...")

                    async def do_research():
                        return await analyzer.research_iteration(
                            chat_input, max_papers=10,
                        )

                    try:
                        result = asyncio.run(do_research())
                        answer = result.get("answer", "分析完成，但未生成回答。")
                        papers_count = result.get("papers_analyzed", 0)

                        status_placeholder.empty()
                        st.markdown(answer)

                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": answer}
                        )

                    except Exception as e:
                        status_placeholder.error(f"分析出错: {e}")
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": f"❌ 分析过程中出现错误: {e}",
                        })
                    finally:
                        st.session_state.chat_analyzing = False

            st.rerun()

        elif chat_input and st.session_state.chat_analyzing:
            st.warning("正在分析中，请等待当前分析完成...")

else:
    # 非结果状态时也提供对话入口
    if st.session_state.analyzer is None:
        st.session_state.analyzer = LiteratureAnalyzer()

# ── 页脚 ────────────────────────────────────
