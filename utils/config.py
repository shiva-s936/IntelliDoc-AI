import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for IntelliDoc AI. Values are read from environment variables."""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Model configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Chunking parameters
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Vector store
    COLLECTION_NAME: str = "documents"
    PERSIST_DIRECTORY: str = "./chroma_db"

    # Retrieval
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.7

    # Evaluation metrics
    TRULENS_METRICS: list = ["answer_relevance", "context_relevance", "groundedness", "context_recall"]

    @classmethod
    def validate_api_keys(cls) -> Dict[str, bool]:
        return {
            "gemini": bool(cls.GEMINI_API_KEY),
            "openai": bool(cls.OPENAI_API_KEY),
        }

    @classmethod
    def get_chunking_config(cls) -> Dict[str, Any]:
        return {"chunk_size": cls.CHUNK_SIZE, "chunk_overlap": cls.CHUNK_OVERLAP}

    @classmethod
    def get_retrieval_config(cls) -> Dict[str, Any]:
        return {"top_k": cls.TOP_K, "similarity_threshold": cls.SIMILARITY_THRESHOLD}
