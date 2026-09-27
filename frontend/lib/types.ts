// Hand-kept mirror of the backend's Pydantic models (BACKEND_SCHEMA §8). Change both together.

export type DocType = "pdf" | "docx" | "pptx";
export type Status = "queued" | "processing" | "ready" | "failed";
export type DocErrorCode = "no_text" | "unreadable" | "interrupted";
export type StreamErrorCode = "llm_busy" | "daily_limit" | "llm_error";

export interface Document {
  id: string; name: string; type: DocType; size_bytes: number; is_sample: boolean;
  status: Status; error_code: DocErrorCode | null; chunks: number; created_at: string;
}
export interface Source {
  n: number; doc_id: string; doc_name: string; doc_type: DocType; location: string; text: string;
}
export type AskEvent =
  | { event: "sources"; data: Source[] }
  | { event: "token"; data: { t: string } }
  | { event: "done"; data: { refused: boolean; model: string | null } }
  | { event: "error"; data: { code: StreamErrorCode } };
export interface ErrorBody { code: string; message: string }

// UI-only: one question and its answer in the thread (kept in browser memory, BACKEND_SCHEMA §1).
export type TurnStatus = "searching" | "writing" | "done" | "stopped" | "error";
export interface TurnError {
  message: string;
  retry: boolean;
  addFiles?: boolean;
}
export interface Turn {
  id: string;
  question: string;
  /** Ready documents when it was asked, for "Searching 3 documents…". */
  searching: number;
  status: TurnStatus;
  sources: Source[] | null;
  text: string;
  refused: boolean;
  error?: TurnError;
}
