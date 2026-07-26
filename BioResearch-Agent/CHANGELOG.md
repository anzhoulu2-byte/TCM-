# Changelog

All notable changes to BioResearch-Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-26

### 🚀 Initial Release

BioResearch-Agent 正式发布！一个基于 AI Agent 的生物医学研究全流程自动化平台。

### ✨ Features

#### Module 01 — 问题理解与规划
- `IntentClassifier`: 基于 DeepSeek LLM 的自然语言意图分类
  - 提取疾病类型、研究目的、所需数据类型
  - 自动重试机制（最多 3 次），失败时返回安全默认值
- `TaskPlanner`: 智能任务流水线规划
  - 基于意图生成有序任务列表
  - 10 种预定义生物医学分析任务

#### Module 02 — 文献与数据检索
- `PubMedClient`: NCBI E-utilities API 封装
  - 速率限制（3 次/秒），内存缓存（TTL 可配置）
  - esearch + esummary，全程 JSON 避免 XML 解析
- `OpenTargetsClient`: Open Targets GraphQL API 封装
  - 两阶段查询（疾病搜索 → 关联基因）
  - 按关联评分降序排列
- `LiteratureRetriever`: 多源检索整合器
  - 自动构建布尔查询（疾病 + 关键词 + 类型）
  - `asyncio.gather()` 并行检索

#### Module 03 — 生信分析核心
- `DifferentialExpression`: 差异表达分析
  - t-test / Wilcoxon 自适应选择（单细胞自动 Wilcoxon）
  - BH / Bonferroni 多重检验校正
  - 结果自动保存 CSV + JSON
- `EnrichmentAnalyzer`: GO / KEGG 通路富集分析
  - GO 三个子本体 (BP / CC / MF)
  - KEGG 通路富集
- `SurvivalAnalyzer`: Kaplan-Meier + Cox 回归
  - Log-rank 检验，C-index 评估
- `AnalysisVisualizer`: 出版级可视化（300 DPI）
  - 火山图（含 gene 标注）、表达热图、GO 气泡图、KM 曲线
- `AnalysisOrchestrator`: 一键全流程编排

#### Module 04 — 靶点发现与推理
- `TargetScorer`: 6 维度靶点评分
  - literature_support / expression_foldchange / functional_importance
  - druggability / novelty / safety
  - 权重可配置，动态调整，自动归一化
- `MultiAgentReasoner`: 多智能体推理引擎
  - LiteratureAgent + OmicsAgent + NetworkAgent + CriticAgent
  - LLM 推理 + 规则推理降级
- `TargetPrioritizer`: 多维加权排序 + 人工反馈
  - 贝叶斯融合人工评分与算法评分
  - LightGBM / XGBoost 排序模型（可选）
  - 排序柱状图 + 维度堆积图

#### Module 05 — 实验方案生成
- `ProtocolGenerator`: 7 部分结构化方案
  - 研究目标 / 实验设计 / 具体步骤 / 试剂耗材
  - 时间表 / 预期结果 / 备选方案
  - Word (.docx) 自动导出
  - 支持用户反馈迭代修改
- `ResourceRecommender`: 资源推荐器
  - 细胞系推荐（4 类疾病 + 通用细胞系）
  - 抗体品牌 + 货号推荐
  - 统计方法推荐
- `FeasibilityAnalyzer`: 5 维度可行性评估
  - 时间 / 资金 / 技术 / 成功率 / 伦理
  - 风险矩阵热图 + 雷达图可视化

#### Module 06 — 溯源与报告
- `TraceabilityTracker`: 全流程溯源追踪
  - 每条步骤记录：时间戳、输入、输出、工具版本、耗时
  - 自动处理 DataFrame 序列化
  - 可迁移工作流导出（JSON 格式）
- `ReportGenerator`: 3 种报告格式
  - 学术摘要 (~400 words)、完整 Markdown、CSS 样式化 HTML
  - 8 章节结构（背景/方法/结果/靶点/方案/溯源/局限/参考文献）
  - 图表 base64 内嵌
- `ReportExporter`: 4 种导出格式
  - HTML / JSON / PDF（weasyprint → pdfkit → fallback）/ 工作流

#### Web 界面 (Streamlit)
- 7 标签页结果展示（摘要 / 文献 / 靶点 / 方案 / 报告 / 溯源 / 工作流）
- Plotly 交互式雷达图 + 柱状图
- 亮色/暗色主题切换
- 工作流文件导入/导出
- 可排序靶点表格

#### CLI 主入口
- `--interactive`: 交互式对话模式
- `--file input.json`: 批量处理模式
- `--question "..."`: 快速模式
- `--verbose`: 详细日志输出

#### 部署
- `Dockerfile` 基于 python:3.10-slim
- `docker-compose.yml` 支持
- GitHub Actions CI（flake8 + mypy + pytest + Docker build）

### 🧪 Testing
- 88+ 个单元测试，覆盖全部模块
- 端到端集成测试（mock API）
- pytest + pytest-asyncio + pytest-cov

### 📦 Packaging
- `pyproject.toml` + `setup.cfg` 标准打包
- PyPI 发布脚本 (`package.py`)

---

## [0.9.0] - 2026-07-20

### Added
- 全部 6 个模块的初始实现
- Streamlit Web 界面的原型
- 基础 CLI 入口

### Fixed
- N/A (pre-release)

---

## [0.1.0] - 2026-07-01

### Added
- 项目骨架搭建
- Config 配置管理
- Pydantic 数据模型定义
- 目录结构初始化
