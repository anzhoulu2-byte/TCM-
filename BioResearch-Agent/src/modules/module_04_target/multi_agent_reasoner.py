"""
多智能体推理引擎 (MultiAgentReasoner)。

实现四个专用智能体协作推理：
- LiteratureAgent: 综合文献证据
- OmicsAgent: 整合多组学数据
- NetworkAgent: 分析蛋白互作网络
- CriticAgent: 批判性评估

每个智能体使用 LLM 进行深度推理，输出带完整证据链的评估结果。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from loguru import logger

from src.config import get_config


# ── 系统提示词模板 ────────────────────────────

LITERATURE_AGENT_PROMPT = """You are a Literature Agent specializing in biomedical literature analysis. Given a candidate target gene and its literature evidence, evaluate:

1. **Consistency**: How consistent are the literature findings across different studies?
2. **Mechanistic Insight**: Does the literature provide mechanistic understanding of the gene's role in the disease?
3. **Clinical Relevance**: Are there clinical studies or trials involving this gene?
4. **Knowledge Gap**: What are the key unknowns or controversies?

Respond in JSON format:
{
    "confidence": <float 0-1>,
    "strengths": [<list of positive findings>],
    "weaknesses": [<list of concerns or gaps>],
    "key_papers": [<up to 3 key PMIDs or references>],
    "reasoning": "<detailed analysis>"
}"""


OMICS_AGENT_PROMPT = """You are an Omics Agent specializing in multi-omics data integration. Given expression, functional, and other omics evidence for a target gene:

1. **Expression Pattern**: Is the gene consistently dysregulated across datasets?
2. **Functional Enrichment**: Is the gene involved in relevant biological pathways?
3. **Genetic Evidence**: Are there disease-associated variants or mutations?
4. **Cross-Platform Validation**: Is the finding replicated across different omics platforms?

Respond in JSON format:
{
    "confidence": <float 0-1>,
    "expression_evidence": "<summary>",
    "pathway_evidence": "<summary>",
    "genetic_evidence": "<summary>",
    "strengths": [<list>],
    "weaknesses": [<list>],
    "reasoning": "<detailed analysis>"
}"""


NETWORK_AGENT_PROMPT = """You are a Network Agent specializing in protein-protein interaction networks and pathway analysis. Given a target gene:

1. **Network Centrality**: Is the gene a hub in relevant biological networks?
2. **Pathway Crosstalk**: Does the gene bridge multiple relevant pathways?
3. **Neighborhood Analysis**: Are the gene's interaction partners also disease-associated?
4. **Functional Modules**: Does the gene belong to functionally coherent modules?

Respond in JSON format:
{
    "confidence": <float 0-1>,
    "network_role": "<hub/bottleneck/module_member/peripheral>",
    "interaction_partners_count": <int>,
    "key_pathways": [<list>],
    "strengths": [<list>],
    "weaknesses": [<list>],
    "reasoning": "<detailed analysis>"
}"""


CRITIC_AGENT_PROMPT = """You are a Critic Agent serving as the final reviewer. Given the assessments from Literature, Omics, and Network agents for a target gene:

1. **Consistency Check**: Do the findings from different agents converge or conflict?
2. **Confidence Assessment**: How reliable is the overall evidence?
3. **Risk Factors**: What are the main risks or limitations?
4. **Priority Score**: What final priority score would you assign (0-1)?

Respond in JSON format:
{
    "confidence": <float 0-1>,
    "priority_score": <float 0-1>,
    "final_verdict": "<upregulate/downgrade/inconclusive>",
    "risks": [<list of risks>],
    "recommendations": [<list of next steps>],
    "reasoning": "<detailed synthesis>"
}"""


# ── 智能体基类 ────────────────────────────────

class _BaseAgent:
    """智能体基类。"""

    def __init__(self, name: str, system_prompt: str) -> None:
        self.name: str = name
        self._system_prompt: str = system_prompt
        self._config = get_config()
        self._api_key: str = self._config.deepseek_api_key

    async def analyze(self, gene: str, context: dict[str, Any]) -> dict[str, Any]:
        """执行推理分析。

        Args:
            gene: 靶点基因名
            context: 该基因对应的证据上下文

        Returns:
            推理结果字典
        """
        if not self._api_key:
            logger.warning(f"[{self.name}] API 密钥未配置，使用规则推理")
            return self._rule_based_fallback(gene, context)

        try:
            messages = [
                {"role": "system", "content": self._system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Gene: {gene}\n"
                        f"Context: {json.dumps(context, ensure_ascii=False, default=str)[:3000]}"
                    ),
                },
            ]
            result_text = await self._call_llm(messages)
            parsed = self._parse_json(result_text)
            logger.debug(f"[{self.name}] {gene} 推理完成, confidence={parsed.get('confidence')}")
            return parsed
        except Exception as e:
            logger.error(f"[{self.name}] {gene} 推理失败: {e}")
            return self._rule_based_fallback(gene, context)

    async def _call_llm(self, messages: list[dict]) -> str:
        """调用 LLM。"""
        import httpx
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-v4-flash",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                json=payload, headers=headers,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _parse_json(self, text: str) -> dict[str, Any]:
        """解析 JSON 响应。"""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())

    def _rule_based_fallback(self, gene: str, context: dict) -> dict[str, Any]:
        """LLM 不可用时的规则推理降级。"""
        return {"confidence": 0.5, "reasoning": "Rule-based fallback", "strengths": [], "weaknesses": []}


# ── 具体智能体 ────────────────────────────────

class LiteratureAgent(_BaseAgent):
    """文献证据综合智能体。"""

    def __init__(self) -> None:
        super().__init__("LiteratureAgent", LITERATURE_AGENT_PROMPT)

    def _rule_based_fallback(self, gene: str, context: dict) -> dict[str, Any]:
        lit = context.get("literature", {})
        pmid_count = lit.get("pmid_count", 0) or 0
        return {
            "confidence": min(pmid_count / 500, 1.0),
            "strengths": [f"{pmid_count} related publications"] if pmid_count > 10 else [],
            "weaknesses": ["Limited literature" if pmid_count < 10 else "No major weaknesses identified"],
            "key_papers": [],
            "reasoning": f"Rule-based: {pmid_count} publications found.",
        }


class OmicsAgent(_BaseAgent):
    """多组学数据整合智能体。"""

    def __init__(self) -> None:
        super().__init__("OmicsAgent", OMICS_AGENT_PROMPT)

    def _rule_based_fallback(self, gene: str, context: dict) -> dict[str, Any]:
        expr = context.get("expression", {})
        log2fc = abs(float(expr.get("log2fc", 0) or 0))
        return {
            "confidence": min(log2fc / 3.0, 1.0),
            "expression_evidence": f"log2FC={expr.get('log2fc', 'N/A')}",
            "pathway_evidence": "N/A",
            "genetic_evidence": "N/A",
            "strengths": [f"Differential expression: |log2FC|={log2fc:.2f}"] if log2fc > 1 else [],
            "weaknesses": ["Weak expression signal"] if log2fc < 1 else [],
            "reasoning": "Rule-based omics assessment.",
        }


class NetworkAgent(_BaseAgent):
    """蛋白互作网络分析智能体。"""

    def __init__(self) -> None:
        super().__init__("NetworkAgent", NETWORK_AGENT_PROMPT)

    def _rule_based_fallback(self, gene: str, context: dict) -> dict[str, Any]:
        fn = context.get("functional", {})
        pathways = fn.get("pathways", []) or []
        return {
            "confidence": min(len(pathways) / 5.0, 1.0),
            "network_role": "module_member",
            "interaction_partners_count": 0,
            "key_pathways": pathways[:3],
            "strengths": [f"Enriched in {len(pathways)} pathways"] if pathways else [],
            "weaknesses": ["No pathway information"] if not pathways else [],
            "reasoning": "Rule-based network assessment.",
        }


class CriticAgent(_BaseAgent):
    """批判性评估智能体（最终裁决）。"""

    def __init__(self) -> None:
        super().__init__("CriticAgent", CRITIC_AGENT_PROMPT)

    def _rule_based_fallback(self, gene: str, context: dict) -> dict[str, Any]:
        scores = context.get("_agent_scores", [0.5, 0.5, 0.5])
        avg_conf = sum(scores) / len(scores)
        return {
            "confidence": avg_conf,
            "priority_score": avg_conf * 0.8,
            "final_verdict": "inconclusive",
            "risks": ["Rule-based assessment - no LLM available"],
            "recommendations": ["Manual review recommended"],
            "reasoning": f"Rule-based critic: average agent confidence={avg_conf:.2f}",
        }


# ── 多智能体推理引擎 ──────────────────────────

class MultiAgentReasoner:
    """多智能体推理引擎。

    协调四个专用智能体对候选靶点进行协作推理，
    输出带完整证据链的评估结果。

    Attributes:
        literature_agent: 文献证据智能体
        omics_agent: 多组学数据智能体
        network_agent: 网络分析智能体
        critic_agent: 批判性评估智能体
        output_dir: 结果保存目录
    """

    def __init__(self, output_dir: str | None = None) -> None:
        self.literature_agent = LiteratureAgent()
        self.omics_agent = OmicsAgent()
        self.network_agent = NetworkAgent()
        self.critic_agent = CriticAgent()

        config = get_config()
        self._output_dir = Path(output_dir or config.output_dir) / "targets" / "reasoning"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("MultiAgentReasoner 初始化完成 (4 agents)")

    async def reason(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """对候选靶点列表执行多智能体推理。

        Args:
            candidates: 候选靶点列表，每个元素至少包含 "gene" 和 "evidence_data"

        Returns:
            增强后的候选靶点列表，每个元素增加 "agent_assessments" 和 "final_score"

        Examples:
            >>> reasoner = MultiAgentReasoner()
            >>> candidates = [{"gene": "TP53", "evidence_data": {"literature": {"pmid_count": 500}}}]
            >>> result = await reasoner.reason(candidates)
            >>> "agent_assessments" in result[0]
            True
        """
        logger.info(f"多智能体推理开始: {len(candidates)} 个候选靶点")

        enriched: list[dict[str, Any]] = []

        for i, candidate in enumerate(candidates):
            gene = candidate.get("gene", "unknown")
            evidence = candidate.get("evidence_data", {})

            logger.info(f"[{i+1}/{len(candidates)}] 推理靶点: {gene}")

            # 并行运行前三个智能体
            lit_task = self.literature_agent.analyze(gene, evidence)
            omics_task = self.omics_agent.analyze(gene, evidence)
            net_task = self.network_agent.analyze(gene, evidence)

            lit_result, omics_result, net_result = await asyncio.gather(
                lit_task, omics_task, net_task,
            )

            # Critic 需要前三个的结果
            critic_context = {**evidence, "_agent_scores": [
                lit_result.get("confidence", 0.5),
                omics_result.get("confidence", 0.5),
                net_result.get("confidence", 0.5),
            ]}
            critic_result = await self.critic_agent.analyze(gene, critic_context)

            # 聚合结果
            agent_assessments = {
                "literature_agent": lit_result,
                "omics_agent": omics_result,
                "network_agent": net_result,
                "critic_agent": critic_result,
            }

            final_score = critic_result.get("priority_score", 0.5)

            enriched_candidate = {
                **candidate,
                "agent_assessments": agent_assessments,
                "final_reasoning_score": round(final_score, 4),
            }
            enriched.append(enriched_candidate)

            # 保存单靶点推理结果
            self._save_reasoning(gene, agent_assessments, final_score)

        # 按 final_score 排序
        enriched.sort(key=lambda x: x.get("final_reasoning_score", 0), reverse=True)

        logger.success(
            f"多智能体推理完成: {len(enriched)} 靶点, "
            f"top={enriched[0]['gene'] if enriched else 'N/A'}"
        )
        return enriched

    def _save_reasoning(
        self,
        gene: str,
        assessments: dict,
        final_score: float,
    ) -> None:
        """保存推理结果。"""
        import json as j
        data = {
            "gene": gene,
            "final_score": final_score,
            "assessments": {
                agent: {
                    k: v for k, v in result.items()
                    if k != "reasoning" or len(str(v)) < 500
                }
                for agent, result in assessments.items()
            },
        }
        path = self._output_dir / f"reasoning_{gene}.json"
        with open(path, "w", encoding="utf-8") as f:
            j.dump(data, f, ensure_ascii=False, indent=2)
