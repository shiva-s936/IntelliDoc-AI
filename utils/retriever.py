import logging
from typing import Any

from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedRetriever:
    """
    Retriever with MMR diversity re-ranking and similarity threshold filtering.

    ChromaDB returns L2 distance for normalized embeddings.
    Relationship to cosine similarity: cosine_sim ≈ 1 - distance / 2
    So similarity_threshold → distance_threshold = 2 * (1 - similarity_threshold).
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store
        logger.info("Retrievers setup successfully")

    # ── Public API ────────────────────────────────────────────────────────────

    def retrieve_documents(
        self,
        query: str,
        k: int = 5,
        similarity_threshold: float = 0.3,
        filters: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Retrieve relevant documents using MMR + similarity threshold."""
        if not query.strip():
            raise ValueError("Query cannot be empty")

        try:
            fetch_k = max(k * 4, 20)

            # Step 1 — threshold filter using scored similarity search
            results_with_scores = self.vector_store.similarity_search_with_score(
                query=query,
                k=fetch_k,
                filter_dict=filters,
            )

            # Convert similarity threshold → L2 distance threshold
            distance_threshold = 2.0 * (1.0 - similarity_threshold)
            passing = {
                doc.page_content
                for doc, score in results_with_scores
                if score <= distance_threshold
            }

            if not passing:
                logger.info("No documents passed similarity_threshold=%.2f", similarity_threshold)
                return []

            # Step 2 — MMR re-ranking over the same candidate pool for diversity
            mmr_docs = self.vector_store.vectorstore.max_marginal_relevance_search(
                query=query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=0.7,  # 0.7 = relevance-weighted; 0.5 = max diversity
                filter=filters,
            )

            # Keep only chunks that also passed the threshold filter
            diverse = [d for d in mmr_docs if d.page_content in passing]

            # Fall back to score-sorted if MMR discarded too many
            if len(diverse) < min(k, len(passing)):
                fallback = [doc for doc, _ in sorted(results_with_scores, key=lambda x: x[1])
                            if doc.page_content in passing]
                diverse = fallback

            result = diverse[:k]
            logger.info(
                "Retrieved %d documents (MMR + threshold=%.2f)", len(result), similarity_threshold
            )
            return result

        except Exception as e:
            logger.error("Error retrieving documents: %s", e)
            raise

    def get_relevant_context(
        self,
        query: str,
        k: int = 5,
        similarity_threshold: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """Return retrieved chunks joined as a single context string."""
        documents = self.retrieve_documents(
            query=query,
            k=k,
            similarity_threshold=similarity_threshold,
        )

        if not documents:
            return "No relevant context found."

        context_parts: list[str] = []
        total_tokens = 0

        for i, doc in enumerate(documents):
            content = doc.page_content.strip()
            estimated_tokens = len(content) // 4

            if total_tokens + estimated_tokens <= max_tokens:
                context_parts.append(f"Source {i + 1}:\n{content}")
                total_tokens += estimated_tokens
            else:
                remaining_chars = (max_tokens - total_tokens) * 4
                if remaining_chars > 100:
                    context_parts.append(f"Source {i + 1}:\n{content[:remaining_chars]}...")
                break

        logger.info(
            "Generated context from %d sources (~%d tokens)", len(context_parts), total_tokens
        )
        return "\n\n".join(context_parts)

    def get_document_metadata(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return metadata for the top-k retrieved documents."""
        documents = self.retrieve_documents(query, k)
        metadata_list = []
        for doc in documents:
            meta = doc.metadata.copy()
            meta["content_preview"] = (
                doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            )
            meta["content_length"] = len(doc.page_content)
            metadata_list.append(meta)
        return metadata_list

    def search_with_scores_and_metadata(
        self,
        query: str,
        k: int = 5,
        similarity_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search and return documents with relevance scores and metadata."""
        results_with_scores = self.vector_store.similarity_search_with_score(
            query=query,
            k=k * 2,
        )

        distance_threshold = 2.0 * (1.0 - similarity_threshold)
        filtered = []
        for doc, score in results_with_scores:
            if score <= distance_threshold:
                # cosine_sim = 1 - distance/2 for L2-normalized vectors
                cosine_sim = max(0.0, 1.0 - score / 2.0)
                filtered.append(
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": cosine_sim,
                        "content_preview": (
                            doc.page_content[:200] + "..."
                            if len(doc.page_content) > 200
                            else doc.page_content
                        ),
                    }
                )

        filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
        return filtered[:k]
