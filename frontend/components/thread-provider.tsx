"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { useWorkspace } from "@/components/workspace-provider";
import * as api from "@/lib/api";
import { ANSWER_COPY, STREAM_ERROR } from "@/lib/copy";
import type { Turn, TurnError } from "@/lib/types";

interface ThreadValue {
  turns: Turn[];
  /** The id of the answer that is streaming now, if any. */
  streamingId: string | null;
  draft: string;
  setDraft: (text: string) => void;
  send: (question: string) => void;
  stop: () => void;
  retry: (turnId: string) => void;
  announcement: string;
}

const ThreadContext = createContext<ThreadValue | null>(null);

export function useThread(): ThreadValue {
  const value = useContext(ThreadContext);
  if (!value) throw new Error("useThread must be used inside <ThreadProvider>");
  return value;
}

// Errors that arrive as a normal HTTP response, before any answer text (BACKEND_SCHEMA §7, APP_FLOW J4).
function preStreamError(err: unknown): TurnError {
  if (err instanceof api.ApiError) {
    if (err.code === "no_ready_documents") return { message: ANSWER_COPY.noReadyDocuments, retry: false, addFiles: true };
    if (err.code === "ask_rate_limited") return { message: ANSWER_COPY.askRateLimited, retry: false };
    if (err.code === "network" || err.code === "unavailable") return { message: ANSWER_COPY.connectionLost, retry: true };
  }
  return { ...STREAM_ERROR.llm_error };
}

// Thread lives in browser memory only; a reload clears it (APP_FLOW §2).
export function ThreadProvider({ children }: { children: React.ReactNode }) {
  const { documents, retryServer } = useWorkspace();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const running = useRef<{ id: string; controller: AbortController } | null>(null);
  const readyCount = documents.filter((d) => d.status === "ready").length;

  const update = (id: string, patch: Partial<Turn> | ((turn: Turn) => Partial<Turn>)) =>
    setTurns((all) => all.map((t) => (t.id === id ? { ...t, ...(typeof patch === "function" ? patch(t) : patch) } : t)));

  const stop = useCallback(() => running.current?.controller.abort(), []);

  const run = useCallback(
    async (id: string, question: string) => {
      running.current?.controller.abort(); // a new question stops the running answer first (APP_FLOW J4)
      const controller = new AbortController();
      running.current = { id, controller };
      setStreamingId(id);
      setAnnouncement("");
      let finished = false;
      try {
        for await (const event of api.ask(question, controller.signal)) {
          if (event.event === "sources") update(id, { sources: event.data, status: "writing" });
          else if (event.event === "token") update(id, (t) => ({ text: t.text + event.data.t, status: "writing" }));
          else if (event.event === "done") {
            finished = true;
            update(id, { status: "done", refused: event.data.refused });
            setAnnouncement(ANSWER_COPY.answerReady);
          } else {
            finished = true;
            update(id, { status: "error", error: { ...STREAM_ERROR[event.data.code] } });
          }
        }
        if (!finished) update(id, { status: "error", error: { message: ANSWER_COPY.connectionLost, retry: true } });
      } catch (err) {
        if (controller.signal.aborted) {
          update(id, { status: "stopped" });
        } else {
          const error = preStreamError(err);
          update(id, { status: "error", error });
          if (err instanceof api.ApiError) {
            if (err.code === "ask_rate_limited") setDraft(question); // nothing is retyped (APP_FLOW J4)
            if (err.code === "network" || err.code === "unavailable") retryServer();
          }
        }
      } finally {
        if (running.current?.id === id) {
          running.current = null;
          setStreamingId(null);
        }
      }
    },
    [retryServer],
  );

  const send = useCallback(
    (question: string) => {
      const id = crypto.randomUUID();
      setTurns((all) => [
        ...all,
        { id, question, searching: readyCount, status: "searching", sources: null, text: "", refused: false },
      ]);
      setDraft("");
      void run(id, question);
    },
    [readyCount, run],
  );

  const retry = useCallback(
    (turnId: string) => {
      const turn = turns.find((t) => t.id === turnId);
      if (!turn) return;
      update(turnId, { status: "searching", searching: readyCount, sources: null, text: "", refused: false, error: undefined });
      void run(turnId, turn.question);
    },
    [turns, readyCount, run],
  );

  const value = useMemo(
    () => ({ turns, streamingId, draft, setDraft, send, stop, retry, announcement }),
    [turns, streamingId, draft, send, stop, retry, announcement],
  );
  return <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>;
}
