"""
===================================================================================
PACKAGE: chroma_build
ROLE: Vector Ingestion & ChromaDB Management Package
===================================================================================
WHAT THIS PACKAGE CONTAINS:
- pdf_loader.py: Page-by-page PDF extraction and semantic text chunking.
- chroma_store.py: Custom Nomic Embed v1.5 function and ChromaDB PersistentClient manager.
- load_data.py: Ingestion pipeline execution script with live tqdm progress bar.
===================================================================================
"""
from .pdf_loader import load_pdf_pages, chunk_pdf_documents
from .chroma_store import ChromaManager, NomicEmbeddingFunction

__all__ = [
    "load_pdf_pages",
    "chunk_pdf_documents",
    "ChromaManager",
    "NomicEmbeddingFunction"
]
