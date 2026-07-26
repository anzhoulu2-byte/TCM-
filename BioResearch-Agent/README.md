# 🧬 BioResearch-Agent

**生物医学研究自动化平台** — 基于 AI Agent 的科研全流程自动化工具。

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![Tests](https://github.com/user/bioresearch-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/user/bioresearch-agent/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen)](https://docker.com)

---

## 📖 项目简介

BioResearch-Agent 是一个面向生物医学研究者的智能自动化平台，利用**大语言模型 (DeepSeek/OpenAI)** 和**多 Agent 协作**技术，覆盖从文献理解、数据检索、生物信息学分析、靶点发现、实验方案设计到研究报告生成的全流程。

**核心能力：**

| 阶段 | 模块 | 功能 |
|------|------|------|
| 🧠 理解 | Module 01 | 自然语言意图分类 + 任务自动规划 |
| 📚 检索 | Module 02 | PubMed / Open Targets 多源数据检索 |
| 🔬 分析 | Module 03 | 差异表达 / GO-KEGG 富集 / 生存分析 / 可视化 |
| 🎯 靶点 | Module 04 | 6 维评分 / 多智能体推理 / 机器学习排序 |
| 🧪 方案 | Module 05 | 实验方案生成 / 资源推荐 / 可行性分析 |
| 📋 报告 | Module 06 | 溯源追踪 / 报告生成 / 多格式导出 / 可迁移工作流 |

---

## ✨ 功能特性

- **🤖 AI 驱动** — 基于 DeepSeek LLM 的意图理解和多智能体推理
- **🔗 多源数据** — 整合 PubMed、Open Targets、NCBI 等生物医学数据库
- **📊 完整分析链路** — 从原始问题到靶点候选的一键式分析
- **🎯 多维度评分** — 文献支持、表达差异、功能重要性、可药性、新颖性、安全性
- **🧪 智能方案生成** — 自动生成实验方案 + 资源品牌推荐 + 可行性评估
- **📝 学术级报告** — 结构化学术论文格式报告（HTML / PDF / JSON）
- **🔄 可迁移工作流** — 完整溯源追踪 + 工作流导出/导入，确保可复现
- **🌐 双界面** — 命令行 (CLI) + Web (Streamlit) 两种交互方式
- **🐳 Docker 支持** — 一键容器化部署

---

## 🚀 快速开始

### 前置条件

- Python 3.10+
- [DeepSeek API Key](https://platform.deepseek.com/)（推荐）或 OpenAI API Key
- PubMed 邮箱（NCBI E-utilities 要求）

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/bioresearch-agent.git
cd BioResearch-Agent

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DEEPSEEK_API_KEY=sk-your_key_here
OPENAI_API_KEY=sk-your_key_here
PUBMED_EMAIL=your_email@example.com
```

### 3. 运行

#### Web 界面（推荐）

```bash
streamlit run app/streamlit_app.py
```

打开浏览器访问 `http://localhost:8501`

#### 交互式命令行

```bash
python src/main.py --interactive
```

#### 快速模式

```bash
python src/main.py --question "探索阿尔茨海默病的生物标志物"
```

#### 批量处理

```bash
python src/main.py --file examples/example_question.json
```

---

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -t bioresearch-agent .

# 运行容器
docker run -p 8501:8501 --env-file .env bioresearch-agent
```

---

## 🧪 测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_intent_classifier.py -v
pytest tests/test_end_to_end.py -v

# 查看覆盖率
pip install pytest-cov
pytest tests/ --cov=src/
```

---

## 📁 项目结构

```
BioResearch-Agent/
├── app/                         # Web 界面 (Streamlit)
│   └── streamlit_app.py
├── src/                         # 源代码
│   ├── config.py                # 全局配置
│   ├── main.py                  # CLI 主入口
│   ├── models/schemas.py        # Pydantic 数据模型
│   ├── modules/
│   │   ├── module_01_understanding/  # 意图分类 + 任务规划
│   │   ├── module_02_retrieval/      # PubMed + Open Targets
│   │   ├── module_03_analysis/       # DE + GO/KEGG + 生存分析
│   │   ├── module_04_target/         # 评分 + 推理 + 排序
│   │   ├── module_05_protocol/       # 方案 + 资源 + 可行性
│   │   └── module_06_report/         # 溯源 + 报告 + 导出
│   └── utils/                  # 工具函数
├── tests/                       # 单元测试
├── examples/                    # 示例文件
├── outputs/                     # 输出目录
├── data/                        # 数据目录
├── Dockerfile                   # Docker 构建
├── requirements.txt             # Python 依赖
└── .env.example                 # 环境变量模板
```

---

## 🧩 模块详解

### Module 01 — 问题理解与规划
- `IntentClassifier`: 调用 LLM 分析研究问题，提取疾病类型、研究目的、所需数据
- `TaskPlanner`: 根据意图生成有序的任务流水线（文献检索 → 表达分析 → 靶点排序）

### Module 02 — 文献与数据检索
- `PubMedClient`: NCBI E-utilities API 封装，速率限制 + 缓存
- `OpenTargetsClient`: Open Targets GraphQL API 封装
- `LiteratureRetriever`: 统一检索接口，自动构建布尔查询

### Module 03 — 生信分析核心
- `DifferentialExpression`: t-test / Wilcoxon + BH 校正 + log2FC
- `EnrichmentAnalyzer`: GO (BP/CC/MF) + KEGG 通路富集
- `SurvivalAnalyzer`: Kaplan-Meier + Log-rank + Cox 回归
- `AnalysisVisualizer`: 火山图 / 热图 / GO 气泡图 / KM 曲线
- `AnalysisOrchestrator`: 一键串联全部分析

### Module 04 — 靶点发现与推理
- `TargetScorer`: 6 维度评分（文献 / 表达 / 功能 / 可药性 / 新颖性 / 安全性）
- `MultiAgentReasoner`: 4 智能体（文献 + 组学 + 网络 + 批判）协作推理
- `TargetPrioritizer`: 加权排序 + LightGBM/XGBoost + 人工反馈调整

### Module 05 — 实验方案生成
- `ProtocolGenerator`: 7 部分结构化方案 + Word 文档导出
- `ResourceRecommender`: 细胞系 / 抗体 / 检测 / 统计方法推荐
- `FeasibilityAnalyzer`: 时间 / 资金 / 技术 / 成功率 / 伦理 5 维评估

### Module 06 — 溯源与报告
- `TraceabilityTracker`: 全步骤溯源日志 + 可迁移工作流
- `ReportGenerator`: 摘要 / Markdown / HTML 三种报告
- `ReportExporter`: HTML / JSON / PDF / 工作流 四种导出

---

## 🔧 配置选项

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| DeepSeek Key | `DEEPSEEK_API_KEY` | `""` | LLM API 密钥 |
| OpenAI Key | `OPENAI_API_KEY` | `""` | 备选 LLM |
| PubMed Email | `PUBMED_EMAIL` | `""` | NCBI 要求提供 |
| 日志级别 | `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING |
| 请求超时 | `REQUEST_TIMEOUT` | `60` | HTTP 超时秒数 |
| 最大重试 | `MAX_RETRIES` | `3` | API 重试次数 |

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

### 开发规范

- 使用 `pre-commit` 检查代码质量
- 所有新功能需包含单元测试（pytest）
- 代码需通过 `flake8` 和 `mypy` 检查
- 遵循 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

### 本地开发

```bash
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
pytest tests/
```

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [DeepSeek](https://deepseek.com/) 提供大语言模型 API
- [NCBI](https://www.ncbi.nlm.nih.gov/) 提供 E-utilities API
- [Open Targets](https://www.opentargets.org/) 提供靶点数据平台
- [Streamlit](https://streamlit.io/) 提供 Web 框架
