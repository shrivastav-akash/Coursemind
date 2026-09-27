import os
from pathlib import Path
from typing import get_args
from uuid import UUID

from dotenv import load_dotenv

from app.schemas import RetrievalMode

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# Environment (TRD §5). Secrets stay empty until the steps that use them.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODELS = _list("LLM_MODELS", "openai/gpt-oss-20b,openai/gpt-oss-120b")
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "4"))
PREFETCH_K = int(os.getenv("PREFETCH_K", "20"))
RETRIEVAL_MODE: RetrievalMode = os.getenv("RETRIEVAL_MODE", "hybrid_rerank")  # type: ignore[assignment]  # checked below
ALLOWED_ORIGINS = _list("ALLOWED_ORIGINS", "http://localhost:3000")

# Fail at startup, not on the first request.
if RETRIEVAL_MODE not in get_args(RetrievalMode):
    raise ValueError(f"RETRIEVAL_MODE must be dense, hybrid or hybrid_rerank, got {RETRIEVAL_MODE!r}")

# Fixed ids (BACKEND_SCHEMA §2). Never change: every stored id depends on them.
ID_NAMESPACE = UUID("ed1bef70-990c-4c4f-b76f-28c158ed0c8f")
EVAL_WORKSPACE_ID = UUID("860e1106-bd9b-47f8-9f4d-37eb144b909d")

# Limits (BACKEND_SCHEMA §9). Frontend mirrors live in frontend/lib/limits.ts.
MAX_FILE_MB = 25
MAX_DOCS_PER_WORKSPACE = 30
MAX_TOTAL_CHUNKS = 30_000
MAX_UNZIPPED_MB = 200
QUESTION_MIN_CHARS = 3
QUESTION_MAX_CHARS = 500
ASK_LIMIT = (5, 60)  # requests per seconds, per IP
UPLOAD_LIMIT = (30, 3600)

REFUSAL = "I couldn't find that in your notes."

# Qdrant Cloud Inference models (BACKEND_SCHEMA §4).
DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "qdrant/bm25"
COLBERT_MODEL = "answerdotai/answerai-colbert-small-v1"
