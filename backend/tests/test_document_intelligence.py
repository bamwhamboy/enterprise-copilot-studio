"""Tests for POST /api/v1/document-intelligence/classify-document/{document_id}.

Mirrors the real end-to-end path the frontend now depends on: upload a
real PDF (via ``/documents/upload``, exercising the actual ingestion
pipeline), then classify it by id.
"""

import io

import fitz
import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"
DI_BASE = "/api/v1/document-intelligence"


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


async def _create_knowledge_source(
    client: AsyncClient, headers: dict, name: str = "Doc Intelligence Test Source"
) -> str:
    response = await client.post(KS_BASE, json={"name": name}, headers=headers)
    assert response.status_code == 201
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
async def test_classify_document_recommends_hr_copilot_for_leave_policy(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="di-hr@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "HR Source")
    document = await _upload_pdf(
        client,
        headers,
        ks_id,
        "Leave Policy.pdf",
        pages=["Employee Leave and Time Off Policy", "Requesting vacation and PTO"],
    )

    response = await client.post(
        f"{DI_BASE}/classify-document/{document['id']}", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "HR"
    assert body["recommended_copilot"] == "HR Copilot"
    assert body["document_type"] == "Leave & Time Off Policy"
    assert 0.0 <= body["confidence"] <= 1.0
    assert any(
        signal in body["matched_signals"] for signal in ("leave", "vacation", "pto", "time off")
    )


@pytest.mark.asyncio
async def test_classify_document_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        f"{DI_BASE}/classify-document/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_classify_document_404_for_missing_document(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="di-missing@example.com"))
    response = await client.post(
        f"{DI_BASE}/classify-document/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_classify_document_404_for_another_organizations_document(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(email="di-org-a@example.com", organization_name="DI Org A")
    )
    ks_id = await _create_knowledge_source(client, org_a_headers, "Org A Source")
    document = await _upload_pdf(
        client, org_a_headers, ks_id, "confidential.pdf", pages=["Org A only content."]
    )

    org_b_headers = _auth_headers(
        await register_and_login(email="di-org-b@example.com", organization_name="DI Org B")
    )
    response = await client.post(
        f"{DI_BASE}/classify-document/{document['id']}", headers=org_b_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_classify_document_falls_back_to_filename_only_when_no_extracted_text(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="di-fallback@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Fallback Source")
    create_response = await client.post(
        DOC_BASE,
        json={
            "knowledge_source_id": ks_id,
            "name": "Employee Benefits and Compensation.pdf",
            "status": "indexed",
            "pages": 1,
            "chunks": 1,
            "embeddings": 1,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    document_id = create_response.json()["id"]

    response = await client.post(
        f"{DI_BASE}/classify-document/{document_id}", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["domain"] == "HR"


@pytest.mark.asyncio
async def test_stateless_classify_endpoint_still_works_unchanged(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="di-stateless@example.com"))
    response = await client.post(
        f"{DI_BASE}/classify",
        json={"filename": "Legal Contract Agreement.pdf", "text": "This NDA and agreement..."},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["domain"] == "Legal"
