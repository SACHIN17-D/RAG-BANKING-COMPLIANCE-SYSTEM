import sys
import argparse
from rag_chat import run_cli_chat

def main():
    parser = argparse.ArgumentParser(description="FDIC Loan Application & Credit Risk RAG Assistant")
    parser.add_argument("--cli", action="store_true", help="Launch terminal interactive CLI chat mode")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default: 8000)")
    args = parser.parse_args()

    if args.cli:
        run_cli_chat()
    else:
        print("\n" + "=" * 65, flush=True)
        print("      FDIC LOAN POLICY & CREDIT RISK RAG ASSISTANT", flush=True)
        print("=================================================================", flush=True)
        print(f" Starting FastAPI Web Application on http://{args.host}:{args.port}", flush=True)
        print(" Press Ctrl+C to stop the server.", flush=True)
        print("=" * 65 + "\n", flush=True)
        import app as fastapi_app
        import uvicorn
        uvicorn.run(fastapi_app.app, host=args.host, port=args.port, reload=False)



if __name__ == "__main__":
    main()

