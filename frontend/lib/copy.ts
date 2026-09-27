import type { DocErrorCode, StreamErrorCode } from "@/lib/types";
import { MAX_DOCS_PER_WORKSPACE, MAX_FILE_MB, MAX_FILES_PER_BATCH, QUESTION_MIN_CHARS } from "@/lib/limits";

// On-screen strings from APP_FLOW §5. The server's `message` is only a fallback for unknown codes.

export const DOC_ERROR_COPY: Record<DocErrorCode, string> = {
  no_text: "No selectable text found. Scanned documents aren’t supported yet.",
  unreadable: "Couldn’t read this file. Check that it opens on your computer and isn’t password-protected.",
  interrupted: "Processing was interrupted by a server restart. Add the file again.",
};

export const UPLOAD_ERROR_COPY: Record<string, string> = {
  unsupported_type: "This file type isn’t supported. Use PDF, .docx, or .pptx.",
  legacy_format: "Old Word and PowerPoint formats aren’t supported. Save it as .docx or .pptx and add it again.",
  bad_signature: "This file doesn’t look like a real PDF, Word, or PowerPoint file.",
  file_too_large: `This file is larger than ${MAX_FILE_MB} MB.`,
  workspace_full: `Your library is full (${MAX_DOCS_PER_WORKSPACE} documents). Delete a document to add another.`,
  storage_full: "The demo’s storage is full right now. Try again later.",
  upload_rate_limited: "Too many uploads in the last hour. Try again later.",
  network: "Upload didn’t finish. Check your connection.",
  unavailable: "The server isn’t ready. Try again in a moment.",
};

export const COPY = {
  waitingForServer: "Waiting for the server…",
  serverStarting: "The server is starting. This can take up to a minute.",
  serverUnreachable: "Can’t reach the server. Check your connection, then try again.",
  tooManyFiles: `You can add up to ${MAX_FILES_PER_BATCH} files at a time. Add the rest in another batch.`,
  libraryLoadFailed: "Couldn’t load your documents.",
  lockedNoDocuments: "Add a document to ask questions.",
  lockedProcessing: "Your documents are still processing. You can ask once one is ready.",
  threadEmpty: "Ask a question about your documents.",
  alreadyInLibrary: (name: string) => `${name} is already in your library.`,
  deleted: (name: string) => `${name} deleted.`,
  deleteFailed: (name: string) => `Couldn’t delete ${name}. Try again.`,
  ready: (name: string) => `${name} is ready.`,
  failed: (name: string, reason: string) => `${name} failed: ${reason}`,
};

export const STREAM_ERROR: Record<StreamErrorCode, { message: string; retry: boolean }> = {
  llm_busy: { message: "CourseMind is busy right now. Try again in a minute.", retry: true },
  daily_limit: { message: "The demo has reached today’s question limit. Try again tomorrow.", retry: false },
  llm_error: { message: "The answer was interrupted.", retry: true },
};

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export const ANSWER_COPY = {
  searching: (docs: number) => `Searching ${plural(docs, "document", "documents")}…`,
  found: (passages: number) => `Found ${plural(passages, "passage", "passages")}. Writing answer…`,
  stopped: "Stopped.",
  noReadyDocuments: "Add a document before asking.",
  askRateLimited: "Too many questions in a minute. Try again shortly.",
  connectionLost: "Connection lost. Check your connection, then retry.",
  refusalHint: "Try rephrasing with terms from your notes, or add the document that covers this.",
  sourceRemoved: "This document has since been removed from your library.",
  answerReady: "Answer ready.",
  tooShort: `Type at least ${QUESTION_MIN_CHARS} characters.`,
};
