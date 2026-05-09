import os
import logging
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB vector store operations."""

    def __init__(
        self,
        collection_name: str = "documents",
        persist_directory: str = "./chroma_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model

        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info(f"Using HuggingFace embedding model: {embedding_model}")

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        self.vectorstore: Optional[Chroma] = None
        self._initialize_vectorstore()

    def _initialize_vectorstore(self) -> None:
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
            client=self.client,
        )
        logger.info(f"Vector store initialized with collection: {self.collection_name}")

    def add_documents(self, documents: List[Document]) -> List[str]:
        if not documents:
            raise ValueError("No documents provided")
        ids = self.vectorstore.add_documents(documents)
        logger.info(f"Added {len(documents)} documents to vector store")
        return ids

    def similarity_search(
        self, query: str, k: int = 5, filter_dict: Optional[dict] = None
    ) -> List[Document]:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        results = self.vectorstore.similarity_search(query=query, k=k, filter=filter_dict)
        logger.info(f"Found {len(results)} similar documents")
        return results

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter_dict: Optional[dict] = None
    ) -> List[tuple]:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        results = self.vectorstore.similarity_search_with_score(
            query=query, k=k, filter=filter_dict
        )
        logger.info(f"Found {len(results)} similar documents with scores")
        return results

    def get_collection_info(self) -> dict:
        try:
            collection = self.client.get_collection(self.collection_name)
            count = collection.count()
        except Exception:
            count = 0
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "embedding_model": self.embedding_model_name,
            "persist_directory": self.persist_directory,
        }

    def get_retriever(self, search_type: str = "similarity", search_kwargs: Optional[dict] = None):
        if search_kwargs is None:
            search_kwargs = {"k": 5}
        return self.vectorstore.as_retriever(
            search_type=search_type, search_kwargs=search_kwargs
        )

    def delete_collection(self) -> None:
        self.client.delete_collection(self.collection_name)
        self._initialize_vectorstore()
        logger.info(f"Deleted and recreated collection: {self.collection_name}")

    def update_documents(self, documents: List[Document], ids: List[str]) -> List[str]:
        if len(documents) != len(ids):
            raise ValueError("Number of documents and IDs must match")
        self.vectorstore.delete(ids=ids)
        return self.add_documents(documents)

    def reset_collection(self) -> None:
        self.delete_collection()
        logger.info("Collection reset successfully")
