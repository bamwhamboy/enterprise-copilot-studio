"""Tests for POST /api/v1/documents/upload.

Uses PyMuPDF itself to generate small real PDFs in-memory — no fixture
files, no mocking of the parser or storage layer.
"""

import io

import fitz
import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


def _make_pdf_bytes(*, pages: list[str]) -> bytes:
    """Generate a real, valid PDF with one line of text per page."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    content = doc.tobytes()
    doc.close()
    return content


async def _create_knowledge_source(client: AsyncClient, name: str = "Upload Test Source") -> str:
    response = await client.post(KS_BASE, json={"name": name})
    return response.json()["id"]


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Upload Success Source")
    pdf_bytes = _make_pdf_bytes(pages=["Page one text.", "Page two text."])

    response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": ("handbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "handbook.pdf"
    assert body["pages"] == 2
    assert body["processing_status"] == "READY"
    assert body["status"] == "indexed"
    assert body["mime_type"] == "application/pdf"
    assert body["file_size_bytes"] == len(pdf_bytes)
    assert body["storage_path"] is not None
    assert body["extracted_text_path"] is not None


@pytest.mark.asyncio
async def test_upload_registers_document_retrievable_via_get(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Retrievable Upload Source")
    pdf_bytes = _make_pdf_bytes(pages=["Only page."])

    upload_response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": ("single.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_response.json()["id"]

    get_response = await client.get(f"{DOC_BASE}/{doc_id}")
    assert get_response.status_code == 200
    assert get_response.json()["processing_status"] == "READY"


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Reject Non-PDF Source")

    response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": ("notes.txt", io.BytesIO(b"just some text"), "text/plain")},
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_missing_knowledge_source(client: AsyncClient) -> None:
    pdf_bytes = _make_pdf_bytes(pages=["Orphan page."])

    response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": "00000000-0000-0000-0000-000000000000"},
        files={"file": ("orphan.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_uploaded_document_removes_files_from_disk(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Delete Upload Source")
    pdf_bytes = _make_pdf_bytes(pages=["Deletable page."])

    upload_response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": ("deleteme.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    body = upload_response.json()
    doc_id = body["id"]

    from pathlib import Path

    storage_path = Path(body["storage_path"])
    text_path = Path(body["extracted_text_path"])
    assert storage_path.exists()
    assert text_path.exists()

    delete_response = await client.delete(f"{DOC_BASE}/{doc_id}")
    assert delete_response.status_code == 204

    assert not storage_path.exists()
    assert not text_path.exists()

    get_response = await client.get(f"{DOC_BASE}/{doc_id}")
    assert get_response.status_code == 404
