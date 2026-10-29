"""
===================================================================================
FILE: app.py
ROLE: FastAPI Backend for Loan Policy & Credit Risk RAG Assistant (Single Document)
===================================================================================
"""
import time
import os
import json
import base64
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, Field

import config

# Fix read-only filesystem issues on Vercel/serverless environments
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    tmp = tempfile.gettempdir()
    os.environ["HOME"] = tmp
    os.environ["USERPROFILE"] = tmp
    os.environ["XDG_CACHE_HOME"] = str(Path(tmp) / ".cache")
    os.environ["HF_HOME"] = str(Path(tmp) / ".cache" / "huggingface")

try:
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
    safe_onnx_dir = Path(tempfile.gettempdir()) / ".cache" / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    model_file = safe_onnx_dir / "onnx" / "model.onnx"
    if model_file.exists() and model_file.stat().st_size < 85000000:
        import shutil
        shutil.rmtree(safe_onnx_dir, ignore_errors=True)
    safe_onnx_dir.mkdir(parents=True, exist_ok=True)
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = safe_onnx_dir
except Exception:
    pass

from chroma_build.chroma_store import ChromaManager
from rag_chat import get_llm_response, get_llm_response_stream, sanitize_text

# Initialize FastAPI application
app = FastAPI(
    title="Loan Policy & Credit Risk RAG Assistant API",
    description="Clean, single-document RAG assistant with instant PDF replacement, 768-dim Nomic vector retrieval, and Groq LLM explanations.",
    version="3.1.0",
    redirect_slashes=False
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
ACTIVE_STATE_FILE = (Path(tempfile.gettempdir()) / "active_doc.json") if (config.is_vercel or config.is_readonly_env) else config.DATA_DIR / "active_doc.json"
_chroma_manager: Optional[ChromaManager] = None
COLLECTION_NAME = "active_policy_document"


def get_chroma_manager() -> ChromaManager:
    global _chroma_manager
    if _chroma_manager is None:
        _chroma_manager = ChromaManager(collection_name=COLLECTION_NAME)
    return _chroma_manager


def get_active_document_info() -> Dict[str, Any]:
    """Reads or determines the current active policy document on disk."""
    candidates = [
        Path(tempfile.gettempdir()) / "active_doc.json",
        ACTIVE_STATE_FILE,
        config.DATA_DIR / "active_doc.json"
    ]

    # Check if saved in active_doc.json
    for active_file in candidates:
        if active_file.exists():
            try:
                with open(active_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    filename = data.get("filename", "")
                    if filename and (
                        (config.DATA_DIR / filename).exists()
                        or ((Path(tempfile.gettempdir()) / "data") / filename).exists()
                    ):
                        return data
            except Exception:
                pass

    # Default fallback: check for 154MD.pdf (RBI Master Direction) first, then RBIC, FDIC
    preferred = ["154MD.pdf", "RBIC_Loan_Compliance_Checking_Policy.pdf", "fdic_manual.pdf"]
    for p in preferred:
        if (config.DATA_DIR / p).exists():
            info = {"filename": p, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            try:
                save_active_document_info(info)
            except Exception:
                pass
            return info

    for p in config.DATA_DIR.glob("*.pdf"):
        info = {"filename": p.name, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        try:
            save_active_document_info(info)
        except Exception:
            pass
        return info

    info = {"filename": "No Document Uploaded", "updated_at": ""}
    return info


def save_active_document_info(info: Dict[str, Any]):
    """Saves the active document metadata to JSON."""
    if config.is_vercel or config.is_readonly_env or not config.is_dir_writable(config.DATA_DIR):
        active_file = Path(tempfile.gettempdir()) / "active_doc.json"
    else:
        active_file = ACTIVE_STATE_FILE
    active_file.parent.mkdir(parents=True, exist_ok=True)
    with open(active_file, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)


import threading

def ensure_active_document_indexed():
    """Ensures the active policy document is loaded into ChromaDB upon startup."""
    try:
        if not config.is_vercel:
            # Give Uvicorn 1.5 seconds to bind to port and pass Render's port scan before indexing
            time.sleep(1.5)
        info = get_active_document_info()
        filename = info.get("filename")
        if not filename or filename == "No Document Uploaded":
            return

        doc_path = config.DATA_DIR / filename
        if not doc_path.exists():
            doc_path = (Path(tempfile.gettempdir()) / "data") / filename
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
        raise e


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
@app.get("/status")
async def get_system_status():
    """Returns system status, active policy document name, chunk count, and model settings."""
    info = get_active_document_info()
    filename = info.get("filename", "No Document Uploaded")
    
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)
    count = manager.collection.count() if manager.collection else 0
    index_error = None
    if count == 0 and config.is_vercel:
        try:
            ensure_active_document_indexed()
            count = manager.collection.count() if manager.collection else 0
        except Exception as e:
            import traceback
            index_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    has_groq = bool(os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY)

    bundled_db = config.BASE_DIR / "chroma_db"
    tmp_chroma = Path(tempfile.gettempdir()) / "chroma_db"
    diag = {
        "base_dir": str(config.BASE_DIR),
        "bundled_db_exists": bundled_db.exists(),
        "bundled_files": [p.name for p in bundled_db.iterdir()] if bundled_db.exists() else [],
        "tmp_chroma_exists": tmp_chroma.exists(),
        "tmp_chroma_files": [p.name for p in tmp_chroma.iterdir()] if tmp_chroma.exists() else [],
        "model_file_size": (Path(tempfile.gettempdir()) / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx" / "model.onnx").stat().st_size if (Path(tempfile.gettempdir()) / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx" / "model.onnx").exists() else 0
    }

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
        "default_min_score": config.DEFAULT_MIN_SCORE,
        "debug_error": index_error,
        "diag": diag
    }


# =====================================================================
# API ENDPOINTS: UPLOAD & REPLACE DOCUMENT
# =====================================================================
@app.post("/api/upload")
@app.post("/upload")
async def upload_and_replace_pdf(request: Request):
    """
    Uploads a new policy PDF to replace the previous one, re-indexes ChromaDB,
    and updates the active policy document immediately.
    Supports both JSON Base64 (100% reliable on Vercel/serverless) and multipart/form-data.
    """
    content_type = request.headers.get("content-type", "").lower()
    filename = ""
    content_bytes = b""

    # Read raw body first to allow flexible parsing
    try:
        raw_body = await request.body()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")

    # Method 1: JSON payload with Base64 content (Vercel serverless compatible)
    # Try JSON first regardless of content-type header (Vercel may strip/alter headers)
    if "multipart" not in content_type and "form" not in content_type:
        try:
            body = json.loads(raw_body)
            filename = body.get("filename", "").strip()
            raw_b64 = body.get("content_base64", "")
            if not raw_b64:
                raise HTTPException(status_code=400, detail="Missing 'content_base64' in upload payload.")
            content_bytes = base64.b64decode(raw_b64)
        except HTTPException:
            raise
        except Exception as e:
            # JSON parse failed — fall through to multipart attempt below
            content_type = "multipart/form-data"

    # Method 2: Standard multipart/form-data (cURL, Postman, non-serverless)
    if not content_bytes:
        try:
            form = await request.form()
            uploaded_file = form.get("file")
            if not uploaded_file:
                raise HTTPException(status_code=400, detail="No file field provided in form data.")
            filename = getattr(uploaded_file, "filename", "policy.pdf")
            content_bytes = await uploaded_file.read()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Form-data parsing error: {str(e)}")

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    if not content_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    if config.is_vercel or config.is_readonly_env or not config.is_dir_writable(config.DATA_DIR):
        target_dir = Path(tempfile.gettempdir()) / "data"
    else:
        target_dir = config.DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (".", "_", "-")).strip()
    if not safe_filename:
        safe_filename = f"policy_{int(time.time())}.pdf"

    target_path = target_dir / safe_filename

    # Save uploaded PDF to data/
    try:
        with open(target_path, "wb") as buffer:
            buffer.write(content_bytes)
    except Exception as e:
        print(f"[Upload Error] Failed to write file to {target_path}: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Replace collection in ChromaDB and re-index
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)

    try:
        manager.load_and_index_documents(pdf_path=target_path, force_reload=True)
        count = manager.collection.count() if manager.collection else 0
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Upload Error] Indexing failed: {e}", flush=True)
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


@app.get("/api/documents")
@app.get("/documents")
async def list_available_documents():
    """Lists all policy documents pre-installed or uploaded on the server."""
    dirs_to_check = [config.DATA_DIR, Path(tempfile.gettempdir()) / "data"]
    docs = []
    seen = set()
    for d in dirs_to_check:
        if d.exists():
            for p in d.glob("*.pdf"):
                if p.name not in seen:
                    seen.add(p.name)
                    docs.append({
                        "filename": p.name,
                        "size_bytes": p.stat().st_size,
                        "size_mb": round(p.stat().st_size / (1024 * 1024), 2)
                    })
    info = get_active_document_info()
    return {"active_document": info.get("filename"), "documents": docs}


@app.post("/api/select_document")
@app.post("/select_document")
async def select_policy_document(request: Request):
    """Switches the active policy document to one already present on the server."""
    body = await request.json()
    filename = body.get("filename", "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing 'filename'")

    target_path = config.DATA_DIR / filename
    if not target_path.exists():
        target_path = (Path(tempfile.gettempdir()) / "data") / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found on server.")

    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)
    try:
        manager.load_and_index_documents(pdf_path=target_path, force_reload=True)
        count = manager.collection.count() if manager.collection else 0
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Indexing error: {type(e).__name__}: {str(e)} | {tb[-400:]}")

    info = {"filename": filename, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    save_active_document_info(info)
    return {
        "status": "success",
        "message": f"Successfully activated '{filename}' ({count} chunks indexed).",
        "active_document": filename,
        "total_chunks": count
    }


# =====================================================================
# API ENDPOINTS: RAG CHAT & STREAMING
# =====================================================================
@app.post("/api/chat/stream")
@app.post("/chat/stream")
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
        ensure_active_document_indexed()

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
        ensure_active_document_indexed()

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
@app.post("/search")
async def handle_vector_search(req: SearchRequest):
    """Raw Cosine similarity vector search on the active policy document."""
    manager = get_chroma_manager()
    manager.set_collection(COLLECTION_NAME)

    start_time = time.time()
    if not manager.collection or manager.collection.count() == 0:
        ensure_active_document_indexed()

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
@app.post("/reindex")
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
    try:
        manager.load_and_index_documents(pdf_path=target_path, force_reload=True)
        count = manager.collection.count() if manager.collection else 0
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Indexing error: {type(e).__name__}: {str(e)} | {tb[-400:]}")

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
    app.mount("/api/static", StaticFiles(directory=str(static_dir)), name="api_static")


@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    target = static_dir / file_path
    if not target.exists():
        target = config.BASE_DIR / "public" / "static" / file_path
    if target.exists() and target.is_file():
        media_type = "text/css" if file_path.endswith(".css") else ("application/javascript" if file_path.endswith(".js") else None)
        return FileResponse(target, media_type=media_type)
    raise HTTPException(status_code=404, detail="Static asset not found")


@app.get("/healthz")
@app.get("/health")
@app.get("/api/healthz")
async def health_check():
    """Health check endpoint for cloud hosting providers (Render, Railway, Vercel, etc.)."""
    return {"status": "ok", "app": "CrediSense AI Copilot"}


@app.get("/favicon.ico")
@app.get("/api/favicon.ico")
async def favicon():
    fav = config.BASE_DIR / "static" / "favicon.ico"
    if fav.exists():
        return FileResponse(fav)
    return Response(status_code=204)


@app.get("/api")
@app.get("/api/")
async def api_root():
    return {"status": "online", "message": "CrediSense API is running"}


@app.get("/")
@app.get("/index.html")
@app.get("/index")
async def root():
    index_file = config.BASE_DIR / "static" / "index.html"
    if not index_file.exists():
        index_file = config.BASE_DIR / "public" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "running", "message": "Loan Policy RAG Assistant API is online."})


@app.on_event("startup")
def startup_event():
    # Run heavy vector initialization in a background thread so Uvicorn can immediately
    # bind to the port ($PORT on Render/Cloud) without failing healthcheck/port scans.
    threading.Thread(target=ensure_active_document_indexed, daemon=True).start()
