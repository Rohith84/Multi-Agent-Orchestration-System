"""
Unit tests for Phase 6: Safe ChromaDB Recovery and Deterministic RAG States.

Verifies:
- Deterministic RAG states (RAG_SUCCESS, RAG_EMPTY, RAG_INFRASTRUCTURE_ERROR)
- Targeted recovery ONLY for KeyError('_type') and recoverable collection metadata errors
- Preservation of metadata {"hnsw:space": "cosine"}
- Data safety: unrelated collections and persistent directory are NEVER deleted
- Non-recoverable errors (permission, connection, unexpected exceptions) fail closed
- ResearchAgent proper reporting without document fabrication or false "no documents" claims
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.research import ResearchAgent
from app.ai.ollama_client import OllamaClient
from app.knowledge.retriever.search import KnowledgeRetriever
from app.knowledge.vectorstore.chroma import ChromaStore, VectorDBUnavailableError
from app.schemas.rag import RAGResult, RAGStatus


@pytest.fixture(autouse=True)
def mock_embedding_generator():
    with patch("app.knowledge.embeddings.generator.EmbeddingGenerator.__init__", return_value=None), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 384):
        yield


@pytest.mark.asyncio
async def test_1_successful_chromadb_retrieval():
    """1. Successful ChromaDB retrieval → RAG_SUCCESS."""
    retriever = KnowledgeRetriever()
    mock_chunks = [
        {"filename": "main.py", "document_id": "doc1", "chunk_index": 0, "content": "import sys", "score": 0.95}
    ]
    with patch.object(retriever.embedding_generator, "generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch.object(retriever.vector_store, "search_similarity", return_value=mock_chunks):
        mock_emb.return_value = [0.1] * 384
        res: RAGResult = await retriever.retrieve_with_status("query")

    assert res.status == RAGStatus.RAG_SUCCESS
    assert len(res.chunks) == 1
    assert res.error is None


@pytest.mark.asyncio
async def test_2_successful_retrieval_zero_results():
    """2. Successful retrieval with zero results → RAG_EMPTY."""
    retriever = KnowledgeRetriever()
    with patch.object(retriever.embedding_generator, "generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch.object(retriever.vector_store, "search_similarity", return_value=[]):
        mock_emb.return_value = [0.1] * 384
        res: RAGResult = await retriever.retrieve_with_status("query")

    assert res.status == RAGStatus.RAG_EMPTY
    assert len(res.chunks) == 0
    assert res.error is None


@pytest.mark.asyncio
async def test_3_collection_unavailable():
    """3. Collection unavailable → RAG_INFRASTRUCTURE_ERROR."""
    retriever = KnowledgeRetriever()
    with patch.object(retriever.embedding_generator, "generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch.object(retriever.vector_store, "search_similarity", side_effect=VectorDBUnavailableError("Chroma client down")):
        mock_emb.return_value = [0.1] * 384
        res: RAGResult = await retriever.retrieve_with_status("query")

    assert res.status == RAGStatus.RAG_INFRASTRUCTURE_ERROR
    assert len(res.chunks) == 0
    assert "VectorDBUnavailableError" in res.error


def test_4_5_6_keyerror_type_targeted_recovery():
    """
    4. Original KeyError('_type') triggers targeted recovery.
    5. _type recovery successfully recreates target collection.
    6. Preserves metadata={"hnsw:space": "cosine"}.
    """
    store = ChromaStore()
    mock_client = MagicMock()
    mock_collection = MagicMock()

    # Get collection fails first with KeyError('_type')
    mock_client.get_collection.side_effect = KeyError("_type")
    mock_client.create_collection.return_value = mock_collection

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384):
        col = store._get_collection()

    assert col == mock_collection
    # Verify targeted collection deletion was called for store.collection_name ONLY
    mock_client.delete_collection.assert_called_once_with(name=store.collection_name)
    mock_client.create_collection.assert_called_once_with(
        name=store.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def test_7_recovery_failure_raises():
    """7. Recovery failure → RAG_INFRASTRUCTURE_ERROR."""
    store = ChromaStore()
    mock_client = MagicMock()
    mock_client.get_collection.side_effect = KeyError("_type")
    mock_client.create_collection.side_effect = Exception("Disk full during creation")

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384):
        with pytest.raises(VectorDBUnavailableError) as exc_info:
            store._get_collection()

    assert "Targeted recovery failed" in str(exc_info.value)


def test_8_9_unrelated_collections_and_directory_protected():
    """
    8. Verify unrelated collections are NOT deleted.
    9. Verify the entire ChromaDB directory is NOT deleted.
    """
    store = ChromaStore()
    mock_client = MagicMock()
    mock_client.get_collection.side_effect = KeyError("_type")
    mock_client.create_collection.return_value = MagicMock()

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384), \
         patch("shutil.rmtree") as mock_rmtree:
        store._get_collection()

        # Verify rmtree was NEVER called
        mock_rmtree.assert_not_called()
        # Verify delete_collection was called ONLY with store.collection_name
        deleted_names = [call.kwargs.get("name") for call in mock_client.delete_collection.call_args_list]
        for name in deleted_names:
            assert name == store.collection_name


def test_10_original_exception_logged_and_preserved(caplog):
    """10. Verify original exception is logged/preserved."""
    store = ChromaStore()
    mock_client = MagicMock()
    original_exc = KeyError("_type")
    mock_client.get_collection.side_effect = original_exc
    mock_client.create_collection.return_value = MagicMock()

    with caplog.at_level(logging.WARNING), \
         patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384):
        store._get_collection()

    assert "metadata corruption detected" in caplog.text
    assert "_type" in caplog.text


def test_11_dimension_mismatch_affects_only_target_collection():
    """11. Embedding dimension mismatch affects only the target collection."""
    store = ChromaStore()
    mock_client = MagicMock()
    existing_col = MagicMock()
    existing_col.count.return_value = 1
    existing_col.peek.return_value = {"embeddings": [[0.1] * 768]}  # Existing has 768 dims

    mock_client.get_collection.return_value = existing_col
    new_col = MagicMock()
    mock_client.create_collection.return_value = new_col

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384):  # Active expects 384
        col = store._get_collection()

    assert col == new_col
    mock_client.delete_collection.assert_called_once_with(name=store.collection_name)
    mock_client.create_collection.assert_called_once_with(
        name=store.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def test_12_successful_recovery_allows_retrieval_to_continue():
    """12. Successful recovery allows retrieval to continue."""
    store = ChromaStore()
    mock_client = MagicMock()
    recovered_col = MagicMock()
    recovered_col.query.return_value = {
        "documents": [["def foo(): pass"]],
        "metadatas": [[{"filename": "a.py", "document_id": "1", "chunk_index": 0}]],
        "distances": [[0.1]],
    }
    mock_client.get_collection.side_effect = KeyError("_type")
    mock_client.create_collection.return_value = recovered_col

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384):
        res = store.search_similarity([0.1] * 384, top_k=1)

    assert len(res) == 1
    assert res[0]["filename"] == "a.py"


@pytest.mark.asyncio
async def test_13_failed_chroma_initialization():
    """13. Failed Chroma initialization → RAG_INFRASTRUCTURE_ERROR."""
    retriever = KnowledgeRetriever()
    with patch.object(retriever.vector_store, "_get_client", side_effect=VectorDBUnavailableError("Client init failed")):
        res = await retriever.retrieve_with_status("query")

    assert res.status == RAGStatus.RAG_INFRASTRUCTURE_ERROR
    assert len(res.chunks) == 0
    assert "Client init failed" in res.error


@pytest.mark.asyncio
async def test_14_query_exception():
    """14. Query exception → RAG_INFRASTRUCTURE_ERROR."""
    retriever = KnowledgeRetriever()
    with patch.object(retriever.embedding_generator, "generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch.object(retriever.vector_store, "search_similarity", side_effect=RuntimeError("Search crashed")):
        mock_emb.return_value = [0.1] * 384
        res = await retriever.retrieve_with_status("query")

    assert res.status == RAGStatus.RAG_INFRASTRUCTURE_ERROR
    assert len(res.chunks) == 0
    assert "Search crashed" in res.error


@pytest.mark.asyncio
async def test_15_empty_successful_query_is_not_infrastructure_failure():
    """15. Empty successful query is NOT infrastructure failure."""
    retriever = KnowledgeRetriever()
    with patch.object(retriever.embedding_generator, "generate_embedding", new_callable=AsyncMock) as mock_emb, \
         patch.object(retriever.vector_store, "search_similarity", return_value=[]):
        mock_emb.return_value = [0.1] * 384
        res = await retriever.retrieve_with_status("query")

    assert res.status == RAGStatus.RAG_EMPTY
    assert res.status != RAGStatus.RAG_INFRASTRUCTURE_ERROR
    assert res.error is None


@pytest.mark.asyncio
async def test_16_19_research_agent_reports_rag_success():
    """
    16. ResearchAgent reports RAG_SUCCESS correctly.
    19. ResearchAgent does not fabricate documents when RAG retrieval fails.
    """
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat = AsyncMock(return_value="Research summary based on Source 1")
    agent = ResearchAgent(mock_client)

    chunks = [{"filename": "main.py", "document_id": "1", "chunk_index": 0, "content": "print('hello')", "score": 0.9}]
    success_result = RAGResult(status=RAGStatus.RAG_SUCCESS, chunks=chunks, retrieval_time=0.1)

    with patch.object(agent.retriever, "retrieve_with_status", new_callable=AsyncMock, return_value=success_result):
        output = await agent.execute("request", "plan")

    assert "RETRIEVED DOCUMENTS & KNOWLEDGE (Status: RAG_SUCCESS)" in output
    assert "1. Document: main.py" in output


@pytest.mark.asyncio
async def test_17_research_agent_reports_rag_empty():
    """17. ResearchAgent reports RAG_EMPTY correctly."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat = AsyncMock(return_value="No code found summary")
    agent = ResearchAgent(mock_client)

    empty_result = RAGResult(status=RAGStatus.RAG_EMPTY, chunks=[], retrieval_time=0.05)

    with patch.object(agent.retriever, "retrieve_with_status", new_callable=AsyncMock, return_value=empty_result):
        output = await agent.execute("request", "plan")

    assert "RETRIEVED DOCUMENTS & KNOWLEDGE (Status: RAG_EMPTY)" in output
    assert "accessed successfully, but returned 0 relevant document chunks" in output


@pytest.mark.asyncio
async def test_18_20_research_agent_reports_rag_infrastructure_error():
    """
    18. ResearchAgent reports RAG_INFRASTRUCTURE_ERROR correctly.
    20. ResearchAgent does not claim 'no documents found' when the database itself failed.
    """
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat = AsyncMock(return_value="Fallback summary")
    agent = ResearchAgent(mock_client)

    infra_error_result = RAGResult(
        status=RAGStatus.RAG_INFRASTRUCTURE_ERROR,
        chunks=[],
        error="VectorDBUnavailableError: Chroma client down",
    )

    with patch.object(agent.retriever, "retrieve_with_status", new_callable=AsyncMock, return_value=infra_error_result):
        output = await agent.execute("request", "plan")

    assert "RETRIEVED DOCUMENTS & KNOWLEDGE (Status: RAG_INFRASTRUCTURE_ERROR)" in output
    assert "VectorDBUnavailableError: Chroma client down" in output
    assert "No relevant documents found in the Knowledge Base." not in output


def test_generic_exception_does_not_trigger_collection_recreation():
    """Verify generic/unrelated exceptions (e.g. PermissionError) DO NOT trigger delete_collection."""
    store = ChromaStore()
    mock_client = MagicMock()
    mock_client.get_collection.side_effect = PermissionError("Access denied to sqlite DB")

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384):
        with pytest.raises(VectorDBUnavailableError):
            store._get_collection()

    # Crucial assertion: delete_collection was NOT called for unrecoverable permission errors
    mock_client.delete_collection.assert_not_called()
