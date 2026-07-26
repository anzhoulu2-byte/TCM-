"""
学术文献分析对话代理 (LiteratureAnalyzer)。

实现检索-阅读-分析-对话-迭代 的完整学术AI研究助手流程：
1. 搜索相关文献
2. 获取全文摘要
3. LLM 深度分析每篇文献
4. 跨文献整合观点
5. 与用户对话交互
6. 根据反馈重新搜索和分析
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from loguru import logger

from src.config import get_config
from src.modules.module_02_retrieval.pubmed_client import PubMedClient


# ── LLM 提示词模板 ────────────────────────────

ANALYZE_PAPER_PROMPT = """You are an expert biomedical researcher analyzing a scientific paper. Read the title and abstract carefully, then extract structured insights.

Paper Title: {title}
Abstract: {abstract}

Respond in JSON format with these fields:
{{
    "research_purpose": "What was the main goal of this study?",
    "methods_summary": "Key experimental methods used (1-2 sentences)",
    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
    "strengths": ["Strength 1", "Strength 2"],
    "limitations": ["Limitation 1", "Limitation 2"],
    "relevance_to_query": "How relevant is this to the user's question? (0-1 score)",
    "key_genes_or_proteins": ["gene1", "gene2"],
    "significance": "Why this matters (1 sentence)"
}}"""


SYNTHESIS_PROMPT = """You are an expert biomedical research synthesizer. You've analyzed multiple papers related to a research question. Synthesize the findings into a coherent overview.

Research Question: {question}

Analyzed Papers (with structured insights):
{paper_insights}

Provide a comprehensive synthesis in JSON format:
{{
    "overall_summary": "Integrated summary of what the literature says (2-3 paragraphs)",
    "key_consensus": ["Point of consensus 1", "Point of consensus 2", "Point of consensus 3"],
    "key_controversies": ["Debated point 1", "Debated point 2"],
    "knowledge_gaps": ["Gap 1", "Gap 2"],
    "emerging_themes": ["Theme 1", "Theme 2"],
    "suggested_next_questions": ["Question to explore 1", "Question to explore 2"],
    "confidence_level": "high/medium/low based on evidence strength"
}}"""


RE_SEARCH_PROMPT = """Based on our discussion so far, the user has provided the following feedback or follow-up question:

User: {user_message}

Previous research focus: {previous_focus}
Previous findings summary: {previous_summary}

Generate a refined PubMed search query to find more specific or relevant papers.
Respond with ONLY a JSON object:
{{
    "refined_query": "PubMed boolean search query",
    "reasoning": "Why this new search direction?",
    "focus_shift": "How the search focus is adjusted"
}}"""


class LiteratureAnalyzer:
    """学术文献分析对话代理。

    支持完整的检索-分析-对话-迭代循环。
    用户提出问题 → 搜索文献 → 阅读分析 → 综合观点 → 与用户讨论 → 根据反馈再搜索。

    Attributes:
        pubmed: PubMedClient 实例
        conversation_history: 对话历史记录
        analyzed_papers: 已分析的论文库
    """

    def __init__(self) -> None:
        self.pubmed = PubMedClient()
        self._config = get_config()
        self._api_key: str = self._config.deepseek_api_key
        self._api_url: str = "https://api.deepseek.com/v1/chat/completions"
        self._model: str = "deepseek-v4-flash"

        # 会话状态
        self.conversation_history: list[dict[str, str]] = []
        self.analyzed_papers: list[dict[str, Any]] = []
        self.current_synthesis: dict[str, Any] | None = None
        self.last_search_query: str = ""

    # ── 公开方法 ──────────────────────────────

    async def research_iteration(
        self,
        user_message: str,
        max_papers: int = 10,
    ) -> dict[str, Any]:
        """执行一次完整的研究迭代：搜索 → 阅读 → 分析 → 综合。

        第一次调用时执行完整流程；后续调用根据上下文精简搜索范围。

        Args:
            user_message: 用户的研究问题或反馈
            max_papers: 每次迭代分析的最大论文数

        Returns:
            包含分析结果和综合观点的字典
        """
        # 记录用户消息
        self.conversation_history.append({"role": "user", "content": user_message})

        # 判断是初次提问还是追问
        is_first_round = not self.analyzed_papers

        if is_first_round:
            # ── 初次：搜索 + 分析 + 综合 ──
            query = user_message
            self.last_search_query = query
            papers = await self._search_and_fetch(query, max_papers)
            if not papers:
                return self._empty_result("未找到相关文献")

            analyzed = await self._analyze_papers(papers, query)
            self.analyzed_papers = analyzed
            synthesis = await self._synthesize(analyzed, query)
            self.current_synthesis = synthesis
        else:
            # ── 追问：根据反馈重新搜索 + 补充分析 ──
            refined = await self._generate_refined_query(user_message)
            new_query = refined.get("refined_query", user_message)
            self.last_search_query = new_query

            papers = await self._search_and_fetch(new_query, max_papers)
            if papers:
                analyzed = await self._analyze_papers(papers, new_query)
                # 合并新旧论文（去重）
                existing_pmids = {p.get("pmid") for p in self.analyzed_papers if p.get("pmid")}
                new_papers = [p for p in analyzed if p.get("pmid") not in existing_pmids]
                self.analyzed_papers.extend(new_papers)

                # 重新综合（包含新旧论文）
                synthesis = await self._synthesize(self.analyzed_papers, user_message)
                self.current_synthesis = synthesis
            else:
                synthesis = self.current_synthesis or {}

        # 生成回答
        answer = self._format_answer(self.current_synthesis, self.analyzed_papers)

        result = {
            "answer": answer,
            "synthesis": self.current_synthesis,
            "papers_analyzed": len(self.analyzed_papers),
            "papers": self.analyzed_papers,
            "search_query": self.last_search_query,
        }

        self.conversation_history.append({"role": "assistant", "content": answer})
        return result

    def get_conversation(self) -> list[dict[str, str]]:
        """返回对话历史。"""
        return self.conversation_history

    def reset_conversation(self) -> None:
        """重置对话和已分析论文。"""
        self.conversation_history.clear()
        self.analyzed_papers.clear()
        self.current_synthesis = None
        self.last_search_query = ""

    # ── 内部方法 ──────────────────────────────

    async def _search_and_fetch(
        self, query: str, max_papers: int
    ) -> list[dict[str, Any]]:
        """搜索 PubMed 并获取带摘要的文献。"""
        logger.info(f"[文献分析] 搜索: {query[:60]}...")

        # 先搜索获取元数据
        articles = await self.pubmed.search(query, max_results=max_papers, sort="relevance")
        if not articles:
            logger.warning("[文献分析] 未搜索到文献")
            return []

        pmids = [a.get("pmid", "") for a in articles if a.get("pmid")]
        logger.info(f"[文献分析] 获取 {len(pmids)} 篇文献的摘要...")

        # 通过 efetch 获取完整摘要
        abstracts = await self.pubmed.fetch_abstracts(pmids)
        logger.info(f"[文献分析] 成功获取 {len(abstracts)} 篇摘要")

        # 按相关度排序（与搜索顺序一致）
        pmid_order = {p: i for i, p in enumerate(pmids)}
        abstracts.sort(key=lambda a: pmid_order.get(a.get("pmid", ""), 999))
        return abstracts

    async def _analyze_papers(
        self, papers: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """用 LLM 逐篇分析论文摘要。"""
        logger.info(f"[文献分析] 分析 {len(papers)} 篇文献...")

        analyzed = []
        tasks = []
        for paper in papers:
            tasks.append(self._analyze_single_paper(paper, query))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for paper, result in zip(papers, results):
            if isinstance(result, Exception):
                logger.warning(f"[文献分析] 分析失败 {paper.get('pmid', '')}: {result}")
                paper["analysis"] = self._default_paper_analysis()
                analyzed.append(paper)
            else:
                paper["analysis"] = result
                analyzed.append(paper)

        logger.success(f"[文献分析] 完成 {len(analyzed)} 篇分析")
        return analyzed

    async def _analyze_single_paper(
        self, paper: dict[str, Any], query: str
    ) -> dict[str, Any]:
        """分析单篇论文。"""
        if not self._api_key:
            return self._default_paper_analysis()

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        if not abstract:
            return self._default_paper_analysis()

        prompt = ANALYZE_PAPER_PROMPT.format(title=title, abstract=abstract[:2000])
        messages = [
            {"role": "system", "content": "You are an expert biomedical research analyst. Respond in JSON only."},
            {"role": "user", "content": prompt},
        ]
        try:
            resp = await self._call_llm(messages)
            return self._parse_json(resp)
        except Exception as e:
            logger.warning(f"[文献分析] LLM 分析异常: {e}")
            return self._default_paper_analysis()

    async def _synthesize(
        self, papers: list[dict[str, Any]], query: str
    ) -> dict[str, Any]:
        """跨文献综合观点。"""
        if not self._api_key:
            return self._default_synthesis()

        insights = []
        for p in papers[:15]:
            a = p.get("analysis", {})
            if isinstance(a, dict) and a.get("key_findings"):
                insights.append({
                    "pmid": p.get("pmid", ""),
                    "title": p.get("title", "")[:80],
                    "findings": a.get("key_findings", []),
                    "purpose": a.get("research_purpose", ""),
                })

        if not insights:
            return self._default_synthesis()

        prompt = SYNTHESIS_PROMPT.format(
            question=query,
            paper_insights=json.dumps(insights, ensure_ascii=False, indent=2)[:4000],
        )
        messages = [
            {"role": "system", "content": "You are an expert biomedical research synthesizer."},
            {"role": "user", "content": prompt},
        ]
        try:
            resp = await self._call_llm(messages)
            return self._parse_json(resp)
        except Exception as e:
            logger.warning(f"[文献分析] 综合失败: {e}")
            return self._default_synthesis()

    async def _generate_refined_query(
        self, user_message: str
    ) -> dict[str, Any]:
        """根据用户反馈生成更精确的搜索查询。"""
        if not self._api_key:
            return {"refined_query": user_message, "reasoning": ""}

        prev_summary = ""
        if self.current_synthesis:
            prev_summary = self.current_synthesis.get("overall_summary", "")[:500]

        prompt = RE_SEARCH_PROMPT.format(
            user_message=user_message,
            previous_focus=self.last_search_query,
            previous_summary=prev_summary,
        )
        messages = [
            {"role": "system", "content": "You are a research query optimizer."},
            {"role": "user", "content": prompt},
        ]
        try:
            resp = await self._call_llm(messages)
            return self._parse_json(resp)
        except Exception:
            return {"refined_query": f"{self.last_search_query} {user_message}", "reasoning": ""}

    async def _call_llm(self, messages: list[dict]) -> str:
        """调用 DeepSeek API。"""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
            resp = await client.post(self._api_url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _parse_json(self, text: str) -> dict[str, Any]:
        """解析 LLM JSON 响应。"""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())

    def _format_answer(
        self, synthesis: dict | None, papers: list[dict]
    ) -> str:
        """将综合结果格式化为可读的回答。"""
        if not synthesis:
            return "目前未找到足够的相关文献来形成综合观点。请尝试换一个搜索方向。"

        parts = []
        parts.append("## 📚 文献综合分析结果\n")

        overall = synthesis.get("overall_summary", "")
        if overall:
            parts.append(overall + "\n")

        consensus = synthesis.get("key_consensus", [])
        if consensus:
            parts.append("### ✅ 主要共识\n")
            parts.extend(f"- {c}" for c in consensus)
            parts.append("")

        controversies = synthesis.get("key_controversies", [])
        if controversies:
            parts.append("### ⚠️ 存在争议\n")
            parts.extend(f"- {c}" for c in controversies)
            parts.append("")

        gaps = synthesis.get("knowledge_gaps", [])
        if gaps:
            parts.append("### ❓ 知识空白\n")
            parts.extend(f"- {g}" for g in gaps)
            parts.append("")

        themes = synthesis.get("emerging_themes", [])
        if themes:
            parts.append("### 🔍 新兴方向\n")
            parts.extend(f"- {t}" for t in themes)
            parts.append("")

        next_q = synthesis.get("suggested_next_questions", [])
        if next_q:
            parts.append("### 💡 下一步可以探索\n")
            parts.extend(f"- {q}" for q in next_q)
            parts.append("")

        # 参考文献
        if papers:
            parts.append("### 📖 参考文献\n")
            shown = set()
            for p in papers[:8]:
                pid = p.get("pmid", "")
                if pid in shown:
                    continue
                shown.add(pid)
                authors = p.get("authors", [])
                author_str = authors[0].split()[0] if authors else "?"
                year = p.get("year", "?")
                title = p.get("title", "")[:80]
                parts.append(f"- {author_str} et al. ({year}). {title}... PMID: {pid}")
                # 显示分析摘要
                analysis = p.get("analysis", {})
                if isinstance(analysis, dict) and analysis.get("key_findings"):
                    for f in analysis["key_findings"][:2]:
                        parts.append(f"  > {f}")
            parts.append("")

        parts.append("---\n*有什么想深入了解的方向吗？我可以进一步搜索和分析。*")
        return "\n".join(parts)

    def _empty_result(self, reason: str) -> dict[str, Any]:
        return {
            "answer": f"⚠️ {reason}。请尝试其他关键词或调整研究问题。",
            "synthesis": None,
            "papers_analyzed": 0,
            "papers": [],
            "search_query": self.last_search_query,
        }

    @staticmethod
    def _default_paper_analysis() -> dict[str, Any]:
        return {
            "research_purpose": "",
            "methods_summary": "",
            "key_findings": [],
            "strengths": [],
            "limitations": [],
            "relevance_to_query": 0.5,
            "key_genes_or_proteins": [],
            "significance": "",
        }

    @staticmethod
    def _default_synthesis() -> dict[str, Any]:
        return {
            "overall_summary": "综合分析完成，但LLM分析不可用，仅提供文献列表。",
            "key_consensus": [],
            "key_controversies": [],
            "knowledge_gaps": ["需要配置LLM API密钥以获取深度分析"],
            "emerging_themes": [],
            "suggested_next_questions": ["请配置API密钥后重试"],
            "confidence_level": "low",
        }
