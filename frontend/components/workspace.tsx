"use client";

import { AppHeader } from "@/components/app-header";
import { FirstVisit } from "@/components/first-visit";
import { GuardedButton } from "@/components/guarded-button";
import { Library, LibraryCount } from "@/components/library";
import { QUESTION_BOX_ID, QuestionBox } from "@/components/question-box";
import { ServerBanner } from "@/components/server-banner";
import { Thread } from "@/components/thread";
import { ThreadProvider, useThread } from "@/components/thread-provider";
import {
  WorkspaceProvider,
  useWorkspace,
} from "@/components/workspace-provider";
import { COPY } from "@/lib/copy";
import { SUGGESTED_QUESTIONS } from "@/lib/samples";

// S1/S2: header, library (column at 1024 px and up, sheet below), thread, question box (UI_UX_BRIEF §2, §4).
export function Workspace() {
  return (
    <WorkspaceProvider>
      <ThreadProvider>
        <div className="flex h-dvh flex-col">
          <a
            href={`#${QUESTION_BOX_ID}`}
            className="sr-only rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
          >
            Skip to question box
          </a>
          <AppHeader />
          <div className="grid min-h-0 flex-1 lg:grid-cols-[320px_minmax(0,1fr)] xl:grid-cols-[360px_minmax(0,1fr)]">
            <LibraryColumn />
            <main className="flex min-h-0 flex-col">
              <ServerBanner />
              <ThreadArea />
              <QuestionBox />
            </main>
          </div>
        </div>
      </ThreadProvider>
    </WorkspaceProvider>
  );
}

function LibraryColumn() {
  const { dragging, server } = useWorkspace();
  return (
    <aside
      aria-labelledby="library-heading"
      className="relative hidden min-h-0 flex-col gap-4 border-r p-4 lg:flex"
    >
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="library-heading" className="text-xl font-bold">
          Documents
        </h2>
        <LibraryCount />
      </div>
      <Library />
      {/* S11: shown while files are dragged anywhere over the window. */}
      {dragging && server === "ready" && (
        <div className="absolute inset-2 grid place-items-center rounded-xl border-2 border-dashed border-input bg-background/95 text-sm font-medium">
          Drop to add files
        </div>
      )}
    </aside>
  );
}

function ThreadArea() {
  const { documents, localRows, hasDocuments, libraryState, lockReason } = useWorkspace();
  const { turns, send } = useThread();
  if (turns.length > 0) return <Thread />;
  if (!hasDocuments && libraryState === "loaded") return <FirstVisit />;
  if (!hasDocuments) return <div className="flex-1" />;
  // APP_FLOW J2: suggestions while the library holds only samples and one of them is ready.
  const samplesOnly = localRows.length === 0 && documents.every((d) => d.is_sample) && documents.some((d) => d.status === "ready");
  if (samplesOnly) {
    return (
      <div className="flex flex-1 flex-col justify-center overflow-y-auto">
        <div role="group" aria-labelledby="suggestions-label" className="mx-auto flex w-full max-w-[720px] flex-col items-start gap-3 px-4 py-6 lg:px-6">
          <p id="suggestions-label" className="text-muted-foreground">
            {COPY.threadEmpty}
          </p>
          {SUGGESTED_QUESTIONS.map((question) => (
            <GuardedButton
              key={question}
              variant="outline"
              size="sm"
              reason={lockReason}
              onClick={() => send(question)}
              className="h-auto max-w-full py-1.5 text-left whitespace-normal"
            >
              {question}
            </GuardedButton>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className="grid flex-1 place-items-center px-4 text-center text-muted-foreground">
      <p>{COPY.threadEmpty}</p>
    </div>
  );
}
