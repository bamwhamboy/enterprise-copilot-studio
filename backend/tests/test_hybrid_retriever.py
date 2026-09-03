"""Focused tests for explicit document-scoped retrieval."""

from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever


def _retriever():
    return object.__new__(HybridRetriever)


def test_qdrant_filter_without_document_preserves_knowledge_source_scope():
    result = _retriever()._build_qdrant_filter("ks-a", None)

    assert result is not None
    assert len(result.must) == 1
    assert result.must[0].key == "knowledge_source_id"


def test_qdrant_filter_adds_document_scope():
    result = _retriever()._build_qdrant_filter("ks-a", None, "doc-a")

    keys = {condition.key for condition in result.must}

    assert keys == {"knowledge_source_id", "source_document_id"}


def test_qdrant_filter_ands_document_and_knowledge_source():
    result = _retriever()._build_qdrant_filter("ks-a", None, "doc-a")

    values = {
        condition.key: condition
        for condition in result.must
    }

    assert values["knowledge_source_id"].match.value == "ks-a"
    assert values["source_document_id"].match.value == "doc-a"


def test_document_only_qdrant_filter_is_supported():
    result = _retriever()._build_qdrant_filter(None, None, "doc-a")

    assert len(result.must) == 1
    assert result.must[0].key == "source_document_id"
    assert result.must[0].match.value == "doc-a"


def test_multiple_knowledge_sources_remain_supported():
    result = _retriever()._build_qdrant_filter(
        None,
        ["ks-a", "ks-b"],
        "doc-a",
    )

    keys = {condition.key for condition in result.must}

    assert "knowledge_source_id" in keys
    assert "source_document_id" in keys


def test_qdrant_filter_without_any_scope_is_unrestricted():
    result = _retriever()._build_qdrant_filter(None, None)

    assert result is None


def test_llama_filters_add_document_scope():
    result = _retriever()._to_llama_filters(
        "ks-a",
        None,
        "doc-a",
    )

    keys = {item.key for item in result.filters}

    assert "knowledge_source_id" in keys
    assert "source_document_id" in keys


def test_llama_filters_without_document_preserve_existing_scope():
    result = _retriever()._to_llama_filters("ks-a", None)

    assert len(result.filters) == 1
    assert result.filters[0].key == "knowledge_source_id"


def test_llama_filters_support_document_only():
    result = _retriever()._to_llama_filters(None, None, "doc-a")

    assert len(result.filters) == 1
    assert result.filters[0].key == "source_document_id"
    assert result.filters[0].value == "doc-a"


def test_fetch_corpus_nodes_accepts_document_id():
    import inspect

    signature = inspect.signature(
        _retriever()._fetch_corpus_nodes
    )

    assert "document_id" in signature.parameters


def test_retrieve_accepts_document_id():
    import inspect

    signature = inspect.signature(
        _retriever().retrieve
    )

    assert "document_id" in signature.parameters


def test_document_scope_is_exact_document_identifier():
    result = _retriever()._build_qdrant_filter(
        "ks-a",
        None,
        "doc-a",
    )

    document_conditions = [
        condition
        for condition in result.must
        if condition.key == "source_document_id"
    ]

    assert len(document_conditions) == 1
    assert document_conditions[0].match.value == "doc-a"
