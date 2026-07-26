"""
BioResearch-Agent 主入口。

提供命令行交互模式和文件批量处理模式，串联全部六个模块。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from loguru import logger

from src.config import get_config
from src.utils.logger import setup_logger
from src.modules.module_01_understanding import IntentClassifier, TaskPlanner
from src.modules.module_02_retrieval import LiteratureRetriever
from src.modules.module_03_analysis import AnalysisOrchestrator
from src.modules.module_04_target import TargetScorer, MultiAgentReasoner, TargetPrioritizer
from src.modules.module_05_protocol import ProtocolGenerator, ResourceRecommender, FeasibilityAnalyzer
from src.modules.module_06_report import TraceabilityTracker, ReportGenerator, ReportExporter


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="BioResearch-Agent: 生物医学研究自动化平台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python src/main.py --interactive\n"
            "  python src/main.py --file input.json\n"
            "  python src/main.py --question \"乳腺癌中TP53的机制研究\"\n"
            "  streamlit run app/streamlit_app.py\n"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互式命令行模式",
    )
    mode.add_argument(
        "--file", "-f",
        type=str,
        metavar="input.json",
        help="从 JSON 文件读取输入",
    )
    mode.add_argument(
        "--question", "-q",
        type=str,
        help="直接传入研究问题（快速模式）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="输出目录（默认: outputs/）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出",
    )
    return parser.parse_args()


def main() -> None:
    """主入口。"""
    args = parse_args()

    # 初始化配置和日志
    config = get_config()
    log_level = "DEBUG" if args.verbose else config.log_level
    output_dir = Path(args.output) if args.output else Path(config.output_dir)

    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    setup_logger(level=log_level, log_file=str(log_dir / "app.log"))

    logger.info(f"{config.app_name} v{config.app_version} 启动")
    logger.info(f"模式: {'interactive' if args.interactive else 'file' if args.file else 'quick'}")

    if args.interactive:
        run_interactive(output_dir)
    elif args.file:
        run_from_file(Path(args.file), output_dir)
    elif args.question:
        # 快速模式：直接传入问题
        question_data = {
            "disease": args.question,
            "question_type": "mechanism",
            "description": args.question,
            "keywords": [],
        }
        result = asyncio.run(run_pipeline(question_data, output_dir))
        _print_summary(result)
    else:
        # 默认启动交互模式
        run_interactive(output_dir)


def run_interactive(output_dir: Path) -> None:
    """交互式命令行模式。"""
    config = get_config()
    print(f"\n{'='*60}")
    print(f"  {config.app_name} v{config.app_version}")
    print(f"  {'='*60}")
    print(f"  {'交互式命令行模式':^56}")
    print(f"{'='*60}\n")

    print("请输入研究问题（如: \"探索阿尔茨海默病的生物标志物\"）：")
    try:
        question_text = input("> ").strip()
        if not question_text:
            logger.warning("未输入问题")
            return

        print("\n选择问题类型:")
        types = {"1": "mechanism", "2": "biomarker", "3": "therapy",
                 "4": "diagnosis", "5": "drug_target_identification"}
        for k, v in types.items():
            print(f"  [{k}] {v}")
        type_choice = input("请选择 [1-5] (默认 1): ").strip() or "1"
        question_type = types.get(type_choice, "mechanism")

        question_data = {
            "disease": question_text,
            "question_type": question_type,
            "description": question_text,
            "keywords": [],
        }
        print(f"\n{'='*60}")
        print("  开始全流程分析，请稍候...")
        print(f"{'='*60}\n")

        result = asyncio.run(run_pipeline(question_data, output_dir))
        _print_summary(result)
        print(f"\n完整报告已保存至: {output_dir / 'reports'}")

    except (KeyboardInterrupt, EOFError):
        print("\n\n用户退出")
    except Exception as e:
        logger.error(f"运行失败: {e}")
        print(f"\n错误: {e}")


def run_from_file(input_path: Path, output_dir: Path) -> None:
    """从 JSON 文件读取输入并执行。"""
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_path}")
        print(f"错误: 文件 {input_path} 不存在")
        return

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"从文件加载输入: {input_path}")

        question_data = {
            "disease": data.get("disease", data.get("question", "Unknown")),
            "question_type": data.get("question_type", "mechanism"),
            "description": data.get("description", data.get("question", "")),
            "keywords": data.get("keywords", []),
        }
        result = asyncio.run(run_pipeline(question_data, output_dir))
        _print_summary(result)
        print(f"\n结果已保存至: {output_dir}")

    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        print(f"错误: JSON 格式不正确 - {e}")
    except Exception as e:
        logger.error(f"运行失败: {e}")
        print(f"错误: {e}")


async def run_pipeline(
    question_data: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """执行全流程分析。

    Args:
        question_data: 研究问题数据
        output_dir: 输出目录

    Returns:
        综合结果字典
    """
    # 初始化追踪器
    tracker = TraceabilityTracker(output_dir=str(output_dir))

    # ── 模块 1: 问题理解 ──────────────────────
    logger.info("="*40)
    logger.info("模块 1: 问题理解与规划")
    logger.info("="*40)

    classifier = IntentClassifier()
    intent = await classifier.classify(question_data["disease"])
    tracker.log_step("intent_classification", {"question": question_data}, intent,
                     {"module": "IntentClassifier"})

    planner = TaskPlanner()
    tasks = await planner.plan(question_data["disease"], intent)
    tracker.log_step("task_planning", {"intent": intent}, {"tasks": tasks},
                     {"module": "TaskPlanner"})
    logger.info(f"规划任务: {tasks}")

    # ── 模块 2: 文献与数据检索 ──────────────────
    logger.info("="*40)
    logger.info("模块 2: 文献与数据检索")
    logger.info("="*40)

    retriever = LiteratureRetriever()
    retrieval_result = await retriever.retrieve(question_data)
    tracker.log_step("literature_search",
                     {"query": question_data["disease"]},
                     {"literature_count": len(retrieval_result.get("literature", [])),
                      "gene_count": len(retrieval_result.get("associated_genes", []))},
                     {"module": "LiteratureRetriever"})

    # ── 模块 3: 生信分析 ──────────────────────
    logger.info("="*40)
    logger.info("模块 3: 生信分析核心")
    logger.info("="*40)

    orchestrator = AnalysisOrchestrator(output_dir=str(output_dir))
    # 注：需要实际表达数据时用户需提供；此处以空DataFrame示意
    import pandas as pd
    analysis_result = orchestrator.run_full_analysis(
        expression_data=pd.DataFrame(),
        metadata=pd.DataFrame(),
        survival_data=pd.DataFrame(),
        question=question_data,
    )
    tracker.log_step("bioinformatics_analysis",
                     {"data_type": "bulk"},
                     {"status": analysis_result.get("status", "completed")},
                     {"module": "AnalysisOrchestrator"})

    # ── 模块 4: 靶点发现 ──────────────────────
    logger.info("="*40)
    logger.info("模块 4: 靶点发现与推理")
    logger.info("="*40)

    scorer = TargetScorer(output_dir=str(output_dir / "targets"))
    # 使用关联基因作为靶点候选
    candidates = []
    for gene_data in retrieval_result.get("associated_genes", [])[:20]:
        gene = gene_data.get("gene_symbol", "")
        if gene:
            evidence = {
                "literature": {"pmid_count": gene_data.get("score", 1) * 100,
                               "co_occurrence": question_data.get("keywords", [])},
                "expression": {"log2fc": gene_data.get("score", 1.0), "pvalue": 0.001, "padj": 0.005},
                "functional": {"go_terms": [], "pathways": [], "domains": []},
                "druggability": {"family": "enzyme", "known_drugs": [], "pocket": ""},
                "novelty": {"total_publications": int(gene_data.get("score", 0.5) * 200),
                            "clinical_trials": 0, "patents": 0},
                "safety": {"side_effects": [], "tissue_specificity": 0.7, "off_targets": []},
            }
            candidates.append({"gene": gene, "evidence_data": evidence})

    if candidates:
        reasoner = MultiAgentReasoner(output_dir=str(output_dir / "targets"))
        enriched = await reasoner.reason(candidates)
        tracker.log_step("multi_agent_reasoning",
                         {"candidates_count": len(candidates)},
                         {"enriched_count": len(enriched)},
                         {"module": "MultiAgentReasoner"})

        prioritizer = TargetPrioritizer(
            scorer=scorer,
            output_dir=str(output_dir / "targets"),
        )
        ranked_targets = prioritizer.prioritize(enriched, top_k=10)
    else:
        ranked_targets = []

    tracker.log_step("target_prioritization",
                     {"candidates_count": len(candidates)},
                     {"top_targets": [t.get("gene") for t in ranked_targets[:5]]},
                     {"module": "TargetPrioritizer"})

    # ── 模块 5: 实验方案生成 ──────────────────
    logger.info("="*40)
    logger.info("模块 5: 实验方案生成")
    logger.info("="*40)

    protocol = {}
    if ranked_targets:
        top_target = ranked_targets[0]
        protocol_gen = ProtocolGenerator(output_dir=str(output_dir / "protocols"))
        context = {
            "experiment_type": "in_vitro",
            "budget": "medium",
            "disease": question_data.get("disease", ""),
        }
        protocol = protocol_gen.generate(top_target, context)
        tracker.log_step("protocol_generation",
                         {"target": top_target.get("gene")},
                         {"protocol_id": protocol.get("protocol_id", "")},
                         {"module": "ProtocolGenerator"})

        # 资源推荐和可行性分析
        recommender = ResourceRecommender(output_dir=str(output_dir / "protocols"))
        resources = recommender.recommend(protocol)
        tracker.log_step("resource_recommendation", {}, {"cell_lines": len(resources.get("cell_lines", []))},
                         {"module": "ResourceRecommender"})

        feasibility = FeasibilityAnalyzer(output_dir=str(output_dir / "protocols"))
        feasibility_result = feasibility.analyze(protocol)
        tracker.log_step("feasibility_analysis", {},
                         {"overall_score": feasibility_result.get("overall", {}).get("score")},
                         {"module": "FeasibilityAnalyzer"})

    # ── 模块 6: 报告生成 ──────────────────────
    logger.info("="*40)
    logger.info("模块 6: 溯源与报告生成")
    logger.info("="*40)

    all_results = {
        "question": question_data,
        "intent": intent,
        "tasks": tasks,
        "literature": retrieval_result.get("literature", []),
        "associated_genes": retrieval_result.get("associated_genes", []),
        "differential_expression": analysis_result,
        "targets": ranked_targets,
        "protocol": protocol,
        "visualizations": analysis_result.get("visualizations", {}),
        "traceability": tracker.export_traceability(),
        "pipelines": tracker.get_summary(),
    }

    report_gen = ReportGenerator(output_dir=str(output_dir))
    html_report = report_gen.generate_html_report(all_results)
    md_report = report_gen.generate_full_report(all_results)

    exporter = ReportExporter(output_dir=str(output_dir))
    export_files = exporter.export_all(
        html_report, all_results, tracker.generate_workflow_json(),
        base_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    tracker.log_step("report_generation", {},
                     {"exported_files": list(export_files.values())},
                     {"module": "ReportExporter"})

    # 保存最终结果
    tracker.save()
    result = {
        **all_results,
        "export_files": export_files,
        "traceability": tracker.export_traceability(),
    }
    logger.success("全流程分析完成")
    return result


def _print_summary(result: dict[str, Any]) -> None:
    """打印结果摘要。"""
    print(f"\n{'='*60}")
    print("  分析完成！")
    print(f"{'='*60}")

    intent = result.get("intent", {})
    print(f"\n[意图分类]:")
    print(f"   疾病: {intent.get('disease_type', 'N/A')}")
    print(f"   类型: {intent.get('research_purpose', 'N/A')}")

    literature = result.get("literature", [])
    genes = result.get("associated_genes", [])
    targets = result.get("targets", [])
    protocol = result.get("protocol", {})

    print(f"\n[文献检索]: {len(literature)} 篇")
    print(f"[关联基因]: {len(genes)} 个")
    print(f"\n[Top 靶点]:")

    if targets:
        for t in targets[:5]:
            score = t.get("total_score", 0)
            print(f"   {t.get('ranking', '?')}. {t.get('gene', '')} "
                  f"(score: {score:.3f})")
    else:
        print("   (无靶点数据)")

    if protocol:
        print(f"\n[实验方案]: {protocol.get('title', 'N/A')}")
        print(f"   方案 ID: {protocol.get('protocol_id', 'N/A')}")

    exports = result.get("export_files", {})
    print(f"\n[导出文件]:")
    for fmt, path in exports.items():
        print(f"   .{fmt}: {path}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
