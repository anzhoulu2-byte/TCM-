"""
溯源追踪器 (TraceabilityTracker)。

记录工作流中每一步的执行信息：时间戳、输入参数、输出结果、
使用的工具/API 版本、执行耗时。支持导出为结构化 JSON。
实现完整的可复现性溯源链。
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.config import get_config


class TraceabilityTracker:
    """溯源追踪器。

    记录研究全流程中每个步骤的详细信息，确保结果可复现。
    支持步骤级日志、导出和统计汇总。

    Attributes:
        workflow_id: 工作流唯一标识
        steps: 已记录的步骤列表
        output_dir: 日志输出目录
    """

    def __init__(
        self,
        workflow_id: str | None = None,
        output_dir: str | None = None,
    ) -> None:
        self.workflow_id: str = workflow_id or f"WF-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.steps: list[dict[str, Any]] = []
        self._start_time: float = time.time()

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "traceability"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 记录起始元数据
        self._metadata = {
            "app_name": config.app_name,
            "app_version": config.app_version,
            "python_version": __import__("sys").version,
            "workflow_id": self.workflow_id,
        }

        # 初始化步骤
        self.log_step(
            step_name="workflow_init",
            inputs={"workflow_id": self.workflow_id},
            outputs={"status": "initialized"},
            metadata={"module": "TraceabilityTracker", "description": "工作流初始化"},
        )

        logger.info(f"TraceabilityTracker 初始化: workflow_id={self.workflow_id}")

    # ── 记录步骤 ──────────────────────────────

    def log_step(
        self,
        step_name: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """记录一个执行步骤。

        Args:
            step_name: 步骤名称（如 "literature_search", "differential_expression"）
            inputs: 输入参数字典
            outputs: 输出结果摘要
            metadata: 附加元数据（模块名、版本、耗时等）

        Returns:
            创建的步骤记录字典
        """
        step = {
            "step_id": f"STEP-{len(self.steps) + 1:03d}",
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "elapsed_from_start": round(time.time() - self._start_time, 3),
            "inputs": self._sanitize(inputs or {}),
            "outputs": self._sanitize(outputs or {}),
            "metadata": {
                "module": metadata.get("module", "unknown") if metadata else "unknown",
                "api_version": metadata.get("api_version", ""),
                "tool_version": metadata.get("tool_version", ""),
                **(metadata or {}),
            },
        }
        self.steps.append(step)
        logger.debug(f"[溯源] {step['step_id']} {step_name} - "
                     f"elapsed={step['elapsed_from_start']:.1f}s")
        return step

    # ── 查询 ──────────────────────────────────

    def get_traceability(self) -> list[dict[str, Any]]:
        """获取完整溯源记录。

        Returns:
            所有步骤的列表（按执行顺序）
        """
        return list(self.steps)

    def get_step(self, step_name: str) -> dict[str, Any] | None:
        """按名称获取特定步骤的记录。

        Args:
            step_name: 步骤名称

        Returns:
            步骤记录，未找到返回 None
        """
        for step in self.steps:
            if step["step_name"] == step_name:
                return step
        return None

    def get_summary(self) -> dict[str, Any]:
        """获取溯源汇总信息。"""
        total_time = round(time.time() - self._start_time, 2)
        module_counts: dict[str, int] = {}
        for step in self.steps:
            mod = step.get("metadata", {}).get("module", "unknown")
            module_counts[mod] = module_counts.get(mod, 0) + 1

        return {
            "workflow_id": self.workflow_id,
            "total_steps": len(self.steps),
            "total_elapsed_seconds": total_time,
            "modules_used": list(module_counts.keys()),
            "module_summary": module_counts,
            "first_step": self.steps[0]["timestamp"] if self.steps else "",
            "last_step": self.steps[-1]["timestamp"] if self.steps else "",
        }

    # ── 导出 ──────────────────────────────────

    def export_traceability(self) -> dict[str, Any]:
        """导出完整溯源记录为可序列化字典。

        Returns:
            包含元数据和所有步骤的结构化字典
        """
        summary = self.get_summary()
        return {
            "metadata": self._metadata,
            "summary": summary,
            "workflow_id": self.workflow_id,
            "generated_at": datetime.now().isoformat(),
            "steps": self.steps,
        }

    def save(self, filename: str | None = None) -> str:
        """保存溯源记录到 JSON 文件。

        Args:
            filename: 文件名（默认自动生成）

        Returns:
            文件路径
        """
        path = self._output_dir / (filename or f"traceability_{self.workflow_id}.json")
        data = self.export_traceability()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"溯源记录已保存: {path}")
        return str(path)

    # ── 辅助方法 ──────────────────────────────

    @staticmethod
    def _sanitize(obj: Any) -> Any:
        """清理不可序列化的对象（如 DataFrame 转为摘要）。"""
        import pandas as pd

        if isinstance(obj, pd.DataFrame):
            return {
                "_type": "DataFrame",
                "_shape": list(obj.shape),
                "_columns": list(obj.columns),
                "_preview": obj.head(3).to_dict("records"),
            }
        if isinstance(obj, pd.Series):
            return {
                "_type": "Series",
                "_length": len(obj),
                "_preview": obj.head(3).to_dict(),
            }
        if isinstance(obj, dict):
            return {k: TraceabilityTracker._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [TraceabilityTracker._sanitize(v) for v in obj[:100]]
        if hasattr(obj, "__class__") and not isinstance(obj, (str, int, float, bool)):
            return f"<{obj.__class__.__name__}: {str(obj)[:100]}>"
        return obj

    def generate_workflow_json(self) -> dict[str, Any]:
        """生成可迁移的工作流定义文件。

        包含所有步骤的输入参数和执行顺序，
        可在新的环境中复现整个分析流程。
        """
        workflow = {
            "workflow_id": self.workflow_id,
            "created_at": datetime.now().isoformat(),
            "schema_version": "1.0",
            "app": self._metadata,
            "pipeline": [],
        }
        for step in self.steps:
            if step["step_name"] == "workflow_init":
                continue
            workflow["pipeline"].append({
                "step_id": step["step_id"],
                "step_name": step["step_name"],
                "module": step.get("metadata", {}).get("module", ""),
                "inputs": step["inputs"],
                "elapsed_seconds": step.get("elapsed_from_start", 0),
            })
        return workflow
