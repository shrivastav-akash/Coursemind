"use client";

import { Fragment, useMemo, useState } from "react";
import { ArrowClockwiseIcon, CaretDownIcon, WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Spinner } from "@/components/ui/spinner";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { FileName } from "@/components/file-name";
import { AddFilesButton } from "@/components/library";
import { useThread } from "@/components/thread-provider";
import { useWorkspace } from "@/components/workspace-provider";
import { type Block, type Inline, parseAnswer } from "@/lib/answer-text";
import { ANSWER_COPY } from "@/lib/copy";
import { citationLabel, displayLocation } from "@/lib/format";
import type { Source, Turn } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_STAGGERED_ROWS = 6; // UI_UX_BRIEF §3.6: sources fade in 40 ms apart, max 6

// S8: progress line, streamed text with inline citations, sources, and the end state (UI_UX_BRIEF §4.3).
export function AnswerBlock({ turn }: { turn: Turn }) {
  const [open, setOpen] = useState<ReadonlySet<number>>(new Set());
  const sources = useMemo(() => turn.sources ?? [], [turn.sources]);
  const numbers = useMemo(() => new Set(sources.map((s) => s.n)), [sources]);
  const blocks = useMemo(() => parseAnswer(turn.text, numbers), [turn.text, numbers]);
  const streaming = turn.status === "searching" || turn.status === "writing";

  const toggle = (n: number, reveal: boolean) => {
    const opening = !open.has(n);
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
    // From a citation: bring the passage into view only if it is off screen (UI_UX_BRIEF §5).
    if (opening && reveal) {
      requestAnimationFrame(() => document.getElementById(sourceId(turn, n))?.scrollIntoView({ block: "nearest" }));
    }
  };

  return (
    <div aria-busy={streaming} className="flex max-w-[68ch] flex-col gap-4">
      {streaming && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner />
          {turn.sources ? ANSWER_COPY.found(sources.length) : ANSWER_COPY.searching(turn.searching)}
        </p>
      )}
      {turn.text && (
        <AnswerText
          blocks={blocks}
          sources={sources}
          open={open}
          onCite={(n) => toggle(n, true)}
          caret={turn.status === "writing"}
        />
      )}
      {turn.refused && <p className="text-sm text-muted-foreground">{ANSWER_COPY.refusalHint}</p>}
      <EndNote turn={turn} />
      {/* A refusal lists no sources, so nothing misleading can be opened (APP_FLOW J5). */}
      {sources.length > 0 && !turn.refused && (
        <SourceList turn={turn} sources={sources} open={open} onToggle={(n) => toggle(n, false)} />
      )}
    </div>
  );
}

function EndNote({ turn }: { turn: Turn }) {
  const { retry } = useThread();
  if (turn.status !== "stopped" && turn.status !== "error") return null;
  const error = turn.status === "error" ? turn.error : undefined;
  const canRetry = turn.status === "stopped" || error?.retry;
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <p className={cn("flex items-center gap-1.5", error ? "text-destructive" : "text-muted-foreground")}>
        {error && <WarningCircleIcon aria-hidden="true" className="size-4 shrink-0" />}
        {error ? error.message : ANSWER_COPY.stopped}
      </p>
      {canRetry && (
        <Button type="button" variant="outline" size="sm" onClick={() => retry(turn.id)}>
          <ArrowClockwiseIcon data-icon="inline-start" aria-hidden="true" />
          Retry
        </Button>
      )}
      {error?.addFiles && <AddFilesButton />}
    </div>
  );
}

function AnswerText({
  blocks,
  sources,
  open,
  onCite,
  caret,
}: {
  blocks: Block[];
  sources: Source[];
  open: ReadonlySet<number>;
  onCite: (n: number) => void;
  caret: boolean;
}) {
  const byNumber = new Map(sources.map((s) => [s.n, s]));
  const renderInlines = (inlines: Inline[], withCaret: boolean) => (
    <>
      {inlines.map((part, i) => {
        if ("cite" in part) {
          const source = byNumber.get(part.cite);
          return source ? <Citation key={i} source={source} open={open.has(part.cite)} onClick={() => onCite(part.cite)} /> : null;
        }
        return part.bold ? (
          <strong key={i} className="font-bold">
            {part.text}
          </strong>
        ) : (
          <Fragment key={i}>{part.text}</Fragment>
        );
      })}
      {withCaret && <Caret />}
    </>
  );
  // Answer prose is ink; only text from the student's own documents is yellow (UI_UX_BRIEF §1).
  return (
    <div className="flex flex-col gap-3 text-reading">
      {blocks.map((block, b) => {
        const last = caret && b === blocks.length - 1;
        if (block.kind === "p") {
          return (
            <p key={b} className="whitespace-pre-line text-pretty">
              {renderInlines(block.inlines, last)}
            </p>
          );
        }
        const List = block.kind === "ol" ? "ol" : "ul";
        return (
          <List key={b} className={cn("flex flex-col gap-1 pl-6", block.kind === "ol" ? "list-decimal" : "list-disc")}>
            {block.items.map((item, i) => (
              <li key={i} className="whitespace-pre-line text-pretty">
                {renderInlines(item, last && i === block.items.length - 1)}
              </li>
            ))}
          </List>
        );
      })}
    </div>
  );
}

function Caret() {
  return <span aria-hidden="true" className="ml-0.5 inline-block h-[1.1em] w-0.5 translate-y-[0.2em] animate-caret bg-foreground" />;
}

function Citation({ source, open, onClick }: { source: Source; open: boolean; onClick: () => void }) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            type="button"
            variant="evidence"
            size="xs"
            aria-expanded={open}
            aria-label={`Source ${source.n}: ${source.doc_name}, ${source.location}`}
            className="mx-0.5 align-baseline text-sm"
            onClick={onClick}
          />
        }
      >
        <span translate="no">{citationLabel(source.doc_name, source.location)}</span>
      </TooltipTrigger>
      <TooltipContent>
        <span translate="no">{source.doc_name}</span>
      </TooltipContent>
    </Tooltip>
  );
}

const sourceId = (turn: Turn, n: number) => `source-${turn.id}-${n}`;

function SourceList({
  turn,
  sources,
  open,
  onToggle,
}: {
  turn: Turn;
  sources: Source[];
  open: ReadonlySet<number>;
  onToggle: (n: number) => void;
}) {
  const { documents } = useWorkspace();
  const inLibrary = new Set(documents.map((d) => d.id));
  return (
    <section aria-label="Sources" className="flex flex-col gap-1">
      <h3 className="text-sm font-bold">Sources</h3>
      <ol className="flex flex-col">
        {sources.map((source, i) => (
          <li
            key={source.n}
            id={sourceId(turn, source.n)}
            className="animate-source-in"
            style={{ animationDelay: `${Math.min(i, MAX_STAGGERED_ROWS - 1) * 40}ms` }}
          >
            <Collapsible open={open.has(source.n)} onOpenChange={() => onToggle(source.n)}>
              <CollapsibleTrigger
                aria-label={`Source ${source.n}: ${source.doc_name}, ${source.location}`}
                className="group/source flex min-h-10 w-full items-center gap-3 rounded-lg px-2 text-left text-sm transition-colors duration-[120ms] outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <span className="w-4 shrink-0 text-muted-foreground tabular-nums">{source.n}</span>
                <FileName name={source.doc_name} className="font-medium" />
                <span className="shrink-0 text-xs text-muted-foreground">{displayLocation(source.location)}</span>
                <CaretDownIcon
                  aria-hidden="true"
                  className="ml-auto size-4 shrink-0 text-muted-foreground transition-transform duration-[180ms] group-data-[panel-open]/source:rotate-180"
                />
              </CollapsibleTrigger>
              <CollapsibleContent className="h-(--collapsible-panel-height) overflow-hidden transition-[height,opacity] duration-[180ms] ease-[cubic-bezier(0.2,0,0,1)] data-ending-style:h-0 data-ending-style:opacity-0 data-ending-style:duration-[140ms] data-starting-style:h-0 data-starting-style:opacity-0">
                <blockquote className="my-1 ml-9 rounded-r-lg border-l-3 border-evidence bg-evidence-tint px-3 py-2 text-reading whitespace-pre-line text-pretty">
                  {source.text}
                </blockquote>
                {!inLibrary.has(source.doc_id) && (
                  <p className="mb-1 ml-9 text-xs text-muted-foreground">{ANSWER_COPY.sourceRemoved}</p>
                )}
              </CollapsibleContent>
            </Collapsible>
          </li>
        ))}
      </ol>
    </section>
  );
}
