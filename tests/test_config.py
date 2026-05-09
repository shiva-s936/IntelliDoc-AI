import os
import pytest
from unittest.mock import patch
from utils.config import Config


def test_validate_api_keys_missing():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
        # Re-read class attributes to reflect env patch
        Config.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        Config.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        result = Config.validate_api_keys()
    assert result["gemini"] is False
    assert result["openai"] is False


def test_validate_api_keys_present():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key", "OPENAI_API_KEY": "fake-key"}):
        Config.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        Config.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        result = Config.validate_api_keys()
    assert result["gemini"] is True
    assert result["openai"] is True


def test_chunking_config():
    config = Config.get_chunking_config()
    assert "chunk_size" in config
    assert "chunk_overlap" in config
    assert config["chunk_size"] > 0
    assert config["chunk_overlap"] >= 0
    assert config["chunk_overlap"] < config["chunk_size"]


def test_retrieval_config():
    config = Config.get_retrieval_config()
    assert "top_k" in config
    assert "similarity_threshold" in config
    assert config["top_k"] > 0
    assert 0.0 <= config["similarity_threshold"] <= 1.0


def test_default_model_names():
    assert "gemini" in Config.GEMINI_MODEL.lower()
    assert "sentence-transformers" in Config.EMBEDDING_MODEL
