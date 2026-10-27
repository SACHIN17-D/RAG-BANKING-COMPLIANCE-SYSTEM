# FDIC RAG System — Beginner's Conceptual & Theoretical Guide

Welcome! This guide explains **how Retrieval-Augmented Generation (RAG) works** in simple, beginner-friendly terms using our **FDIC Loan Application RAG Project** as an example.

---

## 💡 What is RAG? (The Open-Book Exam Analogy)

Imagine you ask a banking expert a very specific question about a 48-page FDIC regulatory manual.

- **Standard AI (Without RAG)**: Answers purely from memory. If it forgets a detail or doesn't know the exact FDIC page, it might make up plausible-sounding rules (**hallucination**).
- **RAG System (Our Project)**: Before answering, the AI looks up the exact pages in the FDIC manual, reads the relevant policy paragraphs, and summarizes the facts **directly from the text**.

> **RAG = Open-Book Search + Smart AI Explanation**

---

## 📐 Architecture & Unicode Execution Flow Diagram

```text
  ┌────────────────────────────────────────────────────────┐
  │              1. SOURCE PDF DOCUMENTATION               │
  │                  (data/fdic_manual.pdf)                │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │             2. PAGE EXTRACTION (pypdf)                 │
  │        (Extracts 48 pages & binds page metadata)       │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │        3. SEMANTIC RECURSIVE TEXT CHUNKING             │
  │    (RecursiveCharacterTextSplitter: 1000 size, 200 overlap) │
  │                 (Generates 117 Chunks)                 │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │       4. VECTOR EMBEDDING (Nomic Embed v1.5)           │
  │     (768-dim Matryoshka Asymmetric Search Vectors)     │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │        5. PERSISTENT VECTOR DB (ChromaDB)              │
  │              (Saved in root/chroma_db/)                │
  └───────────────────────────┬────────────────────────────┘
                              │
                              │ (Cosine Similarity Vector Query)
                              ▼
┌──────────────────────┐  ┌────────────────────────────────┐
│  USER QUERY (CLI)    ├──► 6. RELEVANCE SCORE FILTERING   │
│ (Dynamic User Prompt)│  │ (Score >= 0.20, Top K = 4)     │
└──────────────────────┘  └───────────────┬────────────────┘
                                          │
                                          ▼
                          ┌────────────────────────────────┐
                          │ 7. GROQ LLM GROUNDED ANSWER    │
                          │     (openai/gpt-oss-120b)      │
                          │ (Grounded, Zero-Hallucination) │
                          └────────────────────────────────┘
```

---

## 🔄 The 6 Steps of our FDIC RAG Pipeline

Our system processes documents and answers questions through 6 simple steps:

### Step 1: PDF Text Extraction
- **File**: `chroma_build/pdf_loader.py` -> `load_pdf_pages()`
- **Concept**: Reads `data/fdic_manual.pdf` page-by-page.
- **What happens**: Extracts the raw text from each page and binds the page number (e.g. `Page 15`).

### Step 2: Semantic Text Chunking
- **File**: `chroma_build/pdf_loader.py` -> `chunk_pdf_documents()`
- **Concept**: AI embedding models cannot process an entire book all at once. We break long pages into bite-sized paragraphs called **chunks**.
- **Hyperparameters**:
  - `CHUNK_SIZE = 1000`: Each chunk is about 1,000 characters long.
  - `CHUNK_OVERLAP = 200`: 200 overlapping characters between adjacent chunks so sentences across page breaks aren't cut off mid-thought.
- **Result**: Converts 48 pages into **117 semantic chunks**.

### Step 3: Vector Embedding (Text to Numbers)
- **File**: `chroma_build/chroma_store.py` -> `NomicEmbeddingFunction`
- **Concept**: Computers cannot calculate mathematical similarity using raw English words. An **embedding model** (`nomic-ai/nomic-embed-text-v1.5`) translates text into a list of **768 numerical coordinates** (a vector).
- **Asymmetric Search Rule**:
  - PDF document chunks get prefixed with `"search_document: "`
  - User questions get prefixed with `"search_query: "`
  - This helps the computer match short user questions to long manual passages.

### Step 4: Storing in ChromaDB
- **File**: `chroma_build/chroma_store.py` -> `ChromaManager`
- **Concept**: Saved vectors are stored in a local database folder called `chroma_db/`.
- **Why**: Once built, you don't need to re-read the PDF every time you ask a question. The database loads instantly.

### Step 5: Cosine Similarity Matching
- **File**: `chroma_build/chroma_store.py` -> `search()`
- **Concept**: When you type a question in PowerShell (e.g. *"Why is my loan delayed?"*), the system turns your question into a vector and calculates the **angle/distance** between your question vector and all 117 document chunk vectors.
- **Similarity Score**:
  $$\text{Similarity Score} = 1.0 - \text{Cosine Distance}$$
  - `1.000` = Perfect identical match
  - `0.000` = Completely unrelated
- **Noise Filter (`min_score = 0.20`)**: Chunks scoring below 0.20 are filtered out so low-quality noise is never sent to the AI.
- **Top K (`n_results = 4`)**: Selects the **top 4 most relevant chunks**.

### Step 6: Grounded AI Answer Generation
- **File**: `rag_chat.py` -> `get_llm_response()`
- **Concept**: Sends the top 4 retrieved chunks and your question to Groq's LLM (`openai/gpt-oss-120b`).
- **System Prompt**: Enforces 3 golden rules:
  1. **Zero Hallucination**: Rely ONLY on the provided chunks.
  2. **Direct & Concise**: Give 2 to 4 clear points straight to the point.
  3. **Page Citations**: Always cite exact FDIC page numbers (e.g. *Page 15*).

---

## 🎯 Project Scope

The **FDIC Loan Policy & Credit Risk RAG System** is specifically scoped to provide regulatory analysis and loan underwriting advice across the following domains:

1. **Loan Administration & Credit Documentation**: Verification of personal financial statements, income tax returns, and mandatory credit file requirements.
2. **Real Estate Appraisals & Valuations**: Rules governing property reappraisal frequencies, appraisal exemptions, and written evaluation standards.
3. **Accounts Receivable & Working Capital Lines**: Borrowing base eligibility, aged invoice exclusions (90+ days past due), and advance percentage limits.
4. **Distressed Borrower Workouts**: Restructuring action plans for operating cash flow diminishment and collateral depreciation.
5. **Subprime Lending Risk Management**: Enhanced underwriting, capitalization buffers, and stress testing for subprime auto, credit card, and residential mortgage facilities.
6. **Commercial Real Estate (CRE) & Construction**: Progress-based funding, draw inspection schedules, and developer track record evaluations.
7. **Credit Governance**: Independent credit review systems, conflict-of-interest prevention, and credit committee approval authorities.

---

## 🌟 Project Novelty & Technical Key Features

1. **Matryoshka Asymmetric Vector Embeddings**:
   - Implements **Nomic Embed Text v1.5** (768-dim), utilizing specialized `search_document:` and `search_query:` prefixes for asymmetric retrieval.

2. **Cosine Distance Normalization & Noise Filtering**:
   - Converts raw Cosine distances into normalized similarity scores ($\text{Score} = 1.0 - \text{Distance}$) and enforces a `min_score = 0.20` relevance threshold to eliminate unhelpful noise.

3. **Zero-Hallucination Grounded Prompt Design**:
   - Employs a custom System Prompt forcing the LLM (`openai/gpt-oss-120b` via Groq) to rely exclusively on retrieved chunks and cite exact manual page numbers.

4. **Multi-Platform Console Sanitization**:
   - Includes custom `sanitize_text()` routines converting non-standard unicode characters into safe ASCII, preventing Windows PowerShell terminal crashes.

5. **Clean Modular Package Architecture**:
   - Separates Python package logic (`chroma_build/`) from persistent vector storage (`chroma_db/`).

---

## 🔮 Future Improvements & Expansion Possibilities

### 1. Dynamic Live Document Watching & Multi-PDF Ingestion
- **Concept**: Expand `chroma_build/load_data.py` with a background directory watcher (`watchdog` package).
- **Capability**: Whenever a new regulatory PDF manual or updated bank policy document is dropped into the `data/` folder, the system will automatically parse, chunk, embed, and incrementally update ChromaDB without requiring manual reloads.

### 2. Hybrid Search (Dense Vector + BM25 Sparse Keyword Search)
- **Concept**: Combine dense vector semantic search (Nomic v1.5) with sparse keyword search (BM25).
- **Benefit**: Ensures ultra-high accuracy for specific regulatory acronyms, form numbers, and exact section codes alongside semantic vector matching.

### 3. Re-Ranking Pipeline (Cross-Encoder / Cohere Rerank)
- **Concept**: Add a two-stage retrieval pipeline where top $K=20$ candidates are initially retrieved from ChromaDB, then re-ranked using a Cross-Encoder model before selecting the top 4 chunks.

### 4. Multi-Modal Document Extraction & OCR
- **Concept**: Integrate vision-capable OCR models (e.g., LLaVA or Tesseract) to parse complex financial tables, balance sheet images, and scanned PDF forms.

### 5. Web Dashboard & REST API
- **Concept**: Expose the RAG engine via FastAPI endpoints and build a modern web user interface (React / Vite + Tailwind CSS) with interactive document viewers and citation highlighting.

---

## 📚 Key Concepts Glossary

| Concept | Simple Definition |
| :--- | :--- |
| **Vector** | A list of numbers representing the mathematical meaning of a piece of text. |
| **Cosine Similarity** | A geometric calculation measuring how close two text vectors are in meaning. |
| **Matryoshka Embedding** | A modern embedding technique (Nomic v1.5) that outputs high-density 768-dim vectors. |
| **System Prompt** | The hidden master instruction given to the AI defining its persona, rules, and tone. |
| **Zero Hallucination** | Strict system prompt rule preventing the AI from guessing or making up fake rules. |
