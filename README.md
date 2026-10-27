# RAG-BANKING-COMPLIANCE-SYSTEM

## CrediSense AI — Commercial Loan & Credit Policy RAG Copilot

**CrediSense AI** is a commercial credit risk and underwriting copilot powered by Retrieval-Augmented Generation (RAG). It enables credit analysts, underwriters, and risk officers to query institutional lending policy manuals, verify covenant ratios (DSCR, LTV, Current Ratio), and validate regulatory compliance rules with **zero hallucination** and **exact page citations**.

---

## 🌟 Key Features

- **Single Active Policy Workflow**: Upload or replace your active credit policy manual (PDF). The system cleans up previous vectors and re-indexes the new document with 768-dim embeddings in real time.
- **Sub-2-Second Token Streaming**: Live SSE token generation with grounded answers and instant retrieval latency.
- **Zero Hallucination with Page Citations**: Every answer includes transparent source citations displaying chunk ID, page number, similarity score, and excerpted context.
- **Interactive Vector Explorer**: Inspect chunk embeddings, similarity distributions, and semantic distances inside ChromaDB.
- **One-Click Audit Report Export**: Download full Markdown audit reports containing dialogue turns, grounded answers, and verifiable citations.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend API** | `FastAPI` (Python 3.12+) | High-performance asynchronous REST API with SSE Streaming |
| **Vector Embeddings** | `nomic-ai/nomic-embed-text-v1.5` | 768-dimensional Matryoshka asymmetric embeddings |
| **Vector Database** | `ChromaDB` | Persistent vector store with Cosine distance indexing |
| **LLM Inference** | `Groq API` (`openai/gpt-oss-120b`) | Ultra-fast open-weights model inference |
| **PDF Extraction & Chunking** | `pypdf` + `RecursiveCharacterTextSplitter` | Structured page-level parsing with 1000-char chunking & 200-char overlap |
| **Frontend Dashboard** | HTML5 / Vanilla CSS / ES6 JavaScript | Glassmorphism dark-mode UI with live status & streaming |

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/sachinM-10/rag_compliance_policy.git
cd rag_compliance_policy
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=openai/gpt-oss-120b
PORT=8000
HOST=127.0.0.1
```

### 4. Launch the Web Application
```bash
python main.py
```
Open your browser and navigate to `http://127.0.0.1:8000`.

---

## 📁 Repository Structure

```text
rag_compliance_policy/
├── app.py                                   # FastAPI backend server with SSE streaming
├── main.py                                  # Application entry point & Uvicorn runner
├── config.py                                # System configuration & environment paths
├── rag_chat.py                              # RAG pipeline with Groq LLM integration
├── chroma_build/                            # Ingestion & Vector Store Module
│   ├── chroma_store.py                      # ChromaDB manager & Nomic embedding function
│   ├── pdf_loader.py                        # PDF text extractor & semantic chunker
│   └── load_data.py                         # CLI re-indexing script
├── data/                                    # Active policy PDF documents
├── sample_test_pdfs/                        # Reference loan policies for testing
├── static/                                  # Web Application Frontend
│   ├── index.html                           # Single Page Application
│   ├── app.js                               # Frontend logic & SSE stream reader
│   └── style.css                            # Glassmorphism dark mode stylesheet
└── requirements.txt                         # Python dependencies
```

---

## 📜 License
MIT License.
