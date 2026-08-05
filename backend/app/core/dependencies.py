"""Reusable FastAPI dependencies.

Centralizing dependency providers here (rather than importing settings,
sessions, etc. ad hoc in each router) keeps ``Depends(...)`` usage
consistent and makes it trivial to override providers in tests via
``app.dependency_overrides``.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from llama_index.core.base.embeddings.base import BaseEmbedding
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.guardrails.prompt_sanitizer import PromptSanitizer
from app.knowledge_engine.chunking.hierarchical_chunker import HierarchicalChunker
from app.knowledge_engine.compression.compression_service import ContextCompressionService
from app.knowledge_engine.embeddings.embedding_model import build_embedding_model
from app.knowledge_engine.indexing.indexing_service import IndexingService
from app.knowledge_engine.indexing.vector_store import build_qdrant_client, build_vector_store
from app.knowledge_engine.pipeline.ingestion_pipeline import DocumentIngestionPipeline
from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever
from app.knowledge_engine.storage.document_storage import DocumentStorageService
from app.llm.gateway import LLMGateway
from app.llm.providers import build_provider_clients
from app.prompt_engine.renderer import PromptRenderer
from app.services.copilot_service import CopilotService
from app.services.document_service import DocumentService
from app.services.knowledge_source_service import KnowledgeSourceService

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias around ``app.database.session.get_db`` for a stable import path."""
    async for session in get_db():
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_copilot_service(session: DbSessionDep) -> CopilotService:
    return CopilotService(session)


async def get_knowledge_source_service(session: DbSessionDep) -> KnowledgeSourceService:
    return KnowledgeSourceService(session)


async def get_document_storage_service(settings: SettingsDep) -> DocumentStorageService:
    return DocumentStorageService(settings)


DocumentStorageServiceDep = Annotated[DocumentStorageService, Depends(get_document_storage_service)]


async def get_ingestion_pipeline(
    settings: SettingsDep, storage: DocumentStorageServiceDep
) -> DocumentIngestionPipeline:
    return DocumentIngestionPipeline(settings, storage)


IngestionPipelineDep = Annotated[DocumentIngestionPipeline, Depends(get_ingestion_pipeline)]


async def get_document_service(
    session: DbSessionDep,
    storage: DocumentStorageServiceDep,
    pipeline: IngestionPipelineDep,
) -> DocumentService:
    return DocumentService(session, storage=storage, pipeline=pipeline)


CopilotServiceDep = Annotated[CopilotService, Depends(get_copilot_service)]
KnowledgeSourceServiceDep = Annotated[KnowledgeSourceService, Depends(get_knowledge_source_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


# --- Sprint 4: AI infrastructure DI providers -------------------------------
# Not consumed by any route yet (no chat/RAG endpoints exist), but available
# for Sprint 3B/5 to depend on via Depends(...), consistent with every other
# service in this module.


async def get_llm_gateway(settings: SettingsDep) -> LLMGateway:
    """Build an ``LLMGateway`` wired to all four configured provider clients."""
    clients = build_provider_clients(settings)
    return LLMGateway(settings, clients)


LLMGatewayDep = Annotated[LLMGateway, Depends(get_llm_gateway)]


async def get_prompt_sanitizer() -> PromptSanitizer:
    """Build a ``PromptSanitizer`` with the default blocked-term list.

    Injection/PII detectors aren't passed in yet — no concrete
    implementations exist until a later sprint (see
    ``app.guardrails.prompt_sanitizer``).
    """
    return PromptSanitizer()


PromptSanitizerDep = Annotated[PromptSanitizer, Depends(get_prompt_sanitizer)]


async def get_prompt_renderer() -> PromptRenderer:
    return PromptRenderer()


PromptRendererDep = Annotated[PromptRenderer, Depends(get_prompt_renderer)]


# --- Sprint 3B: Enterprise Hybrid Hierarchical RAG DI providers -------------
# Qdrant client and the embedding model are expensive to build (the real
# HuggingFaceEmbedding loads model weights) so they're cached as process-wide
# singletons here rather than rebuilt per request — while still being
# overridable in tests via app.dependency_overrides (see tests/conftest.py,
# which overrides get_embed_model with a MockEmbedding).

_qdrant_client: QdrantClient | None = None
_embed_model: BaseEmbedding | None = None


async def get_qdrant_client(settings: SettingsDep) -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = build_qdrant_client(settings)
    return _qdrant_client


QdrantClientDep = Annotated[QdrantClient, Depends(get_qdrant_client)]


async def get_vector_store(settings: SettingsDep, client: QdrantClientDep) -> QdrantVectorStore:
    return build_vector_store(settings, client)


VectorStoreDep = Annotated[QdrantVectorStore, Depends(get_vector_store)]


async def get_embed_model(settings: SettingsDep) -> BaseEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model = build_embedding_model(settings)
    return _embed_model


EmbedModelDep = Annotated[BaseEmbedding, Depends(get_embed_model)]


async def get_hierarchical_chunker(settings: SettingsDep) -> HierarchicalChunker:
    return HierarchicalChunker(settings)


HierarchicalChunkerDep = Annotated[HierarchicalChunker, Depends(get_hierarchical_chunker)]


async def get_indexing_service(
    session: DbSessionDep,
    chunker: HierarchicalChunkerDep,
    embed_model: EmbedModelDep,
    vector_store: VectorStoreDep,
) -> IndexingService:
    return IndexingService(session, chunker, embed_model, vector_store)


IndexingServiceDep = Annotated[IndexingService, Depends(get_indexing_service)]


async def get_hybrid_retriever(
    settings: SettingsDep,
    client: QdrantClientDep,
    vector_store: VectorStoreDep,
    embed_model: EmbedModelDep,
) -> HybridRetriever:
    return HybridRetriever(settings, client, vector_store, embed_model)


HybridRetrieverDep = Annotated[HybridRetriever, Depends(get_hybrid_retriever)]


async def get_compression_service(settings: SettingsDep) -> ContextCompressionService:
    return ContextCompressionService(settings)


CompressionServiceDep = Annotated[ContextCompressionService, Depends(get_compression_service)]
