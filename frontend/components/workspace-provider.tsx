"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "@/components/ui/toast";
import * as api from "@/lib/api";
import { COPY, DOC_ERROR_COPY, UPLOAD_ERROR_COPY } from "@/lib/copy";
import { MAX_FILE_MB, MAX_FILES_PER_BATCH } from "@/lib/limits";
import type { DocType, Document } from "@/lib/types";
import { hasWorkspace } from "@/lib/workspace";

export type ServerState = "checking" | "ready" | "starting" | "unreachable";
export type LibraryState = "loading" | "loaded" | "error";

/** A file the server hasn't accepted yet: waiting, uploading, or rejected (APP_FLOW J3). */
export interface LocalRow {
  key: string;
  name: string;
  type: DocType | null;
  status: "waiting" | "uploading" | "failed";
  message?: string;
  retryable?: boolean;
  file?: File;
}

const HEALTH_RETRY_MS = 3_000;
const GIVE_UP_MS = 90_000;
const POLL_MS = 2_000;
const PARALLEL_UPLOADS = 2;
const FLASH_MS = 1_200;
const TYPES: Record<string, DocType> = { ".pdf": "pdf", ".docx": "docx", ".pptx": "pptx" };

function extension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

// Same rules as the server, checked before sending so obvious mistakes fail instantly.
function precheck(file: File): string | null {
  const ext = extension(file.name);
  if (ext === ".doc" || ext === ".ppt") return "legacy_format";
  if (!TYPES[ext]) return "unsupported_type";
  if (file.size > MAX_FILE_MB * 1024 * 1024) return "file_too_large";
  return null;
}

const busy = (doc: Document) => doc.status === "queued" || doc.status === "processing";

// Read once on the client, before any request creates a workspace: a first visit's library is
// known to be empty, so it can render without waiting on the network. The static HTML is
// prerendered as a first visit (Lighthouse: the first-visit text is the LCP element); for a
// returning visit an inline script in app/layout.tsx hides those parts before first paint.
const FIRST_VISIT = typeof window !== "undefined" && !hasWorkspace();
const neverChanges = () => () => {};

// When the focused row disappears (deleted or removed), focus would fall to <body>;
// put it on the visible "Add files" button instead (APP_FLOW J12).
function refocusIfLost() {
  window.setTimeout(() => {
    if (document.activeElement && document.activeElement !== document.body) return;
    const target = [...document.querySelectorAll<HTMLElement>("[data-add-files]")].find((el) => el.offsetParent !== null);
    target?.focus();
  }, 50);
}

function useServer() {
  const [state, setState] = useState<ServerState>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const startedAt = Date.now();
    const check = async () => {
      const ok = await api.health();
      if (cancelled) return;
      if (ok) return setState("ready");
      if (Date.now() - startedAt >= GIVE_UP_MS) return setState("unreachable");
      setState("starting");
      timer = window.setTimeout(check, HEALTH_RETRY_MS);
    };
    check();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [attempt]);

  // Start checking again: after "Try again", or when a request finds the server gone.
  const recheck = useCallback(() => {
    setState((s) => (s === "ready" ? "starting" : s));
    setAttempt((a) => a + 1);
  }, []);
  return { state, recheck };
}

interface WorkspaceValue {
  server: ServerState;
  retryServer: () => void;
  documents: Document[];
  localRows: LocalRow[];
  libraryState: LibraryState;
  reloadLibrary: () => void;
  openPicker: () => void;
  retryUpload: (key: string) => void;
  removeLocal: (key: string) => void;
  requestDelete: (doc: Document) => void;
  removeFailed: (doc: Document) => void;
  addSamples: () => void;
  addingSamples: boolean;
  flashId: string | null;
  dragging: boolean;
  hasDocuments: boolean;
  /** Why the question box is locked, or null when a question can be sent. */
  lockReason: string | null;
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return value;
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { state: server, recheck } = useServer();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [libraryState, setLibraryState] = useState<LibraryState>("loading");
  const [localRows, setLocalRows] = useState<LocalRow[]>([]);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [dragging, setDragging] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [addingSamples, setAddingSamples] = useState(false);

  const documentsRef = useRef<Document[]>([]);
  const queue = useRef<LocalRow[]>([]);
  const active = useRef(0);
  const pumpRef = useRef<() => void>(() => {});
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    documentsRef.current = documents;
  }, [documents]);

  const serverGone = useCallback(
    (err: unknown) => {
      if (err instanceof api.ApiError && (err.code === "network" || err.code === "unavailable")) recheck();
    },
    [recheck],
  );

  // quiet: an early fetch made before /status answers; its failure is the health loop's to report.
  const refresh = useCallback(async (quiet = false) => {
    try {
      const next = await api.listDocuments();
      // Announce each document that just finished (APP_FLOW J12), not every poll.
      const before = new Map(documentsRef.current.map((d) => [d.id, d]));
      const finished = next.filter((d) => {
        const was = before.get(d.id);
        return was && busy(was) && !busy(d);
      });
      if (finished.length) {
        setAnnouncement(
          finished
            .map((d) => (d.status === "ready" ? COPY.ready(d.name) : COPY.failed(d.name, DOC_ERROR_COPY[d.error_code ?? "unreadable"])))
            .join(" "),
        );
      }
      setDocuments(next);
      setLibraryState("loaded");
    } catch (err) {
      if (quiet) return;
      serverGone(err);
      // A failed poll keeps the list on screen; only a failed first load shows the error.
      setLibraryState((s) => (s === "loaded" ? s : "error"));
    }
  }, [serverGone]);

  // First paint without waiting on the network (Lighthouse: the first-visit text was the LCP
  // element, held back by /status then /documents). A returning visit fetches its library
  // alongside /status instead of after it.
  const firstVisit = useSyncExternalStore(neverChanges, () => FIRST_VISIT, () => true);
  useEffect(() => {
    if (!FIRST_VISIT) void refresh(true);
  }, [refresh]);

  useEffect(() => {
    if (server === "ready") void refresh();
  }, [server, refresh]);

  const polling = documents.some(busy);
  useEffect(() => {
    if (!polling || server !== "ready") return;
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [polling, server, refresh]);

  const flash = useCallback((id: string) => {
    setFlashId(id);
    window.setTimeout(() => setFlashId((current) => (current === id ? null : current)), FLASH_MS);
  }, []);

  const updateLocal = (key: string, patch: Partial<LocalRow>) =>
    setLocalRows((rows) => rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  const pump = useCallback(() => {
    while (active.current < PARALLEL_UPLOADS && queue.current.length > 0) {
      const row = queue.current.shift()!;
      active.current += 1;
      updateLocal(row.key, { status: "uploading", message: undefined });
      api
        .uploadDocument(row.file!)
        .then(({ document, duplicate }) => {
          setLocalRows((rows) => rows.filter((r) => r.key !== row.key));
          setDocuments((prev) =>
            prev.some((d) => d.id === document.id) ? prev.map((d) => (d.id === document.id ? document : d)) : [document, ...prev],
          );
          if (duplicate) {
            toast.add({ title: COPY.alreadyInLibrary(document.name) });
            flash(document.id);
          }
        })
        .catch((err: unknown) => {
          serverGone(err);
          const code = err instanceof api.ApiError ? err.code : "network";
          const message = UPLOAD_ERROR_COPY[code] ?? (err instanceof api.ApiError ? err.message : UPLOAD_ERROR_COPY.network);
          updateLocal(row.key, { status: "failed", message, retryable: code === "network" });
          setAnnouncement(COPY.failed(row.name, message));
        })
        .finally(() => {
          active.current -= 1;
          pumpRef.current(); // start the next waiting file
        });
    }
  }, [flash, serverGone]);
  useEffect(() => {
    pumpRef.current = pump;
  }, [pump]);

  const addFiles = useCallback(
    (files: File[]) => {
      if (server !== "ready" || files.length === 0) return;
      let batch = files;
      if (batch.length > MAX_FILES_PER_BATCH) {
        toast.add({ title: COPY.tooManyFiles });
        batch = batch.slice(0, MAX_FILES_PER_BATCH);
      }
      const rows: LocalRow[] = batch.map((file) => {
        const problem = precheck(file);
        const base = { key: crypto.randomUUID(), name: file.name, type: TYPES[extension(file.name)] ?? null };
        return problem
          ? { ...base, status: "failed", message: UPLOAD_ERROR_COPY[problem] }
          : { ...base, status: "waiting", file };
      });
      setLocalRows((prev) => [...rows, ...prev]);
      queue.current.push(...rows.filter((r) => r.status === "waiting"));
      pump();
    },
    [server, pump],
  );

  const retryUpload = useCallback(
    (key: string) => {
      const row = localRows.find((r) => r.key === key);
      if (!row?.file) return;
      updateLocal(key, { status: "waiting", message: undefined, retryable: false });
      queue.current.push(row);
      pump();
    },
    [localRows, pump],
  );

  const removeLocal = useCallback((key: string) => {
    setLocalRows((rows) => rows.filter((r) => r.key !== key));
    refocusIfLost();
  }, []);

  const deleteOnServer = useCallback(
    async (doc: Document): Promise<boolean> => {
      try {
        await api.deleteDocument(doc.id);
      } catch (err) {
        // Already gone counts as deleted.
        if (!(err instanceof api.ApiError && err.code === "not_found")) {
          serverGone(err);
          toast.add({ title: COPY.deleteFailed(doc.name) });
          return false;
        }
      }
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      refocusIfLost();
      return true;
    },
    [serverGone],
  );

  const addSamples = useCallback(async () => {
    if (addingSamples) return;
    setAddingSamples(true);
    try {
      const { documents: samples, added } = await api.addSamples();
      setDocuments((prev) => {
        const byId = new Map(samples.map((s) => [s.id, s]));
        const updated = prev.map((d) => byId.get(d.id) ?? d);
        return [...samples.filter((s) => !prev.some((d) => d.id === s.id)), ...updated];
      });
      toast.add({ title: added ? COPY.samplesAdded : COPY.samplesAlreadyAdded });
      // The first-visit block holding the button is replaced by the list.
      refocusIfLost();
    } catch (err) {
      serverGone(err);
      const code = err instanceof api.ApiError ? err.code : "network";
      toast.add({ title: UPLOAD_ERROR_COPY[code] ?? (err instanceof api.ApiError ? err.message : UPLOAD_ERROR_COPY.network) });
    } finally {
      setAddingSamples(false);
    }
  }, [addingSamples, serverGone]);

  const confirmDelete = async () => {
    setDeleteOpen(false);
    if (deleteTarget && (await deleteOnServer(deleteTarget))) toast.add({ title: COPY.deleted(deleteTarget.name) });
  };

  // Drag files anywhere over the window (S11); the file picker is the non-drag alternative.
  const addFilesRef = useRef(addFiles);
  useEffect(() => {
    addFilesRef.current = addFiles;
  }, [addFiles]);
  useEffect(() => {
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");
    const enter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth += 1;
      setDragging(true);
    };
    const leave = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const over = (e: DragEvent) => {
      if (hasFiles(e)) e.preventDefault();
    };
    const drop = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      setDragging(false);
      addFilesRef.current(Array.from(e.dataTransfer?.files ?? []));
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragleave", leave);
    window.addEventListener("dragover", over);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("dragover", over);
      window.removeEventListener("drop", drop);
    };
  }, []);

  const hasDocuments = documents.length > 0 || localRows.length > 0;
  const lockReason =
    server !== "ready"
      ? COPY.waitingForServer
      : documents.some((d) => d.status === "ready")
        ? null
        : documents.some(busy) || localRows.some((r) => r.status !== "failed")
          ? COPY.lockedProcessing
          : COPY.lockedNoDocuments;

  const value = useMemo<WorkspaceValue>(
    () => ({
      server,
      retryServer: recheck,
      documents,
      localRows,
      libraryState: firstVisit && libraryState === "loading" ? "loaded" : libraryState,
      reloadLibrary: () => {
        setLibraryState("loading");
        void refresh();
      },
      openPicker: () => inputRef.current?.click(),
      retryUpload,
      removeLocal,
      requestDelete: (doc) => {
        setDeleteTarget(doc);
        setDeleteOpen(true);
      },
      removeFailed: (doc) => void deleteOnServer(doc),
      addSamples: () => void addSamples(),
      addingSamples,
      flashId,
      dragging,
      hasDocuments,
      lockReason,
    }),
    [server, recheck, documents, localRows, libraryState, firstVisit, refresh, retryUpload, removeLocal, deleteOnServer, addSamples, addingSamples, flashId, dragging, hasDocuments, lockReason],
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        accept=".pdf,.docx,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation"
        onChange={(e) => {
          addFiles(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent className="overscroll-contain">
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete <span translate="no">{deleteTarget?.name}</span>?
            </AlertDialogTitle>
            <AlertDialogDescription>
              It will no longer be used in answers. Answers already shown stay on screen.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>
              Delete document
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </WorkspaceContext.Provider>
  );
}
