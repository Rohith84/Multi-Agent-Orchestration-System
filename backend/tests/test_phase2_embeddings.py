import uuid
import pytest
from app.db.database import init_db, async_session_factory, engine
from app.knowledge.embeddings.generator import OllamaEmbeddingGenerator
from app.knowledge.vectorstore.chroma import ChromaStore
from app.services.knowledge_service import KnowledgeService
from app.knowledge.retriever.search import KnowledgeRetriever


@pytest.mark.asyncio(loop_scope="module")
async def test_fastembed_generation():
    """Verify that FastEmbed (unified EmbeddingGenerator) generates embeddings of size 384."""
    generator = OllamaEmbeddingGenerator()
    assert generator.get_dimension() == 384
    
    vector = await generator.generate_embedding("This is a test of in-process embeddings.")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(x, float) for x in vector)


@pytest.mark.asyncio(loop_scope="module")
async def test_chroma_dimension_mismatch_auto_heal():
    """Verify that ChromaStore automatically heals when dimension mismatch is encountered."""
    await engine.dispose()
    await init_db()
    
    # 1. Manually create a collection in Chroma with 768 dimensions using raw chromadb client
    import chromadb
    client = chromadb.PersistentClient(path="chroma_db")
    col_name = "knowledge_base"
    
    # If it exists, delete it first
    try:
        client.delete_collection(name=col_name)
    except Exception:
        pass
        
    col = client.create_collection(name=col_name, metadata={"hnsw:space": "cosine"})
    col.add(
        ids=["mock_doc"],
        embeddings=[[0.1] * 768],
        documents=["This is a 768-dimensional mock document"]
    )
    assert col.count() == 1
    
    # 2. Instantiate ChromaStore. It should automatically detect the 768 vs 384 mismatch,
    # delete it, and recreate it with 384 dimensions.
    store = ChromaStore()
    collection = store._get_collection()
    
    # The count should now be 0 (because it was wiped and recreated)
    assert collection.count() == 0
    
    # 3. Add a new 384-dimensional chunk and query it to verify it works
    store.add_chunks(
        document_id=uuid.uuid4(),
        filename="test_heal.txt",
        chunks=[{
            "chunk_index": 0,
            "content": "This is a healed 384-dimensional document",
            "embedding": [0.2] * 384
        }]
    )
    assert collection.count() == 1
    
    # Clean up
    try:
        client.delete_collection(name=col_name)
    except Exception:
        pass


@pytest.mark.asyncio(loop_scope="module")
async def test_document_ingestion_and_retrieval_without_ollama():
    """Verify end-to-end ingestion and semantic retrieval without any Ollama server calls."""
    await engine.dispose()
    await init_db()
    
    # Clear collection first
    store = ChromaStore()
    try:
        store.clear_collection()
    except Exception:
        pass

    async with async_session_factory() as session:
        service = KnowledgeService(session)
        
        # 1. Ingest document
        filename = f"test_ingest_{uuid.uuid4().hex[:6]}.txt"
        content = "Enterprise Multi-Agent Orchestration System (EMAOS) uses specialized agents to manage software development workflows."
        doc = await service.upload_document(filename, content.encode("utf-8"))
        
        assert doc.id is not None
        assert doc.filename == filename
        
        # 2. Retrieve document chunks using retriever
        retriever = KnowledgeRetriever()
        results = await retriever.retrieve("What is EMAOS?")
        
        assert len(results) > 0
        assert any("EMAOS" in r["content"] for r in results)
        assert results[0]["score"] > 0.0
