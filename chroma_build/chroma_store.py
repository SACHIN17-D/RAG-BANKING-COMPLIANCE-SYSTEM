"""
===================================================================================
FILE: chroma_build/chroma_store.py
ROLE: Embedding Function & Persistent Vector Database Store Manager
===================================================================================
WHAT THIS FILE CONTAINS:
- NomicEmbeddingFunction: Custom ChromaDB embedding class using SentenceTransformer
  ('nomic-ai/nomic-embed-text-v1.5') with 'search_document:' and 'search_query:' prefixes.
- ChromaManager: Manages ChromaDB PersistentClient in root/chroma_db/, handles collection
  conflicts, executes batch upserts with tqdm progress bar, and runs Cosine similarity search.
===================================================================================
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure parent directory is included in sys.path so config module can be imported cleanly
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm
import config

# Safely patch ChromaDB ONNX model download directory to writable temporary storage (avoids read-only filesystem errors)
try:
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
    safe_onnx_dir = Path(tempfile.gettempdir()) / ".cache" / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    safe_onnx_dir.mkdir(parents=True, exist_ok=True)
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = safe_onnx_dir
except Exception:
    pass

try:
    from .pdf_loader import chunk_pdf_documents
except ImportError:
    from chroma_build.pdf_loader import chunk_pdf_documents


class NomicEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Nomic Embed Text v1.5 Custom ChromaDB Embedding Function:
    --------------------------------------------------------
    Implements Matryoshka 768-dimensional vector embeddings using sentence-transformers.
    Automatically prefixes document chunks with 'search_document: ' and queries with
    'search_query: ' to achieve optimal asymmetric vector retrieval.
    """
    def __init__(self, model_name: str = config.EMBEDDING_MODEL_NAME):
        print("\n" + "=" * 60)
        print(f"[CLI Status] Loading Embedding Model: '{model_name}'...")
        print("[CLI Status] Initializing tqdm progress bar...")
        print("=" * 60)
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        # Load SentenceTransformer model with trust_remote_code=True for Nomic v1.5
        self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
        print("[CLI Status] Embedding model loaded successfully!\n")

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Embeds a batch of document texts into 768-dim float vectors.
        """
        formatted_inputs = []
        for text in input:
            # Prepend Nomic document prefix if not already present
            if not text.startswith("search_document: ") and not text.startswith("search_query: "):
                text = f"search_document: {text}"
            formatted_inputs.append(text)
        
        # Generate numerical vector embeddings using SentenceTransformers
        embeddings = self.model.encode(formatted_inputs, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, input: Any = None, query: Any = None) -> List[List[float]]:
        """
        Embeds search query text using the Nomic query prefix 'search_query: '.
        Accepts both 'input' or 'query' keyword arguments to satisfy ChromaDB internal calls.
        """
        text_input = input if input is not None else query
        if isinstance(text_input, str):
            text_input = [text_input]
            
        formatted = []
        for t in text_input:
            if not t.startswith("search_query: "):
                t = f"search_query: {t}"
            formatted.append(t)
            
        embeddings = self.model.encode(formatted, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()


class ChromaManager:
    """
    ChromaDB Storage & Search Manager:
    ---------------------------------
    Handles PersistentClient lifecycle, collection creation, batch document indexing
    with tqdm progress bar display, and Cosine similarity vector retrieval.
    """
    def __init__(
        self,
        db_dir: Path = config.CHROMA_DB_DIR,
        collection_name: str = config.COLLECTION_NAME,
        model_name: str = config.EMBEDDING_MODEL_NAME
    ):
        self.db_dir = db_dir
        self.collection_name = collection_name
        self.model_name = model_name
        
        # Select Ultra-Lightweight ONNX function (Zero PyTorch, ~40MB RAM) for cloud/Vercel/Render, or Nomic
        is_cloud_lightweight = (
            config.is_cloud
            or "onnx" in self.model_name.lower()
            or "minilm" in self.model_name.lower()
            or "default" in self.model_name.lower()
        )

        if is_cloud_lightweight:
            print(f"[ChromaDB Manager] Initializing Ultra-Lightweight ONNX Embedding Function (Zero-PyTorch, ~40MB RAM)...", flush=True)
            try:
                from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
                safe_onnx_dir = Path(tempfile.gettempdir()) / ".cache" / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
                safe_onnx_dir.mkdir(parents=True, exist_ok=True)
                ONNXMiniLM_L6_V2.DOWNLOAD_PATH = safe_onnx_dir
            except Exception:
                pass
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        elif "nomic" in self.model_name.lower():
            try:
                self.embedding_fn = NomicEmbeddingFunction(model_name=self.model_name)
            except Exception as e:
                print(f"[ChromaDB Manager] Falling back to DefaultEmbeddingFunction: {e}", flush=True)
                self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        else:
            try:
                self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.model_name
                )
            except Exception as e:
                print(f"[ChromaDB Manager] Falling back to DefaultEmbeddingFunction: {e}", flush=True)
                self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.client = None
        self.collection = None

    def _init_client(self, collection_name: Optional[str] = None):
        """Ensure DB directory exists and initialize ChromaDB PersistentClient."""
        target_name = collection_name or self.collection_name
        is_new_dir = not self.db_dir.exists()
        if is_new_dir:
            print(f"[ChromaDB Manager] Creating dedicated vector database directory at '{self.db_dir}'...")
            os.makedirs(self.db_dir, exist_ok=True)
            
        if self.client is None:
            self.client = chromadb.PersistentClient(path=str(self.db_dir))
        
        self.collection_name = target_name
        # Safely create or retrieve collection with Cosine distance metric
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            # Handle collection embedding model mismatch automatically
            print(f"[ChromaDB Manager] Resetting collection due to mismatch/error: {e}")
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )

        return is_new_dir

    def set_collection(self, collection_name: str):
        """Switches the active ChromaDB collection target."""
        if self.collection_name != collection_name or self.collection is None:
            self._init_client(collection_name=collection_name)
        return self.collection

    def delete_company_collection(self, company_id: str):
        """Deletes a company's ChromaDB collection completely."""
        col_name = config.get_company_collection_name(company_id)
        if self.client is None:
            self._init_client(col_name)
        try:
            self.client.delete_collection(name=col_name)
            print(f"[ChromaDB Manager] Deleted collection '{col_name}'.")
        except Exception as e:
            print(f"[ChromaDB Manager] Collection '{col_name}' deletion notice: {e}")
        if self.collection_name == col_name:
            self.collection = None

    def is_db_populated(self) -> bool:
        """Check if the collection exists and contains document chunks."""
        if not self.collection:
            self._init_client()
        return self.collection.count() > 0

    def load_and_index_documents(self, pdf_path: Path = config.PDF_PATH, force_reload: bool = False):
        """
        Loads PDF, generates semantic chunks, and indexes them into ChromaDB with tqdm progress.
        """
        is_new_dir = self._init_client()
        current_count = self.collection.count()

        should_reload = is_new_dir or (current_count == 0) or force_reload

        if not should_reload:
            print(f"[ChromaDB Manager] Database is intact and populated ({current_count} vectors existing). Skipping reload.")
            print("                   (Tip: Use --force-reload to force re-chunking and re-indexing)")
            return self.collection

        if force_reload and current_count > 0:
            print(f"[ChromaDB Manager] Force reload requested. Resetting collection '{self.collection_name}'...")
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )

        print(f"\n[ChromaDB Manager] Starting PDF ingestion into ChromaDB using {self.model_name}...")
        chunks = chunk_pdf_documents(pdf_path)

        if not chunks:
            print("[ChromaDB Manager] Warning: No chunks generated from PDF.")
            return self.collection

        # Process chunks in batches (100 for fast ONNX runtime inference, 50 for Nomic)
        batch_size = 50 if "nomic" in self.model_name.lower() else 100
        total_chunks = len(chunks)
        batches = [chunks[i:i + batch_size] for i in range(0, total_chunks, batch_size)]

        print(f"[CLI Progress] Indexing {total_chunks} chunks across {len(batches)} batches...")
        
        # Display live tqdm progress bar in terminal during batch ingestion
        with tqdm(total=total_chunks, desc="[Vector Indexing Progress]", unit="chunk") as pbar:
            for batch in batches:
                ids = [item["id"] for item in batch]
                
                documents = []
                for item in batch:
                    text = item["text"]
                    if "nomic" in self.model_name.lower() and not text.startswith("search_document: "):
                        text = f"search_document: {text}"
                    documents.append(text)
                    
                metadatas = [item["metadata"] for item in batch]

                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                pbar.update(len(batch))

        print(f"\n[STATUS SUCCESS] Successfully indexed {self.collection.count()} chunks into ChromaDB at '{self.db_dir}'.\n")
        return self.collection

    def search(
        self,
        query: str,
        n_results: int = config.DEFAULT_TOP_K,
        min_score: float = config.DEFAULT_MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """
        Perform high-accuracy Cosine similarity search on stored PDF chunks.
        Applies Nomic query formatting, Cosine distance calculation, relevance score normalization,
        and threshold filtering (min_score) to eliminate weak/irrelevant noise.
        """
        if not self.collection:
            self._init_client()

        if self.collection.count() == 0:
            raise RuntimeError("ChromaDB collection is empty. Run load_and_index_documents() first.")

        search_query = query
        if "nomic" in self.model_name.lower() and not query.startswith("search_query: "):
            search_query = f"search_query: {query}"

        # Execute vector query in ChromaDB
        results = self.collection.query(
            query_texts=[search_query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        formatted_results = []
        docs = results["documents"][0] if results.get("documents") and len(results["documents"]) > 0 else []
        metas = results["metadatas"][0] if results.get("metadatas") and len(results["metadatas"]) > 0 else []
        distances = results["distances"][0] if "distances" in results and results["distances"] and len(results["distances"]) > 0 else [0.0] * len(docs)

        # Process matching results and convert Cosine Distance to Similarity Score
        for doc, meta, dist in zip(docs, metas, distances):
            clean_doc = doc
            if clean_doc.startswith("search_document: "):
                clean_doc = clean_doc[len("search_document: "):]
            
            # Convert Cosine distance d to normalized similarity score (1.0 - d)
            sim_score = max(0.0, 1.0 - dist) if dist <= 1.0 else (1.0 / (1.0 + dist))
            
            # Filter out chunks below minimum score threshold
            if sim_score >= min_score:
                formatted_results.append({
                    "document": clean_doc,
                    "metadata": meta,
                    "distance": round(float(dist), 4),
                    "similarity_score": round(float(sim_score), 4)
                })

        # Sort matches by similarity score descending (highest score first)
        formatted_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return formatted_results
