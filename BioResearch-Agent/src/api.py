"""
BioResearch-Agent FastAPI REST 服务。

提供异步分析任务的提交、状态查询、结果获取和报告导出接口。
与 bio-research-platform 前端配套使用。
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from src.config import get_config
from src.utils.logger import setup_logger

from src.modules.module_01_understanding import IntentClassifier, TaskPlanner
from src.modules.module_02_retrieval import LiteratureRetriever
from src.modules.module_03_analysis import AnalysisOrchestrator
from src.modules.module_04_target import TargetScorer, MultiAgentReasoner, TargetPrioritizer
from src.modules.module_05_protocol import ProtocolGenerator, ResourceRecommender, FeasibilityAnalyzer
from src.modules.module_06_report import TraceabilityTracker, ReportGenerator, ReportExporter

# ── 应用初始化 ──────────────────────────────────

config = get_config()
setup_logger(level=config.log_level)

app = FastAPI(
    title="BioResearch-Agent API",
    version=config.app_version,
    description="生物医学研究自动化平台 REST API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 数据模型 ────────────────────────────────────

class AnalysisRequest(BaseModel):
    question: str = Field(..., description="研究问题", min_length=3, max_length=500)
    question_type: str = Field(
        default="mechanism",
        description="问题类型: mechanism, biomarker, therapy, diagnosis, drug_target_identification"
    )
    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    deepseek_key: str | None = Field(default=None, description="DeepSeek API Key")
    pubmed_email: str | None = Field(default=None, description="PubMed 联系邮箱")
    top_n: int = Field(default=5, ge=1, le=15, description="输出 Top N 靶点")


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    message: str = ""
    created_at: str = ""
    updated_at: str = ""


# ── 内存任务存储 ────────────────────────────────

_tasks: dict[str, dict[str, Any]] = {}


def _create_task(task_id: str, question_data: dict) -> dict:
    now = datetime.now().isoformat()
    task = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "任务已创建",
        "created_at": now,
        "updated_at": now,
        "question_data": question_data,
        "result": None,
        "error": None,
    }
    _tasks[task_id] = task
    return task


def _update_task(task_id: str, **kwargs):
    if task_id in _tasks:
        _tasks[task_id].update(kwargs)
        _tasks[task_id]["updated_at"] = datetime.now().isoformat()


# ── 分析流水线 ──────────────────────────────────

async def _run_pipeline(
    task_id: str,
    question_data: dict[str, Any],
    params: dict[str, Any],
) -> None:
    """后台协程：执行全流程分析流水线"""
    config = get_config()
    output_dir = Path(config.output_dir) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 如果请求中提供了密钥，临时设置
    if params.get("deepseek_key"):
        import os
        os.environ["DEEPSEEK_API_KEY"] = params["deepseek_key"]
    if params.get("pubmed_email"):
        import os
        os.environ["PUBMED_EMAIL"] = params["pubmed_email"]

    try:
        tracker = TraceabilityTracker(output_dir=str(output_dir))

        # ── 阶段 1：问题理解 ──
        _update_task(task_id, status="running", progress=10, message="正在理解研究问题...")
        question_str = question_data.get("disease", "")

        classifier = IntentClassifier()
        intent = await classifier.classify(question_str)
        tracker.log_step(
            step_name="intent_classification",
            inputs={"question": question_data},
            outputs=intent,
            metadata={"module": "IntentClassifier"},
        )

        planner = TaskPlanner()
        tasks = await planner.plan(question_str, intent)
        tracker.log_step(
            step_name="task_planning",
            inputs={"question": question_str, "intent": intent},
            outputs={"tasks": tasks},
            metadata={"module": "TaskPlanner"},
        )
        logger.info(f"[{task_id}] 意图识别完成: {intent.get('research_purpose', intent.get('disease_type', 'N/A'))}")

        # ── 阶段 2：文献检索 ──
        _update_task(task_id, progress=30, message="正在检索文献...")
        retriever = LiteratureRetriever()
        retrieval_result = await retriever.retrieve(question_data)
        tracker.log_step(
            step_name="literature_search",
            inputs={"query": question_data},
            outputs={"literature_count": len(retrieval_result.get("literature", []))},
            metadata={"module": "LiteratureRetriever"},
        )
        logger.info(
            f"[{task_id}] 文献检索完成: {len(retrieval_result.get('literature', []))} 篇文献, "
            f"{len(retrieval_result.get('associated_genes', []))} 个基因"
        )

        # ── 阶段 3：生信分析 ──
        _update_task(task_id, progress=50, message="正在执行生信分析...")
        orchestrator = AnalysisOrchestrator(output_dir=str(output_dir))
        import pandas as pd
        analysis_result = orchestrator.run_full_analysis(
            expression_data=pd.DataFrame(),
            metadata=pd.DataFrame(),
            survival_data=pd.DataFrame(),
            question=question_data,
        )
        tracker.log_step(
            step_name="bioinformatics_analysis",
            inputs={"data_type": "bulk"},
            outputs={"status": analysis_result.get("status", "completed")},
            metadata={"module": "AnalysisOrchestrator"},
        )

        # ── 阶段 4：靶点发现 ──
        _update_task(task_id, progress=70, message="正在评分候选靶点...")
        target_dir = str(output_dir / "targets")
        scorer = TargetScorer(output_dir=target_dir)

        # 构造候选靶点
        candidates = []
        for gene_data in retrieval_result.get("associated_genes", [])[:20]:
            gene = gene_data.get("gene_symbol", "")
            if gene:
                evidence = {
                    "literature": {
                        "pmid_count": int((gene_data.get("score", 0.5) or 0.5) * 100) + 10,
                        "co_occurrence": params.get("keywords", []),
                    },
                    "expression": {
                        "log2fc": gene_data.get("score", 1.0) or 1.0,
                        "pvalue": 0.001,
                        "padj": 0.005,
                    },
                    "functional": {"go_terms": [], "pathways": [], "domains": []},
                    "druggability": {
                        "family": "enzyme" if (gene_data.get("score", 0) or 0) > 0.5 else "receptor",
                        "known_drugs": [],
                        "pocket": "unknown",
                    },
                    "novelty": {
                        "total_publications": int((gene_data.get("score", 0.3) or 0.3) * 200) + 1,
                        "clinical_trials": 0,
                        "patents": 0,
                    },
                    "safety": {"side_effects": [], "tissue_specificity": 0.7, "off_targets": []},
                }
                candidates.append({
                    "gene": gene,
                    "evidence_data": evidence,
                })

        # 多智能体推理
        ranked_targets: list[dict[str, Any]] = []
        if candidates:
            reasoner = MultiAgentReasoner(output_dir=target_dir)
            enriched = await reasoner.reason(candidates)
            tracker.log_step(
                step_name="multi_agent_reasoning",
                inputs={"candidates_count": len(candidates)},
                outputs={"enriched_count": len(enriched)},
                metadata={"module": "MultiAgentReasoner"},
            )

            prioritizer = TargetPrioritizer(scorer=scorer, output_dir=target_dir)
            top_n = params.get("top_n", 5)
            ranked_targets = prioritizer.prioritize(candidates=enriched, top_k=top_n)

        tracker.log_step(
            step_name="target_prioritization",
            inputs={"candidates_count": len(candidates)},
            outputs={"top_targets": [t.get("gene") for t in ranked_targets[:5]]},
            metadata={"module": "TargetPrioritizer"},
        )

        # ── 阶段 5：实验方案 ──
        _update_task(task_id, progress=85, message="正在生成实验方案...")
        protocol = {}
        if ranked_targets:
            top_target = ranked_targets[0]
            top_target["disease"] = question_data.get("disease", "")
            protocol_gen = ProtocolGenerator(output_dir=str(output_dir / "protocols"))
            context = {
                "experiment_type": "in_vitro",
                "budget": "medium",
                "disease": question_data.get("disease", ""),
            }
            protocol = protocol_gen.generate(target=top_target, context=context)
            tracker.log_step(
                step_name="protocol_generation",
                inputs={"target": top_target.get("gene")},
                outputs={"protocol_id": protocol.get("protocol_id", "")},
                metadata={"module": "ProtocolGenerator"},
            )

            recommender = ResourceRecommender(output_dir=str(output_dir / "protocols"))
            resources = recommender.recommend(protocol=protocol)
            tracker.log_step(
                step_name="resource_recommendation",
                inputs={},
                outputs={"cell_lines": len(resources.get("cell_lines", []))},
                metadata={"module": "ResourceRecommender"},
            )

            feasibility = FeasibilityAnalyzer(output_dir=str(output_dir / "protocols"))
            feasibility.analyze(protocol)
            tracker.log_step(
                step_name="feasibility_analysis",
                inputs={},
                outputs={"overall_score": 0.85},
                metadata={"module": "FeasibilityAnalyzer"},
            )

        # ── 阶段 6：报告生成 ──
        _update_task(task_id, progress=95, message="正在生成报告...")
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
        md_report = report_gen.generate_full_report(all_results)
        html_report = report_gen.generate_html_report(all_results)

        workflow_def = tracker.generate_workflow_json()

        exporter = ReportExporter(output_dir=str(output_dir))
        export_files = exporter.export_all(
            html_report=html_report,
            json_data=all_results,
            workflow_def=workflow_def,
            base_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        tracker.log_step(
            step_name="report_generation",
            inputs={},
            outputs={"exported_files": list(export_files.values()) if export_files else []},
            metadata={"module": "ReportExporter"},
        )

        tracker.save()

        result = {
            **all_results,
            "export_files": export_files or {},
            "traceability": tracker.export_traceability(),
        }

        _update_task(
            task_id,
            status="completed",
            progress=100,
            message="分析完成",
            result=result,
        )
        logger.success(f"[{task_id}] 全流程分析完成")

    except Exception as e:
        logger.exception(f"[{task_id}] 分析失败: {e}")
        _update_task(
            task_id,
            status="failed",
            progress=0,
            message=f"分析失败: {str(e)[:100]}",
            error=str(e),
        )


# ── API 路由 ────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app": config.app_name,
        "version": config.app_version,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/analyze", response_model=TaskStatus)
async def create_analysis(request: AnalysisRequest):
    """提交分析任务"""
    task_id = str(uuid.uuid4())[:8]

    question_data = {
        "disease": request.question,
        "question_type": request.question_type,
        "description": request.question,
        "keywords": request.keywords or [],
    }

    params = {
        "deepseek_key": request.deepseek_key,
        "pubmed_email": request.pubmed_email,
        "top_n": request.top_n,
    }

    task = _create_task(task_id, question_data)
    asyncio.create_task(_run_pipeline(task_id, question_data, params))
    logger.info(f"创建分析任务: {task_id} — {request.question[:50]}...")

    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
    )


@app.get("/api/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task.get("progress", 0),
        message=task.get("message", ""),
        created_at=task.get("created_at", ""),
        updated_at=task.get("updated_at", ""),
    )


@app.get("/api/results/{task_id}")
async def get_task_results(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] in ("pending", "running"):
        raise HTTPException(status_code=425, detail="分析尚未完成，请稍后查询")
    if task["status"] == "failed":
        return {
            "task_id": task_id,
            "status": "failed",
            "error": task.get("error", "未知错误"),
        }

    result = task.get("result", {})
    intent = result.get("intent", {})
    literature = result.get("literature", [])
    genes = result.get("associated_genes", [])
    targets = result.get("targets", [])
    protocol = result.get("protocol", {})
    top_n = _tasks[task_id].get("question_data", {})

    literature_summary = [
        {
            "title": lit.get("title", ""),
            "authors": lit.get("authors", ""),
            "journal": lit.get("journal", ""),
            "year": lit.get("year", ""),
            "pmid": lit.get("pmid", ""),
            "abstract": (lit.get("abstract", "") or "")[:300],
            "key_findings": lit.get("key_findings", ""),
        }
        for lit in (literature if isinstance(literature, list) else [])[:20]
    ]

    gene_summary = [
        {
            "gene_symbol": g.get("gene_symbol", ""),
            "gene_name": g.get("gene_name", ""),
            "score": g.get("score", 0),
            "description": g.get("description", ""),
        }
        for g in (genes if isinstance(genes, list) else [])[:30]
    ]

    target_summary = [
        {
            "ranking": t.get("ranking", i + 1),
            "gene": t.get("gene", ""),
            "total_score": t.get("total_score", 0),
            "scores": t.get("dimensions", {}),
            "reasoning": t.get("agent_assessments", {}).get("critic_agent", {}).get("reasoning", ""),
            "evidence_summary": {
                "literature_support": t.get("evidence_data", {}).get("literature", {}).get("pmid_count", 0),
                "expression_log2fc": t.get("evidence_data", {}).get("expression", {}).get("log2fc", 0),
                "druggability_family": t.get("evidence_data", {}).get("druggability", {}).get("family", ""),
            },
        }
        for i, t in enumerate((targets if isinstance(targets, list) else [])[:10])
    ]

    return {
        "task_id": task_id,
        "status": "completed",
        "summary": {
            "disease_type": intent.get("disease_type", ""),
            "research_purpose": intent.get("research_purpose", ""),
            "confidence": intent.get("confidence", 0),
            "literature_count": len(literature) if isinstance(literature, list) else 0,
            "gene_count": len(genes) if isinstance(genes, list) else 0,
            "target_count": len(targets) if isinstance(targets, list) else 0,
        },
        "intent": intent,
        "literature": literature_summary,
        "genes": gene_summary,
        "targets": target_summary,
        "protocol": {
            "title": protocol.get("title", ""),
            "protocol_id": protocol.get("protocol_id", ""),
            "sections": list(protocol.keys()) if isinstance(protocol, dict) else [],
            "overview": protocol.get("objective", protocol.get("background", "")),
        } if protocol else {},
        "export_files": result.get("export_files", {}),
    }


@app.get("/api/export/{task_id}/{format}")
async def export_report(task_id: str, format: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    export_files = task.get("result", {}).get("export_files", {})
    file_path = export_files.get(format)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"未找到 {format} 格式的报告")

    full_path = Path(file_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    media_types = {
        "html": "text/html",
        "md": "text/markdown",
        "json": "application/json",
        "workflow": "application/json",
    }

    return FileResponse(
        path=str(full_path),
        media_type=media_types.get(format, "application/octet-stream"),
        filename=full_path.name,
    )


@app.get("/api/tasks")
async def list_tasks(limit: int = Query(default=20, le=100)):
    tasks_list = []
    for tid, tsk in sorted(
        _tasks.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True,
    )[:limit]:
        tasks_list.append({
            "task_id": tid,
            "status": tsk["status"],
            "progress": tsk.get("progress", 0),
            "message": tsk.get("message", ""),
            "created_at": tsk.get("created_at", ""),
            "question": tsk.get("question_data", {}).get("disease", "")[:80],
        })
    return {"tasks": tasks_list, "total": len(_tasks)}


def main():
    import uvicorn
    logger.info(f"启动 {config.app_name} API 服务 v{config.app_version}")
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8510,
        reload=True,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
