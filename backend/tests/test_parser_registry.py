"""Unit tests for the multi-format parser interface and registry.

Covers each format-specific parser's ``extract()`` in isolation (no
HTTP, no DB) and ``ParserRegistry``'s extension-based resolution and
derived allowed-extension/MIME-type sets.
"""

import csv
import io

import docx
import fitz
import openpyxl
import pptx
import pytest

from app.knowledge_engine.parser.base import ParsedDocument
from app.knowledge_engine.parser.csv_parser import CsvParser
from app.knowledge_engine.parser.docx_parser import DocxParser
from app.knowledge_engine.parser.pdf_parser import PdfParser
from app.knowledge_engine.parser.pptx_parser import PptxParser
from app.knowledge_engine.parser.registry import ParserRegistry, build_default_registry
from app.knowledge_engine.parser.txt_parser import TxtParser
from app.knowledge_engine.parser.xlsx_parser import XlsxParser


# --- Fixture file builders (in-memory, no fixture files on disk) -----------


def _make_pdf(tmp_path, pages: list[str]):
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    path = tmp_path / "doc.pdf"
    doc.save(path)
    doc.close()
    return path


def _make_docx(tmp_path, paragraphs: list[str], table_rows: list[list[str]] | None = None):
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    if table_rows:
        table = document.add_table(rows=0, cols=len(table_rows[0]))
        for row_values in table_rows:
            row = table.add_row()
            for cell, value in zip(row.cells, row_values):
                cell.text = value
    path = tmp_path / "doc.docx"
    document.save(path)
    return path


def _make_pptx(tmp_path, slide_texts: list[str]):
    presentation = pptx.Presentation()
    for text in slide_texts:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = text
    path = tmp_path / "deck.pptx"
    presentation.save(path)
    return path


def _make_csv(tmp_path, headers: list[str], rows: list[list[str]]):
    path = tmp_path / "data.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def _make_xlsx(tmp_path, sheets: dict[str, tuple[list[str], list[list[str]]]]):
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for sheet_name, (headers, rows) in sheets.items():
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
    path = tmp_path / "data.xlsx"
    workbook.save(path)
    return path


def _make_txt(tmp_path, content: str, encoding: str = "utf-8"):
    path = tmp_path / "notes.txt"
    path.write_bytes(content.encode(encoding))
    return path


# --- PdfParser (behavior unchanged by the refactor) -------------------------


def test_pdf_parser_extracts_text_and_page_count(tmp_path):
    path = _make_pdf(tmp_path, ["Page one text", "Page two text"])
    result = PdfParser().extract(path)

    assert isinstance(result, ParsedDocument)
    assert "Page one text" in result.text
    assert "Page two text" in result.text
    assert result.page_count == 2


def test_pdf_parser_declares_extensions_and_mime_types():
    assert PdfParser.extensions == frozenset({".pdf"})
    assert PdfParser.mime_types == frozenset({"application/pdf"})


# --- TxtParser ---------------------------------------------------------------


def test_txt_parser_extracts_text(tmp_path):
    path = _make_txt(tmp_path, "Hello, world.\nSecond line.")
    result = TxtParser().extract(path)

    assert result.text == "Hello, world.\nSecond line."
    assert result.page_count == 1


def test_txt_parser_falls_back_through_encodings(tmp_path):
    # A byte sequence that's invalid UTF-8 but valid latin-1.
    path = tmp_path / "latin.txt"
    path.write_bytes(b"Caf\xe9 latin-1 byte")

    result = TxtParser().extract(path)

    assert "Caf" in result.text
    assert result.page_count == 1


# --- DocxParser --------------------------------------------------------------


def test_docx_parser_extracts_paragraphs_and_tables(tmp_path):
    path = _make_docx(
        tmp_path,
        ["First paragraph.", "Second paragraph."],
        table_rows=[["Name", "Role"], ["Acme Corp", "Vendor"]],
    )
    result = DocxParser().extract(path)

    assert "First paragraph." in result.text
    assert "Second paragraph." in result.text
    assert "Acme Corp" in result.text and "Vendor" in result.text
    assert result.page_count >= 1


def test_docx_parser_declares_extensions_and_mime_types():
    assert DocxParser.extensions == frozenset({".docx"})


# --- PptxParser --------------------------------------------------------------


def test_pptx_parser_extracts_slide_text_and_count(tmp_path):
    path = _make_pptx(tmp_path, ["First Slide Title", "Second Slide Title"])
    result = PptxParser().extract(path)

    assert "First Slide Title" in result.text
    assert "Second Slide Title" in result.text
    assert result.page_count == 2


# --- CsvParser: column names repeated per row --------------------------------


def test_csv_parser_repeats_column_names_in_every_row(tmp_path):
    path = _make_csv(
        tmp_path,
        ["Name", "Amount"],
        [["Registration Fee", "150"], ["Late Fee", "25"]],
    )
    result = CsvParser().extract(path)

    lines = result.text.splitlines()
    assert len(lines) == 2
    assert "Name: Registration Fee" in lines[0]
    assert "Amount: 150" in lines[0]
    assert "Name: Late Fee" in lines[1]
    assert "Amount: 25" in lines[1]
    assert result.page_count == 1


def test_csv_parser_handles_empty_file(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")

    result = CsvParser().extract(path)

    assert result.text == ""
    assert result.page_count == 1


# --- XlsxParser: column names repeated per row, per sheet -------------------


def test_xlsx_parser_repeats_column_names_and_labels_sheets(tmp_path):
    path = _make_xlsx(
        tmp_path,
        {
            "Fees": (["Name", "Amount"], [["Registration Fee", "150"]]),
            "Contacts": (["Name", "Email"], [["Acme Corp", "billing@acme.example"]]),
        },
    )
    result = XlsxParser().extract(path)

    assert "Sheet: Fees" in result.text
    assert "Name: Registration Fee" in result.text
    assert "Amount: 150" in result.text
    assert "Sheet: Contacts" in result.text
    assert "Name: Acme Corp" in result.text
    assert "Email: billing@acme.example" in result.text
    assert result.page_count == 2


# --- ParserRegistry -----------------------------------------------------------


def test_registry_resolves_by_extension():
    registry = ParserRegistry([PdfParser(), TxtParser()])

    assert isinstance(registry.resolve("report.pdf"), PdfParser)
    assert isinstance(registry.resolve("notes.txt"), TxtParser)
    assert isinstance(registry.resolve("REPORT.PDF"), PdfParser)  # case-insensitive


def test_registry_returns_none_for_unregistered_extension():
    registry = ParserRegistry([PdfParser()])
    assert registry.resolve("archive.zip") is None


def test_registry_derives_allowed_extensions_and_mime_types():
    registry = ParserRegistry([PdfParser(), TxtParser()])

    assert registry.allowed_extensions() == frozenset({".pdf", ".txt"})
    assert registry.allowed_mime_types() == frozenset({"application/pdf", "text/plain"})


def test_default_registry_supports_all_sprint_formats():
    registry = build_default_registry()

    assert registry.allowed_extensions() == frozenset(
        {".pdf", ".docx", ".txt", ".pptx", ".csv", ".xlsx"}
    )
    assert isinstance(registry.resolve("agreement.docx"), DocxParser)
    assert isinstance(registry.resolve("data.xlsx"), XlsxParser)
    assert isinstance(registry.resolve("deck.pptx"), PptxParser)
    assert isinstance(registry.resolve("rows.csv"), CsvParser)
