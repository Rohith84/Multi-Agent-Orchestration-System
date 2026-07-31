"""
Research Agent.
Searches context from Knowledge Base, retrieves relevant documents,
and summarizes them with downstream integration.
May access GitHub and HTTP tools via MCP.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.retriever.search import KnowledgeRetriever

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class ResearchAgent:
    """
    Research Agent queries the vector database for relevant documents,
    retrieves context, and uses the LLM to write a research summary.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_research
        self.retriever = KnowledgeRetriever()

    async def execute(
        self,
        user_request: str,
        execution_plan: str,
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        logger.info("Executing Research Agent with model=%s", self.model)

        retrieved_chunks = []
        retrieval_error = None
        retrieval_time = 0.0

        # 1. Similarity Search
        try:
            start_ret = time.time()
            retrieved_chunks = await self.retriever.retrieve(user_request, top_k=5)
            retrieval_time = time.time() - start_ret
        except Exception as e:
            logger.error("Retrieval failed during Research Agent execution: %s", e)
            retrieval_error = str(e)

        # 2. MCP Tool: Optionally query GitHub for context
        github_context = ""
        if tool_runner:
            try:
                result = await tool_runner.run_tool(
                    "github.list_commits",
                    {"owner": "Rohith84", "repo": "Multi-Agent-Orchestration-System", "branch": "main"},
                )
                if result:
                    commits = result.get("commits", [])[:5]
                    if commits:
                        commit_list = "\n".join(
                            f"  - {c['sha']} {c['message']} ({c['author']})"
                            for c in commits
                        )
                        github_context = f"\n\nRecent GitHub Commits:\n{commit_list}"
            except Exception as e:
                logger.debug("Research GitHub MCP tool failed (non-critical): %s", e)

        # 3. Build Context String for LLM Prompt
        context_str = ""
        citation_sources = []
        if retrieved_chunks:
            context_blocks = []
            for idx, chunk in enumerate(retrieved_chunks):
                citation = f"Source {idx + 1}: {chunk['filename']} (similarity: {chunk['score']})"
                citation_sources.append(citation)
                context_blocks.append(
                    f"--- {citation} ---\n{chunk['content']}"
                )
            context_str = "\n\n".join(context_blocks)
        else:
            context_str = "No relevant context found in Knowledge Base."

        # 4. Generate LLM Prompt
        system_prompt = (
            "You are the Research Agent. Your job is to research best practices, dependencies, "
            "and architectural specifications required for the proposed plan using the provided Knowledge Base context.\n"
            "Provide solid implementation guidelines, API signatures, or security considerations that the Coder Agent must follow.\n"
            "Ensure you cite relevant files or documents where appropriate.\n\n"
            "Outline:\n"
            "1. Architectural Principles / Best Practices\n"
            "2. Critical Dependencies & API Reference Guidelines\n"
            "3. Security & Context Checklists"
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Proposed Execution Plan:\n{execution_plan}\n\n"
            f"Knowledge Base Context:\n{context_str}\n\n"
        )
        if github_context:
            prompt += f"{github_context}\n\n"
        prompt += (
            "Please conduct research and provide notes for this plan. "
            "Explicitly reference and cite files from the context in your response."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        # Call Ollama for research summary
        summary = await self.client.chat(messages, model=self.model)

        # 5. Format detailed structured output for the timeline/SSE and Coder Agent
        output_parts = []
        output_parts.append("==================================================")
        output_parts.append("RETRIEVED DOCUMENTS & KNOWLEDGE")
        output_parts.append("==================================================")
        
        if retrieval_error:
            output_parts.append(f"ERROR: Retrieval failed: {retrieval_error}")
        elif not retrieved_chunks:
            output_parts.append("No relevant documents found in the Knowledge Base.")
        else:
            output_parts.append(f"Retrieval Time: {round(retrieval_time, 4)} seconds\n")
            for idx, chunk in enumerate(retrieved_chunks):
                output_parts.append(
                    f"{idx + 1}. Document: {chunk['filename']}\n"
                    f"   Similarity Score: {chunk['score']}\n"
                    f"   Chunk Index: {chunk['chunk_index']}\n"
                    f"   Snippet: {chunk['content'][:200]}...\n"
                )

        if github_context:
            output_parts.append("==================================================")
            output_parts.append("GITHUB CONTEXT")
            output_parts.append("==================================================")
            output_parts.append(github_context)

        output_parts.append("==================================================")
        output_parts.append("RESEARCH SUMMARY")
        output_parts.append("==================================================")
        output_parts.append(summary)

        return "\n".join(output_parts)
