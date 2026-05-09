import logging
import os
from typing import Any

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEvaluator:
    """
    RAG evaluation using RAGAS framework with Google Gemini.

    Metrics (no ground-truth required):
      - faithfulness       : are claims in the answer supported by the retrieved context?
      - answer_relevancy   : does the answer actually address the question?
      - context_precision  : is the retrieved context relevant to the question?
    """

    METRICS_INFO = {
        "faithfulness": (
            "Fraction of claims in the answer that are supported by the retrieved context. "
            "High score = no hallucination."
        ),
        "answer_relevancy": (
            "How well the answer addresses the question. "
            "High score = on-topic, complete response."
        ),
    }

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.ragas_available = False
        self._setup_ragas()

    def _setup_ragas(self) -> None:
        try:
            # Use legacy singletons — they accept LangchainLLMWrapper (collections-style
            # metrics only accept InstructorLLM and are not compatible with Langchain wrappers).
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_huggingface import HuggingFaceEmbeddings
            from ragas.embeddings import LangchainEmbeddingsWrapper
            from ragas.llms import LangchainLLMWrapper
            from ragas.metrics import answer_relevancy, faithfulness

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=self.api_key,
                temperature=0.0,
            )
            # Use local HuggingFace embeddings — avoids external network calls and reuses
            # the same model already loaded by VectorStore.
            hf_emb = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )

            wrapped_llm = LangchainLLMWrapper(llm)
            wrapped_emb = LangchainEmbeddingsWrapper(hf_emb)

            faithfulness.llm = wrapped_llm
            answer_relevancy.llm = wrapped_llm
            answer_relevancy.embeddings = wrapped_emb

            self._metrics = [faithfulness, answer_relevancy]
            self._metric_names = ["faithfulness", "answer_relevancy"]
            self.ragas_available = True
            logger.info("RAGAS evaluator initialised (Gemini LLM + HuggingFace embeddings)")

        except Exception as e:
            logger.warning(f"RAGAS setup failed, falling back to heuristic evaluation: {e}")
            self._metrics = []
            self._metric_names = []

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate_rag_system(
        self,
        questions: list[str],
        answers: list[str],
        contexts: list[list[str]],
        ground_truths: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate a RAG system using RAGAS metrics."""
        if self.ragas_available:
            return self._ragas_evaluate(questions, answers, contexts)
        return self._heuristic_evaluate(questions, answers, contexts)

    def evaluate_single_qa(
        self,
        question: str,
        answer: str,
        context: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a single question-answer pair."""
        return self.evaluate_rag_system(
            questions=[question],
            answers=[answer],
            contexts=[context],
            ground_truths=[ground_truth] if ground_truth else None,
        )

    def batch_evaluate(self, qa_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate a list of QA results produced by QAChain."""
        questions, answers, contexts = [], [], []
        for result in qa_results:
            questions.append(result.get("question", ""))
            answers.append(result.get("answer", ""))
            ctx = result.get("context_used", "")
            if isinstance(ctx, list):
                contexts.append(ctx)
            elif isinstance(ctx, str) and ctx:
                contexts.append([ctx])
            else:
                contexts.append([""])
        return self.evaluate_rag_system(questions, answers, contexts)

    def generate_evaluation_report(self, results: dict[str, Any]) -> str:
        """Return a human-readable evaluation report string."""
        if "error" in results:
            return f"Evaluation Error: {results['error']}"

        lines = ["RAGAS Evaluation Report", "=" * 40, ""]

        if "overall_scores" in results:
            lines.append("Scores:")
            for metric, score in results["overall_scores"].items():
                bar = "█" * int(score * 20)
                lines.append(f"  {metric:<22} {score:.3f}  {bar}")
            lines.append("")

        if "summary" in results:
            lines.append("Summary:")
            for k, v in results["summary"].items():
                lines.append(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
            lines.append("")

        if results.get("engine") == "heuristic":
            lines.append("Note: RAGAS not available; scores are heuristic estimates.")

        return "\n".join(lines)

    def get_metrics_info(self) -> dict[str, Any]:
        return {
            "available_metrics": list(self.METRICS_INFO.keys()),
            "descriptions": self.METRICS_INFO,
            "ragas_available": self.ragas_available,
            "engine": "ragas" if self.ragas_available else "heuristic",
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ragas_evaluate(
        self,
        questions: list[str],
        answers: list[str],
        contexts: list[list[str]],
    ) -> dict[str, Any]:
        try:
            from datasets import Dataset
            from ragas import evaluate

            dataset = Dataset.from_dict(
                {
                    "question": questions,
                    "answer": answers,
                    "contexts": contexts,
                }
            )

            logger.info(f"Running RAGAS evaluation on {len(questions)} sample(s)...")
            result = evaluate(dataset, metrics=self._metrics)
            scores_df: pd.DataFrame = result.to_pandas()

            overall: dict[str, float] = {}
            for name in self._metric_names:
                if name in scores_df.columns:
                    mean_val = scores_df[name].mean()
                    # NaN can occur when a metric cannot be computed (e.g. empty context).
                    overall[name] = 0.0 if (mean_val != mean_val) else float(mean_val)

            all_scores = list(overall.values())
            return {
                "overall_scores": overall,
                "individual_scores": scores_df[self._metric_names].to_dict(orient="records"),
                "summary": {
                    "average_score": float(np.mean(all_scores)),
                    "min_score": float(np.min(all_scores)),
                    "max_score": float(np.max(all_scores)),
                    "total_questions": len(questions),
                },
                "engine": "ragas",
            }

        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return self._heuristic_evaluate(questions, answers, contexts)

    def _heuristic_evaluate(
        self,
        questions: list[str],
        answers: list[str],
        contexts: list[list[str]],
    ) -> dict[str, Any]:
        """Lightweight heuristic fallback — no LLM calls required."""
        logger.info("Using heuristic evaluation fallback")

        def _word_overlap(a: str, b: str) -> float:
            wa, wb = set(a.lower().split()), set(b.lower().split())
            if not wa or not wb:
                return 0.0
            return len(wa & wb) / len(wa | wb)

        faithfulness_scores, relevancy_scores = [], []

        for q, a, ctx_list in zip(questions, answers, contexts):
            ctx_text = " ".join(ctx_list)
            faithfulness_scores.append(_word_overlap(a, ctx_text))
            relevancy_scores.append(_word_overlap(a, q))

        overall = {
            "faithfulness": float(np.mean(faithfulness_scores)),
            "answer_relevancy": float(np.mean(relevancy_scores)),
        }
        all_scores = list(overall.values())

        return {
            "overall_scores": overall,
            "summary": {
                "average_score": float(np.mean(all_scores)),
                "min_score": float(np.min(all_scores)),
                "max_score": float(np.max(all_scores)),
                "total_questions": len(questions),
            },
            "engine": "heuristic",
        }
