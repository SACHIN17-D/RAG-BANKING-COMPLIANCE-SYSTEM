"""
===================================================================================
FILE: app.py
ROLE: FastAPI Backend for Loan Policy & Credit Risk RAG Assistant (Single Document)
===================================================================================
"""
import time
import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import config
from chroma_build.chroma_store import ChromaManager
from rag_chat import get_llm_response, get_llm_response_stream, sanitize_text

# Initialize FastAPI application
app = FastAPI(
    title="Loan Policy & Credit Risk RAG Assistant API",
    description="Clean, single-document RAG assistant with instant PDF replacement, 768-dim Nomic vector retrieval, and Groq LLM explanations.",
    version="3.1.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent State File
ACTIVE_STATE_FILE = config.DATA_DIR / "active_doc.json"
_chroma_manager: Optional[ChromaManager] = None
COLLECTION_NAME = "active_policy_document"


def get_chroma_manager() -> ChromaManager:
    global _chroma_manager
    if _chroma_manager is None:
        _chroma_manager = ChromaManager(collection_name=COLLECTION_NAME)
    return _chroma_manager


def get_active_document_info() -> Dict[str, Any]:
    """Reads or determines the current active policy document on disk."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if saved in active_doc.json
    if ACTIVE_STATE_FILE.exists():
        try:
            with open(ACTIVE_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                filename = data.get("filename", "")
                if filename and (config.DATA_DIR / filename).exists():
                    return data
        except Exception:
            pass

    # Default fallback: check for RBIC policy first, then FDIC manual, or any PDF
    preferred = ["RBIC_Loan_Compliance_Checking_Policy.pdf", "fdic_manual.pdf"]
    for p in preferred:
        if (config.DATA_DIR / p).exists():
            info = {"filename": p, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            save_active_document_info(info)
            return info

    for p in config.DATA_DIR.glob("*.pdf"):
        info = {"filename": p.name, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_active_document_info(info)
        return info

    info = {"filename": "No Document Uploaded", "updated_at": ""}
    return info


def save_active_document_info(info: Dict[str, Any]):
    """Saves the active document metadata to JSON."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)


import threading

def ensure_active_document_indexed():
    """Ensures the active policy document is loaded into ChromaDB upon startup."""
    try:
        info = get_active_document_info()
        filename = info.get("filename")
        if not filename or filename == "No Document Uploaded":
            return

        doc_path = config.DATA_DIR / filename
        if not doc_path.exists():
            return

        manager = get_chroma_manager()
        manager.set_collection(COLLECTION_NAME)
        if not manager.is_db_populated():
            print(f"[Startup] Indexing active policy document '{filename}' into ChromaDB...", flush=True)
            manager.load_and_index_documents(pdf_path=doc_path, force_reload=False)
            print(f"[Startup] Completed indexing '{filename}' into ChromaDB.", flush=True)
    except Exception as e:
        print(f"[Startup Warning] Background indexing encountered: {e}", flush=True)


# =====================================================================
# PYDANTIC SCHEMAS
# =====================================================================
class ChatRequest(BaseModel):
    query: str = Field(..., description="User loan query or policy question", min_length=1)
    top_k: Optional[int] = Field(default=4, description="Number of chunks to retrieve", ge=1, le=20)
    min_score: Optional[float] = Field(default=0.20, description="Minimum similarity threshold", ge=0.0, le=1.0)
    history: Optional[List[Dict[str, Any]]] = Field(default=[], description="Prior dialogue turns")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Keyword query", min_length=1)
    top_k: Optional[int] = Field(default=10, ge=1, le=30)
    min_score: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)


# =====================================================================
# API ENDPOINTS: STATUS & ACTIVE DOCUMENT
# =====================================================================
@app.get("/api/status")
async def get_system_status():
    """Returns system status, active policy document name, chunk count, and model settings."""
    info = get_active_document_info()
    filename = info.get("filename", "No Document Uploaded")
    
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)
    count = manager.collection.count() if manager.collection else 0
    has_groq = bool(os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY)

    return {
        "status": "online",
        "active_document": filename,
        "total_chunks": count,
        "is_populated": count > 0,
        "embedding_model": config.EMBEDDING_MODEL_NAME,
        "embedding_dimension": config.EMBEDDING_DIM,
        "llm_model": config.LLM_MODEL,
        "has_groq_api_key": has_groq,
        "default_top_k": config.DEFAULT_TOP_K,
        "default_min_score": config.DEFAULT_MIN_SCORE
    }


# =====================================================================
# API ENDPOINTS: UPLOAD & REPLACE DOCUMENT
# =====================================================================
@app.post("/api/upload")
async def upload_and_replace_pdf(file: UploadFile = File(...)):
    """
    Uploads a new policy PDF to replace the previous one, re-indexes ChromaDB,
    and updates the active policy document immediately.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in (".", "_", "-")).strip()
    if not safe_filename:
        safe_filename = f"policy_{int(time.time())}.pdf"

    target_path = config.DATA_DIR / safe_filename

    # Save uploaded PDF to data/
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Replace collection in ChromaDB and re-index
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)

    try:
        manager.load_and_index_documents(pdf_path=target_path, force_reload=True)
        count = manager.collection.count() if manager.collection else 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}")

    info = {
        "filename": safe_filename,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_active_document_info(info)

    return {
        "status": "success",
        "message": f"Successfully replaced policy document with '{safe_filename}' ({count} chunks indexed).",
        "active_document": safe_filename,
        "total_chunks": count
    }


# =====================================================================
# API ENDPOINTS: RAG CHAT & STREAMING
# =====================================================================
@app.post("/api/chat/stream")
async def handle_rag_chat_stream(req: ChatRequest):
    """Streams LLM tokens token-by-token using Server-Sent Events (SSE)."""
    info = get_active_document_info()
    filename = info.get("filename", "No Document")

    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)

    top_k = req.top_k if req.top_k is not None else config.DEFAULT_TOP_K
    min_score = req.min_score if req.min_score is not None else config.DEFAULT_MIN_SCORE
    start_time = time.time()

    if not manager.collection or manager.collection.count() == 0:
        async def empty_stream():
            msg = f"⚠️ **No Chunks Indexed**: No policy document is currently indexed. Please upload a PDF policy manual."
            yield f"data: {json.dumps({'type': 'sources', 'sources': [], 'source_count': 0})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'timing': {'total_ms': 0}})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    retrieval_start = time.time()
    try:
        results = manager.search(query=req.query, n_results=top_k, min_score=min_score)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")
    retrieval_ms = round((time.time() - retrieval_start) * 1000, 2)

    async def sse_generator():
        # Event 1: Sources metadata
        yield f"data: {json.dumps({'type': 'sources', 'query': req.query, 'sources': results, 'source_count': len(results), 'retrieval_ms': retrieval_ms})}\n\n"

        # Event 2: Stream tokens from Groq
        gen_start = time.time()
        for token in get_llm_response_stream(req.query, results, conversation_history=req.history):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        gen_ms = round((time.time() - gen_start) * 1000, 2)
        total_ms = round((time.time() - start_time) * 1000, 2)

        # Event 3: Done timing
        yield f"data: {json.dumps({'type': 'done', 'timing': {'retrieval_ms': retrieval_ms, 'generation_ms': gen_ms, 'total_ms': total_ms}})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/api/chat")
async def handle_rag_chat(req: ChatRequest):
    """Non-streaming RAG completion returning full answer, sources, and timing."""
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)

    top_k = req.top_k if req.top_k is not None else config.DEFAULT_TOP_K
    min_score = req.min_score if req.min_score is not None else config.DEFAULT_MIN_SCORE
    start_time = time.time()

    if not manager.collection or manager.collection.count() == 0:
        return {
            "query": req.query,
            "answer": "⚠️ No policy document is currently indexed. Please upload a PDF policy manual.",
            "sources": [],
            "source_count": 0,
            "timing": {"retrieval_ms": 0, "generation_ms": 0, "total_ms": 0}
        }

    retrieval_start = time.time()
    results = manager.search(query=req.query, n_results=top_k, min_score=min_score)
    retrieval_ms = round((time.time() - retrieval_start) * 1000, 2)

    gen_start = time.time()
    answer = get_llm_response(req.query, results, conversation_history=req.history)
    gen_ms = round((time.time() - gen_start) * 1000, 2)
    total_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "query": req.query,
        "answer": answer,
        "sources": results,
        "source_count": len(results),
        "timing": {
            "retrieval_ms": retrieval_ms,
            "generation_ms": gen_ms,
            "total_ms": total_ms
        }
    }


@app.post("/api/search")
async def handle_vector_search(req: SearchRequest):
    """Raw Cosine similarity vector search on the active policy document."""
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)

    start_time = time.time()
    if not manager.collection or manager.collection.count() == 0:
        results = []
    else:
        results = manager.search(query=req.query, n_results=req.top_k or 10, min_score=req.min_score or 0.0)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    info = get_active_document_info()
    return {
        "query": req.query,
        "document": info.get("filename", "Unknown"),
        "results": results,
        "count": len(results),
        "search_time_ms": elapsed_ms
    }


@app.post("/api/reindex")
async def reindex_active_document():
    """Forces re-chunking and re-indexing of the current active policy PDF."""
    info = get_active_document_info()
    filename = info.get("filename")
    if not filename or filename == "No Document Uploaded":
        raise HTTPException(status_code=400, detail="No active document to re-index.")

    target_path = config.DATA_DIR / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Document file '{filename}' not found.")

    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)
    manager.load_and_index_documents(pdf_path=target_path, force_reload=True)
    count = manager.collection.count() if manager.collection else 0

    return {
        "status": "success",
        "message": f"Successfully re-indexed '{filename}' ({count} chunks).",
        "active_document": filename,
        "total_chunks": count
    }


# =====================================================================
# STATIC FILES & ROOT ROUTE
# =====================================================================
static_dir = config.BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    index_file = config.BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "running", "message": "Loan Policy RAG Assistant API is online."})


@app.on_event("startup")
def startup_event():
    # Run heavy vector initialization in a background thread so Uvicorn can immediately
    # bind to the port ($PORT on Render/Cloud) without failing healthcheck/port scans.
    threading.Thread(target=ensure_active_document_indexed, daemon=True).start()
