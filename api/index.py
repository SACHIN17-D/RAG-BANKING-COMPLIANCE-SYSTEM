import os
import sys
import tempfile
from pathlib import Path

# Disable ChromaDB telemetry writes and redirect cache to writable /tmp
os.environ["ANONYMIZED_TELEMETRY"] = "False"
tmp = tempfile.gettempdir()
os.environ["HOME"] = tmp
os.environ["USERPROFILE"] = tmp
os.environ["XDG_CACHE_HOME"] = str(Path(tmp) / ".cache")
os.environ["HF_HOME"] = str(Path(tmp) / ".cache" / "huggingface")

try:
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
    safe_onnx_dir = Path(tmp) / ".cache" / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    safe_onnx_dir.mkdir(parents=True, exist_ok=True)
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = safe_onnx_dir
except Exception:
    pass

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app
