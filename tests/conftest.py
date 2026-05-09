import os
import tempfile
import pytest


@pytest.fixture
def sample_txt_file():
    """Create a temporary TXT file with known content."""
    content = (
        "IntelliDoc AI is a retrieval-augmented generation system.\n"
        "It supports PDF and TXT document ingestion.\n"
        "Users can ask questions and get AI-generated answers backed by sources.\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_text():
    return (
        "IntelliDoc AI is a retrieval-augmented generation system. "
        "It uses ChromaDB for vector storage and Google Gemini for answer generation. "
        "Documents are chunked using LangChain's RecursiveCharacterTextSplitter. "
        "The system evaluates answer quality using TruLens metrics including "
        "answer relevance, context relevance, and groundedness."
    )
