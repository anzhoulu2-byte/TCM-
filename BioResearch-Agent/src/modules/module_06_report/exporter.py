"""
报告导出器 (ReportExporter)。

支持将研究报告导出为 PDF、HTML、JSON 和可迁移的工作流格式。
工作流文件可在新的环境中复现完整的分析流程。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.config import get_config


class ReportExporter:
    """报告导出器。

    支持四种导出格式：
    - PDF: 通过 weasyprint / pdfkit 渲染
    - HTML: 独立网页格式
    - JSON: 结构化数据格式
    - Workflow JSON: 可迁移的工作流定义

    Attributes:
        output_dir: 导出文件输出目录
    """

    def __init__(self, output_dir: str | None = None) -> None:
        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "reports"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ReportExporter 初始化, output_dir={self._output_dir}")

    # ── PDF 导出 ──────────────────────────────

    def export_pdf(self, content: str, path: str | None = None) -> str:
        """导出报告为 PDF 格式。

        优先使用 weasyprint，如果不可用则回退到 pdfkit。

        Args:
            content: HTML 格式的报告内容
            path: 输出文件路径，默认自动生成

        Returns:
            输出文件的路径
        """
        output_path = self._resolve_path(path, "report.pdf")

        # 确保内容包含完整 HTML 结构
        if not content.strip().startswith("<!DOCTYPE html>"):
            content = (
                "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                "<title>Research Report</title></head><body>"
                f"{content}</body></html>"
            )

        exported = False

        # 尝试 weasyprint
        try:
            from weasyprint import HTML

            HTML(string=content).write_pdf(str(output_path))
            logger.info(f"PDF 已导出 (weasyprint): {output_path}")
            exported = True
        except ImportError:
            logger.debug("weasyprint 未安装")

        # 尝试 pdfkit
        if not exported:
            try:
                import pdfkit

                pdfkit.from_string(content, str(output_path))
                logger.info(f"PDF 已导出 (pdfkit): {output_path}")
                exported = True
            except ImportError:
                logger.debug("pdfkit 未安装")

        # 回退：将 HTML 复制为 .pdf.html 作为替代
        if not exported:
            fallback_path = output_path.with_suffix(".pdf.html")
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.warning(
                f"PDF 导出器不可用，已将 HTML 保存为: {fallback_path}"
            )
            return str(fallback_path)

        return str(output_path)

    # ── HTML 导出 ─────────────────────────────

    def export_html(self, content: str, path: str | None = None) -> str:
        """导出报告为 HTML 格式。

        Args:
            content: HTML 报告内容
            path: 输出文件路径，默认自动生成

        Returns:
            输出文件的路径
        """
        output_path = self._resolve_path(path, "report.html")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"HTML 已导出: {output_path}")
        return str(output_path)

    # ── JSON 导出 ─────────────────────────────

    def export_json(self, data: dict[str, Any], path: str | None = None) -> str:
        """导出结果为 JSON 格式。

        包含所有分析步骤的结构化数据，便于程序化处理和二次分析。

        Args:
            data: 要导出的结构化解耦
            path: 输出文件路径，默认自动生成

        Returns:
            输出文件的路径
        """
        output_path = self._resolve_path(path, "report.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"JSON 已导出: {output_path}")
        return str(output_path)

    # ── 工作流导出 (可迁移格式) ────────────────

    def export_workflow(self, workflow: dict[str, Any], path: str | None = None) -> str:
        """导出可迁移的工作流文件。

        工作流文件包含完整的分析步骤定义、输入参数和执行顺序，
        可以导入到新的 BioResearch-Agent 实例中复现分析流程。
        格式设计参考了 CWL (Common Workflow Language) 标准。

        Args:
            workflow: 工作流定义字典（来自 TraceabilityTracker.generate_workflow_json()）
            path: 输出文件路径，默认自动生成

        Returns:
            输出文件的路径
        """
        output_path = self._resolve_path(path, "workflow.json")

        # 确保工作流包含完整元数据
        workflow.setdefault("schema_version", "1.0")
        workflow.setdefault("created_at", datetime.now().isoformat())
        workflow.setdefault("export_format", "BioResearch-Agent Workflow")
        workflow.setdefault("description", "Reproducible analysis workflow")

        # 验证工作流结构
        if "pipeline" not in workflow:
            logger.warning("工作流缺少 'pipeline' 字段，正在创建空结构")
            workflow["pipeline"] = []

        # 为每个步骤添加规范化的输入/输出定义
        for step in workflow.get("pipeline", []):
            step.setdefault("inputs", {})
            step.setdefault("outputs", {})
            step.setdefault("requirements", {})
            step.setdefault("step_name", step.get("step_id", "unknown"))

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"工作流已导出 (可迁移): {output_path}")
        return str(output_path)

    # ── 批量导出 ──────────────────────────────

    def export_all(
        self,
        html_report: str,
        json_data: dict[str, Any],
        workflow_def: dict[str, Any],
        base_name: str = "report",
    ) -> dict[str, str]:
        """一键导出所有格式。

        Args:
            html_report: HTML 报告内容
            json_data: 结构化分析结果
            workflow_def: 工作流定义
            base_name: 基础文件名

        Returns:
            {"html": path, "json": path, "workflow": path, "pdf": path}
        """
        return {
            "html": self.export_html(html_report, f"{base_name}.html"),
            "json": self.export_json(json_data, f"{base_name}.json"),
            "workflow": self.export_workflow(workflow_def, f"{base_name}_workflow.json"),
        }

    # ── 辅助方法 ──────────────────────────────

    def _resolve_path(self, path: str | None, default_name: str) -> Path:
        """解析输出路径。"""
        if path:
            p = Path(path)
            if not p.is_absolute():
                p = self._output_dir / p
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        return self._output_dir / default_name
