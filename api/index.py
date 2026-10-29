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

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
    safe_onnx_dir = Path(tmp) / ".cache" / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    safe_onnx_dir.mkdir(parents=True, exist_ok=True)
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = safe_onnx_dir

    model_file = safe_onnx_dir / "onnx" / "model.onnx"
    # If model is incomplete or corrupted (<85MB), purge it
    if model_file.exists() and model_file.stat().st_size < 85000000:
        import shutil
        shutil.rmtree(safe_onnx_dir / "onnx", ignore_errors=True)

    # If model is not extracted but bundled onnx.tar.gz exists, extract it instantly (0.6s)
    bundled_tar = root_dir / "models" / "onnx.tar.gz"
    if not (safe_onnx_dir / "onnx" / "model.onnx").exists() and bundled_tar.exists():
        import tarfile
        with tarfile.open(bundled_tar, "r:gz") as tar:
            tar.extractall(path=safe_onnx_dir)
except Exception:
    pass

# Copy bundled pre-indexed ChromaDB to writable /tmp on cold start
bundled_db = root_dir / "chroma_db"
bundled_sqlite = bundled_db / "chroma.sqlite3"
tmp_db = Path(tmp) / "chroma_db"
tmp_sqlite = tmp_db / "chroma.sqlite3"
if bundled_sqlite.exists():
    if not tmp_sqlite.exists() or tmp_sqlite.stat().st_size < bundled_sqlite.stat().st_size:
        import shutil
        try:
            shutil.copytree(bundled_db, tmp_db, dirs_exist_ok=True)
        except Exception:
            pass

from app import app
