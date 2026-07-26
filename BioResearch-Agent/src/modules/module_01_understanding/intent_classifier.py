"""
研究意图分类器 (Intent Classifier)。

调用 DeepSeek API (deepseek-v4-flash) 分析用户的自然语言研究问题，
提取结构化的研究意图信息：疾病类型、研究目的、所需数据类型。

提供自动重试机制（最多 3 次）和降级默认值。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from loguru import logger

from src.config import get_config

# ── 系统提示词 ──────────────────────────────────

INTENT_SYSTEM_PROMPT = """You are a biomedical research intent classifier. Your task is to analyze the user's natural language question and extract structured information about their research intent.

Analyze the question and return a JSON object with the following fields:
1. "disease_type": The specific disease or condition mentioned (e.g., "breast cancer", "Alzheimer's disease", "COVID-19"). If no specific disease is mentioned, use "general".
2. "research_purpose": The primary research goal. Choose one from: "mechanism_study", "biomarker_discovery", "drug_target_identification", "diagnostic_development", "therapeutic_evaluation", "literature_review".
3. "data_type_needed": The types of data required. Choose from: "gene_expression", "clinical_data", "genomic_variants", "proteomics", "literature", "pathway_data". Return as a JSON array.

Respond ONLY with the JSON object, no additional text or markdown formatting."""


class IntentClassifier:
    """研究意图分类器。

    将用户提出的自然语言研究问题解析为结构化的意图信息，
    供下游模块（检索、分析、靶点发现等）使用。

    Attributes:
        api_key: DeepSeek API 密钥（从配置自动读取）
        model: 使用的模型名称
        max_retries: 最大重试次数
        timeout: HTTP 请求超时时间（秒）
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._api_key: str = self._config.deepseek_api_key
        self._api_url: str = "https://api.deepseek.com/v1/chat/completions"
        self._model: str = "deepseek-v4-flash"
        self._max_retries: int = self._config.max_retries
        self._timeout: int = self._config.request_timeout

    # ── 公开方法 ──────────────────────────────

    async def classify(self, question: str) -> dict[str, Any]:
        """分析自然语言研究问题，返回结构化意图。

        使用 DeepSeek API 进行分析，包含最多 3 次重试机制。
        所有异常情况下均返回安全的默认值，保证调用方不崩溃。

        Args:
            question: 用户的自然语言研究问题
                     （例如 "乳腺癌中 TP53 突变的机制研究"）

        Returns:
            dict 包含以下键：
            - disease_type (str): 疾病名称
            - research_purpose (str): 研究目的
            - data_type_needed (list[str]): 所需数据类型列表

        Examples:
            >>> classifier = IntentClassifier()
            >>> intent = await classifier.classify("探索阿尔茨海默病的生物标志物")
            >>> intent["disease_type"]
            "alzheimer's disease"
            >>> intent["research_purpose"]
            "biomarker_discovery"
        """
        # 空值保护
        if not question or not question.strip():
            logger.warning("接收到空问题，返回默认意图")
            return self._default_intent()

        # 无 API Key 时跳过 API 调用
        if not self._api_key:
            logger.warning("DeepSeek API 密钥未配置，返回默认意图")
            return self._default_intent()

        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": question.strip()},
        ]

        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(f"[意图分类] 尝试 {attempt}/{self._max_retries}")
                raw_response = await self._call_api(messages)
                parsed = self._parse_response(raw_response)
                logger.success(f"[意图分类] 成功: disease={parsed['disease_type']}, "
                               f"purpose={parsed['research_purpose']}")
                return parsed

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[意图分类] 超时 (尝试 {attempt}/{self._max_retries})")
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code
                logger.warning(f"[意图分类] HTTP {status} (尝试 {attempt}/{self._max_retries})")
                if attempt < self._max_retries and status < 500:
                    await asyncio.sleep(1)
                elif attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                last_error = e
                logger.warning(f"[意图分类] 响应解析失败: {e} (尝试 {attempt}/{self._max_retries})")
                if attempt < self._max_retries:
                    await asyncio.sleep(1)

            except Exception as e:
                last_error = e
                logger.error(f"[意图分类] 未预期异常: {e}")
                break

        logger.error(f"[意图分类] 全部 {self._max_retries} 次重试失败, "
                     f"最后错误: {last_error}")
        return self._default_intent()

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

    def _parse_response(self, content: str) -> dict[str, Any]:
        """解析 LLM 返回的内容为结构化意图。

        支持清理 markdown 代码块标记 (```json ... ```)。

        Args:
            content: LLM 返回的原始文本

        Returns:
            标准化的意图字典

        Raises:
            json.JSONDecodeError: JSON 解析失败
            KeyError: 缺少必要字段
        """
        # 清理 markdown 代码块标记
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # 标准化输出
        disease_type = str(parsed.get("disease_type", "general")).strip().lower()
        research_purpose = str(
            parsed.get("research_purpose", "literature_review")
        ).strip().lower()
        raw_data_types = parsed.get("data_type_needed", ["literature"])

        # 确保 data_type_needed 是 list[str]
        if isinstance(raw_data_types, str):
            data_type_needed = [raw_data_types]
        elif isinstance(raw_data_types, list):
            data_type_needed = [str(t).strip().lower() for t in raw_data_types]
        else:
            data_type_needed = ["literature"]

        return {
            "disease_type": disease_type,
            "research_purpose": research_purpose,
            "data_type_needed": data_type_needed,
        }

    def _default_intent(self) -> dict[str, Any]:
        """返回安全的默认意图（降级方案）。

        在 API 调用失败或无 API Key 时使用，
        保证调用方始终能获得有效结果。

        Returns:
            含默认值的意图字典
        """
        return {
            "disease_type": "general",
            "research_purpose": "literature_review",
            "data_type_needed": ["literature"],
        }
