"use client";

import { ArrowUpIcon, StopIcon } from "@phosphor-icons/react/ssr";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupTextarea } from "@/components/ui/input-group";
import { useThread } from "@/components/thread-provider";
import { useWorkspace } from "@/components/workspace-provider";
import { ANSWER_COPY } from "@/lib/copy";
import { QUESTION_COUNTER_FROM, QUESTION_MAX_CHARS, QUESTION_MIN_CHARS } from "@/lib/limits";

export const QUESTION_BOX_ID = "question";

// UI_UX_BRIEF §5: grows to 6 lines, Enter sends, Shift+Enter adds a line, counter from 450, Stop while streaming.
export function QuestionBox() {
  const { lockReason } = useWorkspace();
  const { draft, setDraft, send, stop, streamingId } = useThread();
  const question = draft.trim();
  const tooShort = question.length > 0 && question.length < QUESTION_MIN_CHARS;
  const canSend = lockReason === null && question.length >= QUESTION_MIN_CHARS;
  const streaming = streamingId !== null;

  const submit = () => {
    if (canSend) send(question);
  };

  return (
    <form
      className="mx-auto w-full max-w-[720px] px-4 pt-2 pb-[max(1rem,env(safe-area-inset-bottom))] lg:px-6"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Field className="gap-1.5" data-invalid={tooShort || undefined}>
        <FieldLabel htmlFor={QUESTION_BOX_ID} className="sr-only">
          Ask a question about your documents
        </FieldLabel>
        <InputGroup className="rounded-xl bg-card dark:bg-card">
          <InputGroupTextarea
            id={QUESTION_BOX_ID}
            name="question"
            autoComplete="off"
            rows={1}
            maxLength={QUESTION_MAX_CHARS}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
            disabled={lockReason !== null}
            placeholder={lockReason ?? "Ask about your notes…"}
            aria-describedby="question-help"
            className="max-h-36 min-h-11 px-3 py-2.5 text-base"
          />
          <InputGroupAddon align="inline-end" className="self-end pb-1.5">
            {streaming ? (
              <InputGroupButton type="button" variant="default" size="icon-sm" aria-label="Stop answer" onClick={stop}>
                <StopIcon aria-hidden="true" />
              </InputGroupButton>
            ) : (
              <InputGroupButton type="submit" variant="default" size="icon-sm" disabled={!canSend} aria-label="Send question">
                <ArrowUpIcon aria-hidden="true" />
              </InputGroupButton>
            )}
          </InputGroupAddon>
        </InputGroup>
        {lockReason === null && (
          <FieldDescription id="question-help" className="flex justify-between gap-3 text-xs">
            <span>{tooShort ? ANSWER_COPY.tooShort : "Enter to send, Shift+Enter for a new line"}</span>
            {draft.length >= QUESTION_COUNTER_FROM && (
              <span className="tabular-nums">
                {draft.length} / {QUESTION_MAX_CHARS}
              </span>
            )}
          </FieldDescription>
        )}
      </Field>
    </form>
  );
}
