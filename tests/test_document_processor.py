import os
import pytest
from utils.document_processor import DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor(chunk_size=200, chunk_overlap=20)


def test_load_txt(processor, sample_txt_file):
    text = processor.load_txt(sample_txt_file)
    assert isinstance(text, str)
    assert len(text) > 0
    assert "IntelliDoc" in text


def test_load_document_txt(processor, sample_txt_file):
    text = processor.load_document(sample_txt_file)
    assert isinstance(text, str)
    assert len(text) > 0


def test_load_document_unsupported_extension(processor, tmp_path):
    bad_file = tmp_path / "test.xyz"
    bad_file.write_text("content")
    with pytest.raises(ValueError, match="Unsupported file format"):
        processor.load_document(str(bad_file))


def test_chunk_text_basic(processor, sample_text):
    docs = processor.chunk_text(sample_text)
    assert len(docs) >= 1
    for doc in docs:
        assert doc.page_content
        assert "chunk_id" in doc.metadata


def test_chunk_text_with_metadata(processor, sample_text):
    metadata = {"filename": "test.txt", "source": "unit-test"}
    docs = processor.chunk_text(sample_text, metadata=metadata)
    for doc in docs:
        assert doc.metadata["filename"] == "test.txt"
        assert doc.metadata["source"] == "unit-test"


def test_chunk_text_empty_raises(processor):
    with pytest.raises(ValueError, match="Cannot chunk empty text"):
        processor.chunk_text("   ")


def test_chunk_text_overlap_respected(processor, sample_text):
    docs = processor.chunk_text(sample_text)
    for doc in docs:
        assert len(doc.page_content) <= processor.chunk_size + 50  # small tolerance


def test_get_document_stats(processor, sample_text):
    docs = processor.chunk_text(sample_text)
    stats = processor.get_document_stats(docs)
    assert stats["total_chunks"] == len(docs)
    assert stats["total_characters"] > 0
    assert stats["total_words"] > 0
    assert stats["average_chunk_size"] > 0


def test_get_document_stats_empty():
    processor = DocumentProcessor()
    stats = processor.get_document_stats([])
    assert stats == {}


def test_process_document(processor, sample_txt_file):
    docs = processor.process_document(sample_txt_file)
    assert len(docs) >= 1
    assert docs[0].metadata["filename"] is not None
