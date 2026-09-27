"use client";

import type { Icon } from "@phosphor-icons/react";
import {
  ArrowClockwiseIcon,
  CheckCircleIcon,
  ClockIcon,
  FileIcon,
  PlusIcon,
  TrashIcon,
  WarningCircleIcon,
  XIcon,
} from "@phosphor-icons/react/ssr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Item, ItemActions, ItemContent, ItemDescription, ItemMedia, ItemTitle } from "@/components/ui/item";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { DOC_TYPE_ICON, FileName } from "@/components/file-name";
import { GuardedButton } from "@/components/guarded-button";
import { type LocalRow, useWorkspace } from "@/components/workspace-provider";
import { COPY, DOC_ERROR_COPY } from "@/lib/copy";
import { passages } from "@/lib/format";
import { MAX_DOCS_PER_WORKSPACE, MAX_FILE_MB } from "@/lib/limits";
import type { DocType, Document } from "@/lib/types";
import { cn } from "@/lib/utils";

export function LibraryCount() {
  const { documents } = useWorkspace();
  return (
    <span className="text-xs text-muted-foreground tabular-nums">
      {documents.length} of {MAX_DOCS_PER_WORKSPACE}
    </span>
  );
}

/** "Add files" opens the picker; used in the library and the first-visit state. */
export function AddFilesButton() {
  const { server, openPicker } = useWorkspace();
  return (
    <GuardedButton data-add-files reason={server === "ready" ? null : COPY.waitingForServer} onClick={openPicker}>
      <PlusIcon data-icon="inline-start" aria-hidden="true" />
      Add files
    </GuardedButton>
  );
}

export function SampleDocumentsButton() {
  const { server } = useWorkspace();
  // ponytail: wired to POST /documents/samples in step 15.
  return (
    <GuardedButton variant="outline" reason={server === "ready" ? null : COPY.waitingForServer}>
      Try sample documents
    </GuardedButton>
  );
}

// Panel body shared by the desktop column and the mobile sheet; each supplies its own heading.
export function Library() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-2">
          <AddFilesButton />
          <SampleDocumentsButton />
        </div>
        <p className="text-xs text-muted-foreground">PDF, .docx, .pptx, up to {MAX_FILE_MB}&nbsp;MB</p>
      </div>
      <Separator />
      <LibraryList />
    </div>
  );
}

function LibraryList() {
  const { documents, localRows, libraryState, reloadLibrary } = useWorkspace();
  if (libraryState === "loading" && localRows.length === 0) {
    return (
      <div aria-hidden="true" className="flex flex-col gap-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-start gap-2.5">
            <Skeleton className="size-4" />
            <div className="flex flex-1 flex-col gap-1.5">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (libraryState === "error") {
    return (
      <div className="flex flex-col items-start gap-2 text-sm">
        <p>{COPY.libraryLoadFailed}</p>
        <Button type="button" variant="outline" size="sm" onClick={reloadLibrary}>
          Try again
        </Button>
      </div>
    );
  }
  if (documents.length === 0 && localRows.length === 0) {
    return (
      <p data-first-visit className="text-sm text-muted-foreground">
        No documents yet.
      </p>
    );
  }
  return (
    <ul aria-label="Your documents" className="-mx-2 flex min-h-0 flex-col gap-1 overflow-y-auto overscroll-contain">
      {localRows.map((row) => (
        <li key={row.key}>
          <LocalLibraryRow row={row} />
        </li>
      ))}
      {documents.map((doc) => (
        <li key={doc.id}>
          <DocumentRow doc={doc} />
        </li>
      ))}
    </ul>
  );
}

function Row({
  name,
  type,
  sample,
  status,
  failed,
  action,
  flash,
}: {
  name: string;
  type: DocType | null;
  sample?: boolean;
  status: React.ReactNode;
  failed: boolean;
  action: React.ReactNode;
  flash?: boolean;
}) {
  const TypeIcon = type ? DOC_TYPE_ICON[type] : FileIcon;
  return (
    <Item size="sm" className={cn("items-start px-2", flash && "animate-row-flash")}>
      <ItemMedia variant="icon" className="pt-0.5 text-muted-foreground">
        <TypeIcon aria-hidden="true" />
      </ItemMedia>
      <ItemContent className="min-w-0 gap-0.5">
        <ItemTitle className="w-full min-w-0">
          <FileName name={name} />
          {sample && <Badge variant="secondary">Sample</Badge>}
        </ItemTitle>
        {/* Errors wrap in full, never truncated (UI_UX_BRIEF §4.4). */}
        <ItemDescription className={cn("text-xs", failed && "line-clamp-none text-destructive")}>
          <span className="flex items-start gap-1.5">{status}</span>
        </ItemDescription>
      </ItemContent>
      <ItemActions className="gap-0">{action}</ItemActions>
    </Item>
  );
}

function StatusLine({ icon, text, iconClass }: { icon: Icon | "spinner"; text: string; iconClass?: string }) {
  const StatusIcon = icon;
  return (
    <>
      {StatusIcon === "spinner" ? (
        <Spinner className="mt-px size-4 shrink-0" />
      ) : (
        <StatusIcon aria-hidden="true" className={cn("mt-px size-4 shrink-0", iconClass)} />
      )}
      <span>{text}</span>
    </>
  );
}

function DocumentRow({ doc }: { doc: Document }) {
  const { requestDelete, removeFailed, flashId } = useWorkspace();
  const status = {
    queued: <StatusLine icon={ClockIcon} text="Queued" />,
    processing: <StatusLine icon="spinner" text="Processing…" />,
    ready: <StatusLine icon={CheckCircleIcon} text={`Ready, ${passages(doc.chunks)}`} iconClass="text-success" />,
    failed: <StatusLine icon={WarningCircleIcon} text={DOC_ERROR_COPY[doc.error_code ?? "unreadable"]} />,
  }[doc.status];
  const busy = doc.status === "queued" || doc.status === "processing";
  const action =
    doc.status === "failed" ? (
      <Button type="button" variant="ghost" size="icon-sm" aria-label={`Remove ${doc.name}`} onClick={() => removeFailed(doc)}>
        <XIcon aria-hidden="true" />
      </Button>
    ) : (
      <GuardedButton
        variant="ghost"
        size="icon-sm"
        aria-label={`Delete ${doc.name}`}
        reason={busy ? "Wait until processing finishes." : null}
        onClick={() => requestDelete(doc)}
      >
        <TrashIcon aria-hidden="true" />
      </GuardedButton>
    );
  return (
    <Row
      name={doc.name}
      type={doc.type}
      sample={doc.is_sample}
      status={status}
      failed={doc.status === "failed"}
      action={action}
      flash={flashId === doc.id}
    />
  );
}

function LocalLibraryRow({ row }: { row: LocalRow }) {
  const { retryUpload, removeLocal } = useWorkspace();
  const status = {
    waiting: <StatusLine icon={ClockIcon} text="Waiting…" />,
    uploading: <StatusLine icon="spinner" text="Uploading…" />,
    failed: <StatusLine icon={WarningCircleIcon} text={row.message ?? ""} />,
  }[row.status];
  const action =
    row.status === "failed" ? (
      <>
        {row.retryable && (
          <Button type="button" variant="ghost" size="icon-sm" aria-label={`Retry ${row.name}`} onClick={() => retryUpload(row.key)}>
            <ArrowClockwiseIcon aria-hidden="true" />
          </Button>
        )}
        <Button type="button" variant="ghost" size="icon-sm" aria-label={`Remove ${row.name}`} onClick={() => removeLocal(row.key)}>
          <XIcon aria-hidden="true" />
        </Button>
      </>
    ) : null;
  return <Row name={row.name} type={row.type} status={status} failed={row.status === "failed"} action={action} />;
}
