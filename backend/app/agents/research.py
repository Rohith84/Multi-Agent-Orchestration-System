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

from app.schemas.rag import RAGResult, RAGStatus

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

    async def execute_with_result(
        self,
        user_request: str,
        execution_plan: str,
        tool_runner: MCPToolRunner | None = None,
    ) -> tuple[str, RAGResult]:
        logger.info("Executing Research Agent with model=%s", self.model)

        # 1. Similarity Search with explicit RAGStatus
        rag_res: RAGResult = await self.retriever.retrieve_with_status(user_request, top_k=5)
        retrieved_chunks = rag_res.chunks
        retrieval_time = rag_res.retrieval_time

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
        if rag_res.status == RAGStatus.RAG_SUCCESS:
            context_blocks = []
            for idx, chunk in enumerate(retrieved_chunks):
                citation = f"Source {idx + 1}: {chunk['filename']} (similarity: {chunk['score']})"
                citation_sources.append(citation)
                context_blocks.append(f"--- {citation} ---\n{chunk['content']}")
            context_str = "\n\n".join(context_blocks)
        elif rag_res.status == RAGStatus.RAG_EMPTY:
            context_str = "Knowledge Base was accessed successfully, but no relevant documents were found for this query."
        else:
            # RAG_INFRASTRUCTURE_ERROR
            context_str = (
                f"Knowledge Base retrieval failed due to an infrastructure error: {rag_res.error or 'Vector DB error'}. "
                "Retrieved context is unavailable."
            )

        # 4. Generate LLM Prompt
        system_prompt = (
            "You are the Research Agent in a multi-agent orchestration system.\n\n"
            "## Role & Responsibilities\n"
            "You provide factual, technical, and project-specific context required to complete the task.\n"
            "You do NOT implement code, run tests, or make final decisions.\n\n"
            "## Evidence Categorization Guidelines (CRITICAL)\n"
            "Categorize your research notes explicitly using these distinctions:\n"
            "- FACT / PROJECT-SPECIFIC EVIDENCE: Verified information directly retrieved from the project context or vector store.\n"
            "- GENERAL KNOWLEDGE: Standard language, library, or framework conventions.\n"
            "- ASSUMPTION: Logical inferences made where project context is silent.\n"
            "- UNKNOWN: Critical missing information or unverified constraints.\n\n"
            "## Rules & Constraints\n"
            "- Do NOT invent documentation, project requirements, or file contents not in the provided context.\n"
            "- Prioritize retrieved project evidence over general assumptions.\n"
            "- Do NOT generate implementation code blocks.\n"
            "- Preserved RAGStatus (RAG_SUCCESS, RAG_EMPTY, RAG_INFRASTRUCTURE_ERROR) is authoritative.\n"
            "- If RAG_INFRASTRUCTURE_ERROR occurred, state clearly that retrieval failed and evidence is unavailable. NEVER claim 'no documents exist'.\n"
            "- If RAG_EMPTY occurred, state clearly that retrieval succeeded with 0 relevant documents.\n\n"
            "## Output Format\n"
            "Return research findings containing:\n"
            "- **Research Summary**: Overview of findings relevant to the task.\n"
            "- **Evidence Categorization**: Distinguish Facts, Evidence, General Knowledge, Assumptions, and Unknowns.\n"
            "- **Relevant Context**: Key information retrieved from Knowledge Base with citations.\n"
            "- **Recommended Approach**: Technical approach, APIs, and design patterns for Coder Agent.\n"
            "- **Constraints & Risks**: Architectural limitations, compatibility rules, or failure risks.\n"
            "- **Unresolved Questions**: Information that could not be found or verified.\n\n"
            "Keep the output focused and actionable for the Coding Agent."
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

        summary = await self.client.chat(messages, model=self.model, max_tokens=1400)

        # 5. Format detailed structured output for the timeline/SSE and Coder Agent
        output_parts = []
        output_parts.append("==================================================")
        output_parts.append(f"RETRIEVED DOCUMENTS & KNOWLEDGE (Status: {rag_res.status})")
        output_parts.append("==================================================")

        if rag_res.status == RAGStatus.RAG_INFRASTRUCTURE_ERROR:
            output_parts.append(f"ERROR: Knowledge Base retrieval failed due to an infrastructure error: {rag_res.error}")
            output_parts.append("Note: Vector database access failed. No document fabrication performed.")
        elif rag_res.status == RAGStatus.RAG_EMPTY:
            output_parts.append("Knowledge Base was accessed successfully, but returned 0 relevant document chunks.")
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

        return "\n".join(output_parts), rag_res

    async def execute(
        self,
        user_request: str,
        execution_plan: str,
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        text_output, _ = await self.execute_with_result(
            user_request=user_request,
            execution_plan=execution_plan,
            tool_runner=tool_runner,
        )
        return text_output

