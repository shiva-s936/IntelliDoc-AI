import logging
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from utils.config import Config
from utils.document_processor import DocumentProcessor
from utils.evaluation import RAGEvaluator
from utils.qa_chain import QAChain
from utils.retriever import AdvancedRetriever
from utils.vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global components
vector_store: VectorStore | None = None
retriever: AdvancedRetriever | None = None
qa_chain: QAChain | None = None
document_processor: DocumentProcessor | None = None
evaluator: RAGEvaluator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG components on startup, clean up on shutdown."""
    global vector_store, retriever, qa_chain, document_processor, evaluator

    logger.info("Initializing IntelliDoc AI components...")

    api_keys = Config.validate_api_keys()
    if not api_keys["gemini"]:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    vector_store = VectorStore(
        collection_name=Config.COLLECTION_NAME,
        persist_directory=Config.PERSIST_DIRECTORY,
        embedding_model=Config.EMBEDDING_MODEL,
    )
    qa_chain = QAChain(api_key=Config.GEMINI_API_KEY, model_name=Config.GEMINI_MODEL)
    retriever = AdvancedRetriever(vector_store)
    document_processor = DocumentProcessor(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
    )
    evaluator = RAGEvaluator()

    logger.info("IntelliDoc AI initialized successfully!")
    yield
    logger.info("IntelliDoc AI shutting down.")


app = FastAPI(
    title="IntelliDoc AI - Enterprise RAG API",
    description="Production-ready RAG system with document processing and intelligent Q&A capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ──────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    top_k: int | None = 5
    similarity_threshold: float | None = 0.1
    temperature: float | None = 0.3
    include_sources: bool | None = True


class QuestionResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]] | None = None
    question: str
    success: bool
    timestamp: str
    processing_time: float | None = None
    context_used: str | None = None


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: str
    chunks_created: int
    success: bool
    filename: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    api_keys_configured: dict[str, bool]
    vector_store_status: str
    document_count: int
    timestamp: str


class EvaluationRequest(BaseModel):
    questions: list[str]
    answers: list[str]
    contexts: list[str]


class EvaluationResponse(BaseModel):
    overall_scores: dict[str, float]
    summary: dict[str, Any]
    success: bool
    timestamp: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", response_model=dict[str, str])
async def root():
    return {
        "message": "Welcome to IntelliDoc AI - Enterprise RAG API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        api_keys = Config.validate_api_keys()
        collection_info = vector_store.get_collection_info()
        return HealthResponse(
            status="healthy",
            api_keys_configured=api_keys,
            vector_store_status="connected",
            document_count=collection_info.get("document_count", 0),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_extensions = [".pdf", ".txt"]
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {allowed_extensions}",
        )

    tmp_file_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        text = document_processor.load_document(tmp_file_path)
        documents = document_processor.chunk_text(
            text,
            metadata={"filename": file.filename, "upload_time": datetime.now().isoformat()},
        )

        document_ids = vector_store.add_documents(documents)
        background_tasks.add_task(os.unlink, tmp_file_path)

        return DocumentUploadResponse(
            message="Document uploaded and processed successfully",
            document_id=document_ids[0] if document_ids else "unknown",
            chunks_created=len(documents),
            success=True,
            filename=file.filename,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        if tmp_file_path:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@app.post("/questions/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        start_time = datetime.now()

        documents = retriever.retrieve_documents(
            query=request.question,
            k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        if not documents:
            return QuestionResponse(
                answer="I couldn't find any relevant information to answer your question.",
                sources=[],
                question=request.question,
                success=True,
                timestamp=datetime.now().isoformat(),
                processing_time=(datetime.now() - start_time).total_seconds(),
            )

        if request.include_sources:
            result = qa_chain.answer_with_sources(
                question=request.question,
                documents=documents,
                temperature=request.temperature,
            )
        else:
            context = retriever.get_relevant_context(
                query=request.question,
                k=request.top_k,
                similarity_threshold=request.similarity_threshold,
            )
            result = qa_chain.generate_answer(
                question=request.question,
                context=context,
                temperature=request.temperature,
            )

        processing_time = (datetime.now() - start_time).total_seconds()

        return QuestionResponse(
            answer=result.get("answer", "Unable to generate answer"),
            sources=result.get("sources", []) if request.include_sources else None,
            question=request.question,
            success=result.get("success", False),
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time,
            context_used=result.get("context_used", ""),
        )

    except Exception as e:
        logger.error(f"Question processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")


@app.post("/evaluation/run", response_model=EvaluationResponse)
async def run_evaluation(request: EvaluationRequest):
    if not (request.questions and request.answers and request.contexts):
        raise HTTPException(status_code=400, detail="Questions, answers, and contexts are required")

    if not len(request.questions) == len(request.answers) == len(request.contexts):
        raise HTTPException(
            status_code=400,
            detail="Questions, answers, and contexts must have the same length",
        )

    try:
        qa_pairs = [
            {"question": q, "answer": a, "context": c, "success": True}
            for q, a, c in zip(request.questions, request.answers, request.contexts)
        ]

        results = evaluator.batch_evaluate(qa_pairs)

        if "error" in results:
            raise HTTPException(status_code=500, detail=results["error"])

        return EvaluationResponse(
            overall_scores=results.get("overall_scores", {}),
            summary=results.get("summary", {}),
            success=True,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.get("/documents/list")
async def list_documents():
    try:
        collection = vector_store.client.get_collection(vector_store.collection_name)
        data = collection.get(include=["metadatas"])
        seen: set[str] = set()
        docs = []
        for meta in (data.get("metadatas") or []):
            name = (meta or {}).get("filename", "unknown")
            if name not in seen:
                seen.add(name)
                docs.append({"filename": name})
        return JSONResponse(content={"documents": docs, "total": len(docs)})
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/info")
async def get_document_info():
    try:
        collection_info = vector_store.get_collection_info()
        return JSONResponse(content={
            "success": True,
            "info": collection_info,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Failed to get document info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {str(e)}")


@app.delete("/documents/clear")
async def clear_documents():
    try:
        vector_store.reset_collection()
        return JSONResponse(content={
            "message": "All documents cleared successfully",
            "success": True,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Failed to clear documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear documents: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
