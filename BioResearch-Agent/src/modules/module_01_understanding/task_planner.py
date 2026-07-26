"""
任务规划器 (Task Planner)。

根据研究问题和意图分类结果，调用 DeepSeek API (deepseek-v4-flash)
生成有序的任务执行流水线，供后续模块依次执行。

提供自动重试机制（最多 3 次）和降级默认流水线。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from loguru import logger

from src.config import get_config

# ── 系统提示词 ──────────────────────────────────

TASK_PLANNER_SYSTEM_PROMPT = """You are a biomedical research task planner. Given a research question and its classified intent, generate an ordered list of tasks to execute.

Available task types (choose only from this list):
- "literature_search": Search PubMed and other databases for relevant literature
- "gene_expression_analysis": Analyze gene expression data (e.g., differential expression)
- "pathway_enrichment": Perform pathway enrichment analysis (e.g., GO, KEGG)
- "protein_interaction_network": Build and analyze protein-protein interaction networks
- "target_prioritization": Prioritize drug targets based on multi-omics evidence
- "experimental_protocol_design": Design experimental validation protocols
- "report_generation": Generate the final research report
- "clinical_data_analysis": Analyze clinical or patient data
- "variant_analysis": Analyze genomic variants and mutations
- "biomarker_discovery": Identify potential biomarkers

Rules:
1. Tasks must be ordered by execution dependency (prerequisites first).
2. Only use task types from the available list above.
3. Respond ONLY with a JSON array of task strings, no additional text or markdown formatting.

Example:
["literature_search", "gene_expression_analysis", "pathway_enrichment", "target_prioritization", "experimental_protocol_design", "report_generation"]"""


class TaskPlanner:
    """任务规划器。

    基于意图分类结果，生成有序的任务流水线。
    每个任务对应一个下游功能模块。

    Attributes:
        api_key: DeepSeek API 密钥（从配置自动读取）
        model: 使用的模型名称
        max_retries: 最大重试次数
        timeout: HTTP 请求超时时间（秒）
        default_pipeline: 降级时使用的默认任务列表
    """

    _AVAILABLE_TASKS: set[str] = {
        "literature_search",
        "gene_expression_analysis",
        "pathway_enrichment",
        "protein_interaction_network",
        "target_prioritization",
        "experimental_protocol_design",
        "report_generation",
        "clinical_data_analysis",
        "variant_analysis",
        "biomarker_discovery",
    }

    def __init__(self) -> None:
        self._config = get_config()
        self._api_key: str = self._config.deepseek_api_key
        self._api_url: str = "https://api.deepseek.com/v1/chat/completions"
        self._model: str = "deepseek-v4-flash"
        self._max_retries: int = self._config.max_retries
        self._timeout: int = self._config.request_timeout

        # 降级默认流水线，覆盖从检索到报告的完整流程
        self._default_pipeline: list[str] = [
            "literature_search",
            "gene_expression_analysis",
            "target_prioritization",
            "experimental_protocol_design",
            "report_generation",
        ]

    # ── 公开方法 ──────────────────────────────

    async def plan(self, query: str, intent: dict[str, Any]) -> list[str]:
        """根据意图生成有序的任务执行列表。

        使用 DeepSeek API 规划任务，包含最多 3 次重试机制。
        所有异常情况下均返回安全的默认流水线。

        Args:
            query: 原始研究问题字符串
            intent: 意图分类结果（IntentClassifier.classify 的输出）

        Returns:
            有序的任务名称列表（字符串），按执行依赖关系排列。
            例如: ["literature_search", "gene_expression_analysis",
                   "target_prioritization"]

        Examples:
            >>> planner = TaskPlanner()
            >>> intent = {"disease_type": "breast cancer",
            ...           "research_purpose": "drug_target_identification"}
            >>> tasks = await planner.plan("乳腺癌新靶点发现", intent)
            >>> "target_prioritization" in tasks
            True
        """
        # 无 API Key 时跳过 API 调用
        if not self._api_key:
            logger.warning("[任务规划] API 密钥未配置，返回默认流水线")
            return list(self._default_pipeline)

        user_content = (
            f"Research question: {query}\n"
            f"Intent: {json.dumps(intent, ensure_ascii=False)}"
        )

        messages = [
            {"role": "system", "content": TASK_PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(f"[任务规划] 尝试 {attempt}/{self._max_retries}")
                raw_response = await self._call_api(messages)
                tasks = self._parse_response(raw_response)
                validated = self._deduplicate_and_validate(tasks)
                logger.success(f"[任务规划] 成功: {validated}")
                return validated

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[任务规划] 超时 (尝试 {attempt}/{self._max_retries})")
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code
                logger.warning(f"[任务规划] HTTP {status} (尝试 {attempt}/{self._max_retries})")
                if attempt < self._max_retries and status < 500:
                    await asyncio.sleep(1)
                elif attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                last_error = e
                logger.warning(f"[任务规划] 响应解析失败: {e} (尝试 {attempt}/{self._max_retries})")
                if attempt < self._max_retries:
                    await asyncio.sleep(1)

            except Exception as e:
                last_error = e
                logger.error(f"[任务规划] 未预期异常: {e}")
                break

        logger.error(f"[任务规划] 全部 {self._max_retries} 次重试失败, "
                     f"最后错误: {last_error}")
        return list(self._default_pipeline)

    # ── 内部方法 ──────────────────────────────

    async def _call_api(self, messages: list[dict]) -> str:
        """调用 DeepSeek Chat Completions API。

        Args:
            messages: OpenAI 格式的 messages 列表

        Returns:
            API 返回的文本内容

        Raises:
            httpx.TimeoutException: 请求超时
            httpx.HTTPStatusError: HTTP 状态码错误
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._api_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _parse_response(self, content: str) -> list[str]:
        """解析 LLM 返回的 JSON 数组。

        支持清理 markdown 代码块标记。

        Args:
            content: LLM 返回的原始文本

        Returns:
            任务名称列表

        Raises:
            json.JSONDecodeError: JSON 解析失败
        """
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        if isinstance(parsed, list):
            return [str(task).strip() for task in parsed]
        raise ValueError(
            f"期望 JSON 数组，但得到 {type(parsed).__name__}: {parsed}"
        )

    def _deduplicate_and_validate(self, tasks: list[str]) -> list[str]:
        """去重并过滤无效任务名。

        Args:
            tasks: 原始任务列表

        Returns:
            去重后的有效任务列表；若为空则返回默认流水线
        """
        seen: set[str] = set()
        result: list[str] = []

        for task in tasks:
            task_lower = task.lower().replace(" ", "_")
            if task_lower in self._AVAILABLE_TASKS and task_lower not in seen:
                seen.add(task_lower)
                result.append(task_lower)

        if not result:
            logger.warning("[任务规划] 所有任务均无效，使用默认流水线")
            return list(self._default_pipeline)

        # 确保始终以 report_generation 结尾
        if "report_generation" in self._AVAILABLE_TASKS and result[-1] != "report_generation":
            result.append("report_generation")

        return result
