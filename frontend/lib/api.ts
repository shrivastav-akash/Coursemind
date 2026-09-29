import type { AskEvent, Document, ErrorBody } from "@/lib/types";
import { getWorkspaceId } from "@/lib/workspace";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Any failed call: `code` is the server's error code, or "network" when no response arrived. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly retryAfter?: number,
  ) {
    super(message);
  }
}

async function call(path: string, init: RequestInit = {}): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: { "X-Workspace-Id": getWorkspaceId(), ...init.headers },
    });
  } catch (err) {
    if (init.signal?.aborted) throw err; // the caller stopped it on purpose
    throw new ApiError(0, "network", "No response from the server.");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null;
    const retryAfter = Number(response.headers.get("Retry-After")) || undefined;
    throw new ApiError(response.status, body?.code ?? "http_error", body?.message ?? response.statusText, retryAfter);
  }
  return response;
}

export async function health(): Promise<boolean> {
  try {
    // Short timeout: a sleeping server can hang; the caller retries every 3 s (APP_FLOW §2).
    // Not /health: EasyPrivacy (uBlock, AdGuard, Brave) blocks `||onrender.com/health`.
    const response = await fetch(`${API_URL}/status`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    return response.ok;
  } catch {
    return false;
  }
}

export async function listDocuments(): Promise<Document[]> {
  return (await call("/documents")).json();
}

/** 202 = new or re-queued; 200 = this exact file is already in the workspace. */
export async function uploadDocument(file: File): Promise<{ document: Document; duplicate: boolean }> {
  const form = new FormData();
  form.append("file", file);
  const response = await call("/documents", { method: "POST", body: form });
  return { document: await response.json(), duplicate: response.status === 200 };
}

/** 202 = at least one sample added or re-queued; 200 = all were already in the workspace. */
export async function addSamples(): Promise<{ documents: Document[]; added: boolean }> {
  const response = await call("/documents/samples", { method: "POST" });
  return { documents: await response.json(), added: response.status === 202 };
}

export async function deleteDocument(id: string): Promise<void> {
  await call(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
}

/**
 * POST /ask as a stream of typed events: one `sources`, then `token`s, then `done` or `error`
 * (BACKEND_SCHEMA §7). EventSource can't POST, so this reads the fetch body directly.
 * Errors before the stream starts throw ApiError; a connection lost mid-stream throws ApiError("network").
 */
export async function* ask(question: string, signal: AbortSignal): AsyncGenerator<AskEvent> {
  const response = await call("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    while (true) {
      let chunk: ReadableStreamReadResult<string>;
      try {
        chunk = await reader.read();
      } catch (err) {
        if (signal.aborted) throw err;
        throw new ApiError(0, "network", "The connection closed mid-answer.");
      }
      if (chunk.done) return;
      buffer += chunk.value;
      let end: number;
      while ((end = buffer.indexOf("\n\n")) >= 0) {
        const event = parseEvent(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        if (event) yield event;
      }
    }
  } finally {
    reader.cancel().catch(() => {}); // stop reading if the consumer leaves early
  }
}

function parseEvent(block: string): AskEvent | null {
  let event = "";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trimStart();
  }
  return event && data ? ({ event, data: JSON.parse(data) } as AskEvent) : null;
}
