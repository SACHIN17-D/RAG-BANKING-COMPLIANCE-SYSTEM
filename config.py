"""
===================================================================================
FILE: config.py
ROLE: Centralized Application Configuration & Hyperparameter Registry
===================================================================================
WHAT THIS FILE CONTAINS:
- API Keys & LLM Settings: Stores Groq API Key and target LLM model name.
- File System Paths: Defines paths for data/ directory, source PDF, and chroma_db/.
- Vector Database Settings: Collection name, Nomic 1.5 embedding model & 768-dim size.
- Retrieval Thresholds: Default Min Similarity Score (0.20) and Top-K matches (4).
- Text Chunking Settings: Chunk size (1000), chunk overlap (200), and section separators.
===================================================================================
"""
import os
import tempfile
from pathlib import Path

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =====================================================================
# 1. LLM & API CONFIGURATION
# Configures the Groq API key and LLM model identifier.
# =====================================================================
# Groq API Key used to authenticate OpenAI-compatible API requests
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Groq LLM model identifier for generating grounded answers
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
MODEL_NAME = LLM_MODEL  # Alias for backward compatibility

# =====================================================================
# 2. BASE DIRECTORY PATHS
# Resolves absolute file paths relative to the project root directory.
# =====================================================================
# Root folder of the project
BASE_DIR = Path(__file__).resolve().parent

# Folder storing source PDF manual documents
DATA_DIR = BASE_DIR / "data"
COMPANIES_DIR = DATA_DIR / "companies"
COMPANIES_REGISTRY_FILE = DATA_DIR / "companies.json"
USERS_REGISTRY_FILE = DATA_DIR / "users.json"

# Security & Authentication Settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fdic-loan-application-rag-super-secret-jwt-key-2026")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# Cloud Environment Detection (Vercel Serverless & Render Free Tier)
is_vercel = bool(os.getenv("VERCEL"))
is_render = (
    os.getenv("RENDER", "").lower() == "true"
    or bool(os.getenv("RENDER_SERVICE_ID"))
    or os.getenv("USE_LIGHTWEIGHT_EMBEDDINGS", "").lower() == "true"
)
is_cloud = is_vercel or is_render

# Dedicated directory for persistent vector database storage (system temp for Vercel Serverless)
if is_vercel:
    CHROMA_DB_DIR = Path(tempfile.gettempdir()) / "chroma_db"
else:
    CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# Multi-tenant Default Configuration
DEFAULT_COMPANY_ID = "default_fdic"
DEFAULT_COMPANY_NAME = "FDIC Ground Truth Bank"

def sanitize_company_id(raw_id: str) -> str:
    """Converts company name or ID string to clean alphanumeric slug."""
    clean = "".join(c if c.isalnum() else "_" for c in raw_id.strip().lower())
    clean = "_".join(filter(None, clean.split("_")))
    return clean or "default_fdic"

def get_company_collection_name(company_id: str) -> str:
    """Returns ChromaDB collection name for a given company_id."""
    clean_id = sanitize_company_id(company_id)
    return f"tenant_{clean_id}"

def get_company_dir(company_id: str) -> Path:
    """Returns Path directory for a specific company's uploads."""
    clean_id = sanitize_company_id(company_id)
    company_path = COMPANIES_DIR / clean_id
    company_path.mkdir(parents=True, exist_ok=True)
    return company_path

# =====================================================================
# 3. SOURCE DOCUMENT CONFIGURATION
# Specifies default target PDF file to be parsed and indexed.
# =====================================================================
PDF_FILENAME = os.getenv("PDF_FILENAME", "fdic_manual.pdf")
PDF_PATH = DATA_DIR / PDF_FILENAME

# =====================================================================
# 4. CHROMADB VECTOR STORE & EMBEDDING HYPERPARAMETERS
# Sets up embedding model details, vector collection name, and score thresholds.
# =====================================================================
# Base default collection name inside ChromaDB
COLLECTION_NAME = get_company_collection_name(DEFAULT_COMPANY_ID)

# Cloud & Lightweight Embedding Detection (Vercel Lambda & Render 512MB RAM optimization)
default_embed = "onnx-all-MiniLM-L6-v2" if is_cloud else "nomic-ai/nomic-embed-text-v1.5"
default_dim = 384 if is_cloud else 768

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", default_embed)
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", str(default_dim)))

# Default minimum Cosine similarity score threshold (filters out weak matches)
DEFAULT_MIN_SCORE = float(os.getenv("MIN_SIMILARITY_SCORE", "0.20"))

# Default number of top matching document chunks to retrieve per search query
DEFAULT_TOP_K = int(os.getenv("TOP_K", "4"))

# =====================================================================
# 5. RECURSIVE TEXT CHUNKING HYPERPARAMETERS
# Defines chunk character length, overlap, and document section separators.
# =====================================================================
# Target character length per chunk
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))

# Character overlap between adjacent chunks to preserve context across boundaries
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Custom hierarchy of separators respecting document structure and manual sections
CHUNK_SEPARATORS = [
    "\n\nSection ",
    "\n\nCHAPTER ",
    "\n\n",
    "\n",
    ". ",
    " ",
    ""
]
