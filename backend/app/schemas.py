from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

DocType = Literal["pdf", "docx", "pptx"]
Status = Literal["queued", "processing", "ready", "failed"]
DocErrorCode = Literal["no_text", "unreadable", "interrupted"]
ErrorCode = Literal[
    "invalid_workspace", "validation_error", "not_found", "still_processing",
    "workspace_full", "file_too_large", "unsupported_type", "legacy_format",
    "bad_signature", "upload_rate_limited", "storage_full", "no_ready_documents",
    "ask_rate_limited", "unavailable",
]
StreamErrorCode = Literal["llm_busy", "daily_limit", "llm_error"]
RetrievalMode = Literal["dense", "hybrid", "hybrid_rerank"]

class Document(BaseModel):
    id: UUID
    name: str
    type: DocType
    size_bytes: int
    is_sample: bool
    status: Status
    error_code: DocErrorCode | None
    chunks: int
    created_at: datetime

class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=3, max_length=500)  # stripped before validation

class Source(BaseModel):
    n: int                    # 1-based, matches [n] in the answer
    doc_id: UUID
    doc_name: str
    doc_type: DocType
    location: str
    text: str

class ErrorBody(BaseModel):
    code: ErrorCode
    message: str

class Health(BaseModel):
    status: Literal["ok"]
