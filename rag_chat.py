"""
===================================================================================
FILE: rag_chat.py
ROLE: Interactive RAG Engine, Streaming Response & Groq LLM Generator
===================================================================================
WHAT THIS FILE CONTAINS:
- SYSTEM_BRAINSTORMING_PROMPT: Advisory prompt enforcing zero hallucination & concise facts.
- sanitize_text(): ASCII sanitization preventing Windows PowerShell UnicodeEncodeError crashes.
- get_llm_response(): Sends retrieved chunks, user question & multi-turn history to Groq API.
- get_llm_response_stream(): Generator streaming tokens real-time via SSE.
- run_cli_chat(): Interactive PowerShell loop displaying query progress and answers.
===================================================================================
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional
import config
from chroma_build.chroma_store import ChromaManager

# Safe import for OpenAI client to connect with Groq API
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =====================================================================
# SYSTEM PROMPT FOR RAG LLM GENERATION
# Enforces concise, elegant, zero-hallucination FDIC ground truth answers.
# =====================================================================
SYSTEM_BRAINSTORMING_PROMPT = """You are an expert FDIC Commercial Loan Advisor. Your role is to give loan applicants concise, elegant, and directly relevant explanations based strictly on FDIC manual ground truth.

### CORE INSTRUCTIONS:
1. **CONCISE & DIRECT (GET STRAIGHT TO THE POINT)**:
   - Keep your response brief, clear, and focused (around 2 to 4 key points max).
   - Avoid long multi-page essays, repetitive intros, or unnecessary filler sections.

2. **SMOOTH & ELEGANT FDIC GROUND TRUTH**:
   - Explain the FDIC policy ground truth smoothly in plain, natural conversational language.
   - Weave exact FDIC manual page citations (e.g. Page 15, Page 6) naturally into your points.

3. **STRICT FACTUAL GROUNDING (ZERO HALLUCINATION)**:
   - Rely ONLY on the facts present in the provided FDIC manual context. Never invent rules, figures, or unmentioned procedures.

4. **ABSENT CONTEXT**:
   - If no relevant policy exists in the context, state simply:
     "Based on the provided FDIC Manual context, no specific policy or guideline was found regarding this query."
"""


def sanitize_text(text: str) -> str:
    """
    Console Output Sanitizer:
    -------------------------
    Replaces unicode smart quotes, non-breaking hyphens, narrow spaces, and em-dashes
    with standard ASCII characters to prevent Windows PowerShell 'cp1252' UnicodeEncodeError crashes.
    """
    replacements = {
        "\u2011": "-",  # non-breaking hyphen
        "\u2012": "-",
        "\u2013": "-",  # en-dash
        "\u2014": "-",  # em-dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2026": "...",# ellipsis
        "\u202f": " ",  # narrow non-breaking space
        "\u00a0": " ",  # non-breaking space
        "\u200b": "",   # zero-width space
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
        
    # Safely convert any remaining unsupported unicode characters to clean ASCII
    return text.encode("ascii", errors="ignore").decode("ascii")


def _build_messages_payload(query: str, retrieved_chunks: list, conversation_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    """Builds system, history, and current retrieval user messages for LLM completion."""
    # Construct formatted context block from retrieved document chunks
    if not retrieved_chunks:
        context_text = "No matching policy chunks retrieved."
    else:
        context_text = ""
        for idx, item in enumerate(retrieved_chunks, start=1):
            meta = item.get("metadata", {})
            page = meta.get("page", "N/A")
            source = meta.get("source", "N/A")
            chunk_idx = meta.get("chunk_index", "N/A")
            score = item.get("similarity_score", 0.0)
            context_text += f"\n--- CHUNK #{idx} (File: {source}, Page {page}, Chunk Index {chunk_idx}, Relevance Score: {score}) ---\n"
            context_text += item.get("document", "") + "\n"

    # User prompt incorporating retrieved FDIC manual context
    user_prompt = f"""Retrieved Policy Manual Context:
{context_text}

Current User Question / Applicant Scenario:
{query}

Please provide a concise, elegant, and direct explanation addressing the user's scenario based on the manual facts above:"""

    messages = [{"role": "system", "content": SYSTEM_BRAINSTORMING_PROMPT}]
    
    # Include up to 6 prior conversation turns for multi-turn conversational memory
    if conversation_history:
        for turn in conversation_history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_prompt})
    return messages


def _get_groq_models():
    primary = config.LLM_MODEL or "llama-3.3-70b-versatile"
    fallbacks = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    models = [primary] + [m for m in fallbacks if m != primary]
    return models


def get_llm_response(query: str, retrieved_chunks: list, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Groq LLM Generation Helper:
    ---------------------------
    Formats retrieved document chunks, user question, and multi-turn chat history into a grounded prompt
    and requests a response from Groq API with automatic fallback.
    """
    groq_key = os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY
    if not groq_key:
        return "[LLM Notice] GROQ_API_KEY is not set in your .env file. Please add your GROQ_API_KEY to test LLM generation."

    if not OpenAI:
        return "[LLM Error] OpenAI package not installed. Run: pip install openai"

    if not retrieved_chunks:
        return "Based on the provided policy manual context, no relevant policy, guideline, or documentation was found regarding this query."

    messages = _build_messages_payload(query, retrieved_chunks, conversation_history)
    client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")

    last_error = None
    for model_name in _get_groq_models():
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=650
            )
            raw_ans = response.choices[0].message.content.strip()
            return sanitize_text(raw_ans)
        except Exception as e:
            last_error = e
            continue

    return f"[LLM API Error] Failed to generate response via Groq API: {last_error}"


def get_llm_response_stream(query: str, retrieved_chunks: list, conversation_history: Optional[List[Dict[str, str]]] = None) -> Generator[str, None, None]:
    """
    Groq Streaming LLM Response Generator:
    --------------------------------------
    Streams LLM output tokens token-by-token using Groq API streaming mode with fallback models.
    """
    groq_key = os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY
    if not groq_key:
        yield "[LLM Notice] GROQ_API_KEY is not set in your .env file."
        return

    if not OpenAI:
        yield "[LLM Error] OpenAI package not installed."
        return

    if not retrieved_chunks:
        yield "Based on the provided policy manual context, no relevant policy, guideline, or documentation was found regarding this query."
        return

    messages = _build_messages_payload(query, retrieved_chunks, conversation_history)
    client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")

    stream_started = False
    last_error = None

    for model_name in _get_groq_models():
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=650,
                stream=True
            )
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        stream_started = True
                        yield sanitize_text(delta.content)
            if stream_started:
                return
        except Exception as e:
            last_error = e
            if stream_started:
                yield f"\n[Stream interrupted]: {e}"
                return
            continue

    if not stream_started:
        yield f"[LLM Stream Error]: {str(last_error)}"


def run_cli_chat():
    """
    Interactive RAG Assistant Command Loop:
    --------------------------------------
    Runs the main PowerShell CLI chat loop with cosine similarity search and LLM answers.
    """
    print("\n" + "=" * 65)
    print("      FDIC LOAN POLICY & CREDIT RISK RAG ASSISTANT")
    print("=" * 65)
    print(f" Embedding Model : {config.EMBEDDING_MODEL_NAME} ({config.EMBEDDING_DIM}-dim)")
    print(f" LLM Model       : {config.LLM_MODEL}")
    print(f" Vector Store    : ChromaDB ({config.CHROMA_DB_DIR})")
    print("=" * 65)
    print("\nAssistant: Hello! I am your FDIC Loan Policy & Credit Risk Assistant.")
    print("           How can I help you today with loan underwriting, risk policies, or FDIC guidelines?")
    print("           (Type 'exit' or 'quit' to end session)\n")

    manager = ChromaManager()
    if not manager.is_db_populated():
        print("[Notice] Vector database is not populated yet. Run 'python .\\chroma_build\\load_data.py' first.")

    history = []

    while True:
        try:
            user_input = input("\nUser > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting session. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("\nGoodbye! Have a great day.")
            break

        print("\n" + "-" * 65)
        print(f"[COSINE RETRIEVAL] Embedding query & searching ChromaDB...")
        print("-" * 65)

        try:
            results = manager.search(
                query=user_input,
                n_results=config.DEFAULT_TOP_K,
                min_score=config.DEFAULT_MIN_SCORE
            )
        except Exception as e:
            print(f"[Error performing retrieval]: {e}")
            continue

        if not results:
            print("\n>>> RETRIEVED CHUNKS: 0 matches above relevance threshold <<<")
        else:
            print(f"\n>>> RETRIEVED CHUNKS ({len(results)} Cosine Matches) <<<")
            for idx, item in enumerate(results, start=1):
                meta = item["metadata"]
                doc = item["document"]
                score = item["similarity_score"]
                page = meta.get("page", "N/A")
                source = meta.get("source", "N/A")
                
                one_line_doc = doc.replace('\r', ' ').replace('\n', ' ')
                snippet_line = one_line_doc[:160].strip() + "..."
                
                print(f"[Chunk #{idx}] File: {source}, Page {page} (Score: {score:.4f}):")
                print(f"Snippet: {snippet_line}\n")

        print("=" * 65)
        print("LLM Answer:")
        print("-" * 65)

        llm_response = get_llm_response(user_input, results, conversation_history=history)
        print(f"{llm_response}")
        print("=" * 65)

        # Update CLI session history
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": llm_response})


if __name__ == "__main__":
    run_cli_chat()
