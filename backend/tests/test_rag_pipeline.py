"""End-to-end tests for the Sprint 3B RAG pipeline: upload -> index -> search -> chunks.

Uses real PyMuPDF-generated PDFs, the real hierarchical chunker, and
real (in-memory) Qdrant — only the embedding model is mocked (network
to huggingface.co is unavailable in this environment; see conftest.py).
"""

import io

import fitz
import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


def _make_pdf_bytes(*, pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    content = doc.tobytes()
    doc.close()
    return content


async def _create_knowledge_source(client: AsyncClient, name: str) -> str:
    response = await client.post(KS_BASE, json={"name": name})
    return response.json()["id"]


async def _upload_pdf(client: AsyncClient, ks_id: str, filename: str, pages: list[str]) -> dict:
    pdf_bytes = _make_pdf_bytes(pages=pages)
    response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_index_document_end_to_end(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "RAG Test Source")
    doc = await _upload_pdf(
        client,
        ks_id,
        "leave_policy.pdf",
        pages=["Employees receive 20 days of paid annual leave per year. " * 20],
    )
    assert doc["processing_status"] == "READY"

    response = await client.post(f"/api/v1/index/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc["id"]
    assert body["chunks_indexed"] > 0
    assert body["index_status"] == "INDEXED"

    get_response = await client.get(f"{DOC_BASE}/{doc['id']}")
    get_body = get_response.json()
    assert get_body["index_status"] == "INDEXED"
    assert get_body["chunks"] == body["chunks_indexed"]
    assert get_body["embeddings"] == body["chunks_indexed"]


@pytest.mark.asyncio
async def test_index_document_not_ready_returns_409(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Not Ready Source")
    create_response = await client.post(
        DOC_BASE, json={"knowledge_source_id": ks_id, "name": "no-file.pdf"}
    )
    doc_id = create_response.json()["id"]

    response = await client.post(f"/api/v1/index/{doc_id}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_index_nonexistent_document_returns_404(client: AsyncClient) -> None:
    response = await client.post("/api/v1/index/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_chunks_for_indexed_document(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Chunks Test Source")
    doc = await _upload_pdf(
        client, ks_id, "handbook.pdf", pages=["Company handbook content. " * 30]
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    response = await client.get(f"/api/v1/chunks/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc["id"]
    assert len(body["chunks"]) > 0
    first = body["chunks"][0]
    assert first["document_name"] == "handbook.pdf"
    assert first["knowledge_source_id"] == ks_id


@pytest.mark.asyncio
async def test_list_chunks_for_unindexed_document_is_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/chunks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 200
    assert response.json()["chunks"] == []


@pytest.mark.asyncio
async def test_search_returns_results_with_citations(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Search Test Source")
    doc = await _upload_pdf(
        client,
        ks_id,
        "travel_policy.pdf",
        pages=["All travel bookings require manager approval before purchase. " * 20],
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    response = await client.get("/api/v1/search", params={"q": "manager approval travel"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "manager approval travel"
    assert len(body["results"]) > 0

    result = body["results"][0]
    assert "citation" in result
    assert result["citation"]["document_name"] == "travel_policy.pdf"
    assert result["citation"]["knowledge_source_id"] == ks_id


@pytest.mark.asyncio
async def test_search_filters_by_knowledge_source(client: AsyncClient) -> None:
    ks_a = await _create_knowledge_source(client, "Search Filter Source A")
    ks_b = await _create_knowledge_source(client, "Search Filter Source B")

    doc_a = await _upload_pdf(client, ks_a, "a.pdf", pages=["Alpha content about onboarding. " * 20])
    doc_b = await _upload_pdf(client, ks_b, "b.pdf", pages=["Beta content about onboarding. " * 20])
    await client.post(f"/api/v1/index/{doc_a['id']}")
    await client.post(f"/api/v1/index/{doc_b['id']}")

    response = await client.get(
        "/api/v1/search", params={"q": "onboarding", "knowledge_source_id": ks_a}
    )
    body = response.json()
    assert all(r["citation"]["knowledge_source_id"] == ks_a for r in body["results"])


@pytest.mark.asyncio
async def test_search_with_no_indexed_documents_returns_empty(client: AsyncClient) -> None:
    """Confirms the not-yet-existing-collection path is handled gracefully."""
    response = await client.get("/api/v1/search", params={"q": "anything at all"})
    assert response.status_code == 200
    assert "results" in response.json()
