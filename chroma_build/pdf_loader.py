"""
===================================================================================
FILE: chroma_build/pdf_loader.py
ROLE: PDF Document Extraction & Semantic Text Chunking Engine
===================================================================================
WHAT THIS FILE CONTAINS:
- load_pdf_pages(): Reads PDF page-by-page using pypdf and captures page metadata.
- chunk_pdf_documents(): Uses RecursiveCharacterTextSplitter (1000 size, 200 overlap)
  to divide PDF pages into 117 structured semantic chunks with rich metadata.
===================================================================================
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure parent directory is included in sys.path so config module can be imported cleanly
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config

def load_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Page-by-Page PDF Text Extractor:
    -------------------------------
    Reads a target PDF file page-by-page using pypdf, extracts the raw text content,
    and returns a list of dictionaries containing page numbers and text.

    :param pdf_path: Path object pointing to the target PDF file.
    :return: List of dicts, e.g. [{"page": 1, "text": "...", "source": "fdic_manual.pdf"}]
    """
    # Verify that the specified PDF file exists on disk
    if not pdf_path.exists():
        raise FileNotFoundError(f"Target PDF document was not found at: {pdf_path}")
    
    print(f"[PDF Extraction] Reading '{pdf_path.name}' page-by-page...")
    
    # Initialize pypdf reader to inspect PDF pages
    reader = pypdf.PdfReader(str(pdf_path))
    pages_data = []
    
    # Loop through each page in the PDF (1-indexed for user-friendly page citations)
    for page_num, page in enumerate(reader.pages, start=1):
        # Extract text from the page (fallback to empty string if page contains images/no text)
        raw_text = page.extract_text() or ""
        cleaned_text = raw_text.strip()
        
        # Only save pages that contain readable text
        if cleaned_text:
            pages_data.append({
                "page": page_num,
                "text": cleaned_text,
                "source": pdf_path.name
            })
            
    print(f"[PDF Extraction] Completed: Extracted {len(pages_data)} readable pages.")
    return pages_data


def chunk_pdf_documents(pdf_path: Path = config.PDF_PATH) -> List[Dict[str, Any]]:
    """
    Semantic Text Chunker:
    ----------------------
    Applies RecursiveCharacterTextSplitter to break long PDF pages into smaller,
    semantically meaningful chunks suitable for vector embedding and retrieval.

    Each chunk retains rich metadata (source filename, page number, chunk index).

    :param pdf_path: Path object pointing to the PDF document.
    :return: List of structured chunk dicts containing 'id', 'text', and 'metadata'.
    """
    # Step 1: Extract all pages from the PDF
    pages = load_pdf_pages(pdf_path)
    
    # Step 2: Initialize LangChain's RecursiveCharacterTextSplitter using config parameters
    print(f"[PDF Chunking] Applying RecursiveCharacterTextSplitter (Size={config.CHUNK_SIZE}, Overlap={config.CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=config.CHUNK_SEPARATORS,
        length_function=len
    )
    
    chunks = []
    doc_stem = pdf_path.stem
    
    # Step 3: Iterate through each extracted page and divide it into semantic chunks
    for page_info in pages:
        page_num = page_info["page"]
        text = page_info["text"]
        
        # Split page text into smaller overlapping chunks
        page_splits = text_splitter.split_text(text)
        
        # Step 4: Attach unique IDs and metadata to each chunk
        for idx, chunk_text in enumerate(page_splits):
            chunk_id = f"{doc_stem}_p{page_num}_c{idx}"
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "source": page_info["source"],
                    "page": page_num,
                    "chunk_index": idx,
                    "doc_id": doc_stem
                }
            })
            
    print(f"[PDF Chunking] Completed: Generated {len(chunks)} semantic chunks from {len(pages)} pages.\n")
    return chunks
