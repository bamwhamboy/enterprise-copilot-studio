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


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _make_pdf_bytes(*, pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    content = doc.tobytes()
    doc.close()
    return content


async def _create_knowledge_source(client: AsyncClient, headers: dict, name: str) -> str:
    response = await client.post(KS_BASE, json={"name": name}, headers=headers)
    return response.json()["id"]


async def _upload_pdf(
    client: AsyncClient, headers: dict, ks_id: str, filename: str, pages: list[str]
) -> dict:
    pdf_bytes = _make_pdf_bytes(pages=pages)
    response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_index_document_end_to_end(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="rag1@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "RAG Test Source")
    doc = await _upload_pdf(
        client,
        headers,
        ks_id,
        "leave_policy.pdf",
        pages=["Employees receive 20 days of paid annual leave per year. " * 20],
    )
    assert doc["processing_status"] == "READY"

    # Indexing itself remains unauthenticated (unchanged by this fix --
    # see the backend README's note on this and /search as related,
    # not-yet-addressed gaps of the same kind fixed here for
    # copilots/knowledge-sources/documents/chunks).
    response = await client.post(f"/api/v1/index/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc["id"]
    assert body["chunks_indexed"] > 0
    assert body["index_status"] == "INDEXED"

    get_response = await client.get(f"{DOC_BASE}/{doc['id']}", headers=headers)
    get_body = get_response.json()
    assert get_body["index_status"] == "INDEXED"
    assert get_body["chunks"] == body["chunks_indexed"]
    assert get_body["embeddings"] == body["chunks_indexed"]


@pytest.mark.asyncio
async def test_index_document_not_ready_returns_409(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="rag2@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Not Ready Source")
    create_response = await client.post(
        DOC_BASE, json={"knowledge_source_id": ks_id, "name": "no-file.pdf"}, headers=headers
    )
    doc_id = create_response.json()["id"]

    response = await client.post(f"/api/v1/index/{doc_id}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_index_nonexistent_document_returns_404(client: AsyncClient) -> None:
    response = await client.post("/api/v1/index/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_chunks_for_indexed_document(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="rag3@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Chunks Test Source")
    doc = await _upload_pdf(
        client, headers, ks_id, "handbook.pdf", pages=["Company handbook content. " * 30]
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    response = await client.get(f"/api/v1/chunks/{doc['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc["id"]
    assert len(body["chunks"]) > 0
    first = body["chunks"][0]
    assert first["document_name"] == "handbook.pdf"
    assert first["knowledge_source_id"] == ks_id


@pytest.mark.asyncio
async def test_list_chunks_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/chunks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cannot_list_chunks_for_another_organizations_document(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(
            email="rag-chunks-org-a@example.com", organization_name="Chunks Org A"
        )
    )
    ks_id = await _create_knowledge_source(client, org_a_headers, "Org A Chunks Source")
    doc = await _upload_pdf(
        client, org_a_headers, ks_id, "private.pdf", pages=["Confidential content. " * 20]
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    org_b_headers = _auth_headers(
        await register_and_login(
            email="rag-chunks-org-b@example.com", organization_name="Chunks Org B"
        )
    )
    response = await client.get(f"/api/v1/chunks/{doc['id']}", headers=org_b_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_chunks_for_unindexed_document_is_empty(
    client: AsyncClient, register_and_login
) -> None:
    """A document that exists but hasn't been indexed yet (the realistic
    "unindexed" case -- e.g. right after upload, before POST /index) has
    zero chunks in Qdrant, which is a legitimate 200 + empty list, not
    an error.
    """
    headers = _auth_headers(await register_and_login(email="rag4@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Unindexed Doc Source")
    create_response = await client.post(
        DOC_BASE,
        json={"knowledge_source_id": ks_id, "name": "never-indexed.pdf"},
        headers=headers,
    )
    doc_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/chunks/{doc_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["chunks"] == []


@pytest.mark.asyncio
async def test_list_chunks_for_nonexistent_document_returns_404(
    client: AsyncClient, register_and_login
) -> None:
    """A document_id that doesn't exist in Postgres at all now 404s,
    rather than the previous behavior of silently returning an empty
    chunk list for any unrecognized id -- this endpoint didn't used to
    check whether the document existed before querying Qdrant directly;
    now it does (the same existence/ownership check GET /documents/{id}
    already applied), which is the more correct, more consistent
    behavior, matching how a nonexistent id behaves everywhere else in
    this API.
    """
    headers = _auth_headers(await register_and_login(email="rag4b@example.com"))
    response = await client.get(
        "/api/v1/chunks/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_returns_results_with_citations(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="rag5@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Search Test Source")
    doc = await _upload_pdf(
        client,
        headers,
        ks_id,
        "travel_policy.pdf",
        pages=["All travel bookings require manager approval before purchase. " * 20],
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    response = await client.get(
        "/api/v1/search", params={"q": "manager approval travel"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "manager approval travel"
    assert len(body["results"]) > 0

    result = body["results"][0]
    assert "citation" in result
    assert result["citation"]["document_name"] == "travel_policy.pdf"
    assert result["citation"]["knowledge_source_id"] == ks_id


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search", params={"q": "anything"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_filters_by_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="rag6@example.com"))
    ks_a = await _create_knowledge_source(client, headers, "Search Filter Source A")
    ks_b = await _create_knowledge_source(client, headers, "Search Filter Source B")

    doc_a = await _upload_pdf(
        client, headers, ks_a, "a.pdf", pages=["Alpha content about onboarding. " * 20]
    )
    doc_b = await _upload_pdf(
        client, headers, ks_b, "b.pdf", pages=["Beta content about onboarding. " * 20]
    )
    await client.post(f"/api/v1/index/{doc_a['id']}")
    await client.post(f"/api/v1/index/{doc_b['id']}")

    response = await client.get(
        "/api/v1/search",
        params={"q": "onboarding", "knowledge_source_id": ks_a},
        headers=headers,
    )
    body = response.json()
    assert all(r["citation"]["knowledge_source_id"] == ks_a for r in body["results"])


@pytest.mark.asyncio
async def test_cannot_search_using_another_organizations_knowledge_source_id(
    client: AsyncClient, register_and_login
) -> None:
    """Explicitly requesting another organization's knowledge_source_id
    as a filter must not be honored -- 404, not a silent search of
    content that isn't the caller's.
    """
    org_a_headers = _auth_headers(
        await register_and_login(
            email="rag-search-org-a@example.com", organization_name="Search Org A"
        )
    )
    ks_id = await _create_knowledge_source(client, org_a_headers, "Org A Search Source")
    doc = await _upload_pdf(
        client, org_a_headers, ks_id, "private.pdf", pages=["Confidential content. " * 20]
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    org_b_headers = _auth_headers(
        await register_and_login(
            email="rag-search-org-b@example.com", organization_name="Search Org B"
        )
    )
    response = await client.get(
        "/api/v1/search",
        params={"q": "confidential", "knowledge_source_id": ks_id},
        headers=org_b_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_without_a_source_filter_only_returns_own_organizations_content(
    client: AsyncClient, register_and_login
) -> None:
    """The actual regression test for this fix: searching with no
    knowledge_source_id specified must be constrained to the caller's
    own organization, not every organization's indexed content.
    """
    org_a_headers = _auth_headers(
        await register_and_login(
            email="rag-search-scope-a@example.com", organization_name="Search Scope Org A"
        )
    )
    ks_a = await _create_knowledge_source(client, org_a_headers, "Scope Org A Source")
    doc_a = await _upload_pdf(
        client,
        org_a_headers,
        ks_a,
        "org-a-secret.pdf",
        pages=["Org A confidential onboarding procedure details. " * 20],
    )
    await client.post(f"/api/v1/index/{doc_a['id']}")

    org_b_headers = _auth_headers(
        await register_and_login(
            email="rag-search-scope-b@example.com", organization_name="Search Scope Org B"
        )
    )
    ks_b = await _create_knowledge_source(client, org_b_headers, "Scope Org B Source")
    doc_b = await _upload_pdf(
        client,
        org_b_headers,
        ks_b,
        "org-b-doc.pdf",
        pages=["Org B onboarding procedure details. " * 20],
    )
    await client.post(f"/api/v1/index/{doc_b['id']}")

    # Org B searches with no specific source -- must only ever see its
    # own document, never Org A's, even though Org A's content is a
    # strong semantic match for the same query.
    response = await client.get(
        "/api/v1/search", params={"q": "onboarding procedure details"}, headers=org_b_headers
    )
    assert response.status_code == 200
    body = response.json()
    document_names = {r["citation"]["document_name"] for r in body["results"]}
    assert document_names == {"org-b-doc.pdf"}
    assert "org-a-secret.pdf" not in document_names


@pytest.mark.asyncio
async def test_search_for_organization_with_no_knowledge_sources_returns_empty(
    client: AsyncClient, register_and_login
) -> None:
    """An organization that owns zero knowledge sources must get zero
    results -- not an unrestricted search across every organization's
    content (an empty owned-sources list is falsy in Python, which
    could otherwise be silently treated the same as "no filter" if not
    handled explicitly).
    """
    other_org_headers = _auth_headers(
        await register_and_login(
            email="rag-search-empty-other@example.com", organization_name="Empty Search Other Org"
        )
    )
    ks_id = await _create_knowledge_source(client, other_org_headers, "Other Org Source")
    doc = await _upload_pdf(
        client, other_org_headers, ks_id, "other.pdf", pages=["Other org content. " * 20]
    )
    await client.post(f"/api/v1/index/{doc['id']}")

    empty_org_headers = _auth_headers(
        await register_and_login(
            email="rag-search-empty-mine@example.com", organization_name="Empty Search My Org"
        )
    )
    response = await client.get(
        "/api/v1/search", params={"q": "content"}, headers=empty_org_headers
    )
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.asyncio
async def test_search_with_no_indexed_documents_returns_empty(
    client: AsyncClient, register_and_login
) -> None:
    """Confirms the not-yet-existing-collection path is handled gracefully."""
    headers = _auth_headers(await register_and_login(email="rag7@example.com"))
    response = await client.get(
        "/api/v1/search", params={"q": "anything at all"}, headers=headers
    )
    assert response.status_code == 200
    assert "results" in response.json()
