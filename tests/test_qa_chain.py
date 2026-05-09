from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from utils.qa_chain import QAChain


@pytest.fixture
def mock_qa_chain():
    with patch("utils.qa_chain.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        chain = QAChain(api_key="fake-api-key", model_name="gemini-2.5-flash")
        chain.client = mock_client
        yield chain, mock_client


def _make_response(text: str):
    response = MagicMock()
    response.text = text
    return response


def test_generate_answer_success(mock_qa_chain):
    chain, client = mock_qa_chain
    client.models.generate_content.return_value = _make_response("The answer is 42.")

    result = chain.generate_answer(
        question="What is the answer?",
        context="The answer is 42.",
    )

    assert result["success"] is True
    assert result["answer"] == "The answer is 42."
    assert result["question"] == "What is the answer?"


def test_generate_answer_empty_question(mock_qa_chain):
    chain, _ = mock_qa_chain
    result = chain.generate_answer(question="  ", context="some context")
    assert result["success"] is False
    assert "empty" in result["answer"].lower() or "error" in result["answer"].lower()


def test_generate_answer_empty_context(mock_qa_chain):
    chain, _ = mock_qa_chain
    result = chain.generate_answer(question="What?", context="  ")
    assert "error" in result
    assert result.get("success") is None or result.get("answer")


def test_answer_with_sources_no_documents(mock_qa_chain):
    chain, _ = mock_qa_chain
    result = chain.answer_with_sources(question="What?", documents=[])
    assert result["success"] is False
    assert result["sources"] == []


def test_answer_with_sources_success(mock_qa_chain):
    chain, client = mock_qa_chain
    client.models.generate_content.return_value = _make_response("Answer from doc.")

    docs = [
        Document(page_content="Content of document one.", metadata={"filename": "doc1.txt"}),
        Document(page_content="Content of document two.", metadata={"filename": "doc2.txt"}),
    ]
    result = chain.answer_with_sources(question="What does doc say?", documents=docs)

    assert result["success"] is True
    assert len(result["sources"]) == 2
    assert result["sources"][0]["source_id"] == 1
    assert result["num_sources"] == 2


def test_validate_answer_quality_good(mock_qa_chain):
    chain, _ = mock_qa_chain
    answer = "IntelliDoc AI uses ChromaDB for vector storage and retrieval."
    question = "What does IntelliDoc use for vector storage?"
    context = "IntelliDoc AI uses ChromaDB for vector storage and retrieval from documents."

    metrics = chain.validate_answer_quality(answer, question, context)
    assert "quality_score" in metrics
    assert "has_answer" in metrics
    assert metrics["has_answer"] is True


def test_batch_qa(mock_qa_chain):
    chain, client = mock_qa_chain
    client.models.generate_content.return_value = _make_response("Batch answer.")

    questions = ["Q1?", "Q2?", "Q3?"]
    results = chain.batch_qa(questions, context="Some context.")

    assert len(results) == 3
    for r in results:
        assert "answer" in r
        assert "question" in r
