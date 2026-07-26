"""
Module 06: 溯源与报告生成层 (Traceability & Report Generation)。

记录全流程溯源信息，生成结构化研究报告（Markdown / HTML / PDF），
支持多格式导出和可迁移的工作流文件。
"""

from .traceability import TraceabilityTracker
from .report_generator import ReportGenerator
from .exporter import ReportExporter

__all__ = [
    "TraceabilityTracker",
    "ReportGenerator",
    "ReportExporter",
]
