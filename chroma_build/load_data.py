"""
===================================================================================
FILE: chroma_build/load_data.py
ROLE: Vector Database Ingestion CLI Command Script
===================================================================================
WHAT THIS FILE CONTAINS:
- main(): CLI entry point supporting flags (--pdf, --force-reload). Parses PDF manual,
  generates semantic chunks, and builds/updates persistent vector database in chroma_db/.
  (Command: python .\chroma_build\load_data.py --force-reload)
===================================================================================
"""
import os
import sys
import argparse
from pathlib import Path

# Ensure parent directory is included in sys.path so config module can be imported cleanly
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import config

# Flexible import handling supporting both module execution and direct script execution
try:
    from .chroma_store import ChromaManager
except ImportError:
    from chroma_build.chroma_store import ChromaManager


def main():
    """
    Vector Ingestion CLI Entry Point:
    ---------------------------------
    Parses command-line flags (--force-reload, --pdf), initializes the ChromaManager,
    extracts & chunks the target PDF manual, and indexes vector embeddings into ChromaDB.
    """
    # Step 1: Configure command-line argument parser
    parser = argparse.ArgumentParser(
        description="PDF Vector Ingestion Pipeline: Parse PDF manual and build ChromaDB embeddings store."
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=str(config.PDF_PATH),
        help="Path to target PDF document file (default: data/fdic_manual.pdf)"
    )
    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Force re-parsing and re-indexing of PDF into ChromaDB even if database already exists"
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)

    # Step 2: Display pipeline execution header and hyperparameter details
    print("\n" + "=" * 60)
    print(" === PDF to ChromaDB Vector Ingestion Pipeline ===")
    print("=" * 60)
    print(f" [1/5] Target PDF Path : {pdf_path}")
    print(f" [2/5] ChromaDB Path   : {config.CHROMA_DB_DIR}")
    print(f" [3/5] Collection Name : {config.COLLECTION_NAME}")
    print(f" [4/5] Embedding Model : {config.EMBEDDING_MODEL_NAME} ({config.EMBEDDING_DIM}-dim)")
    print(f" [5/5] Chunk Strategy  : Size={config.CHUNK_SIZE}, Overlap={config.CHUNK_OVERLAP}")
    print("=" * 60 + "\n")

    # Step 3: Initialize ChromaDB Manager
    print("[STEP 1/2] Initializing ChromaDB Storage Manager...")
    manager = ChromaManager()

    # Step 4: Parse PDF pages, generate semantic chunks, and index vectors
    print("\n[STEP 2/2] Processing PDF & Indexing Chunks into ChromaDB...")
    collection = manager.load_and_index_documents(pdf_path=pdf_path, force_reload=args.force_reload)

    # Step 5: Report completion status
    total_chunks = collection.count()
    print("=" * 60)
    print(f"[STATUS SUCCESS] ChromaDB vector store is ready with {total_chunks} indexed chunks.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
