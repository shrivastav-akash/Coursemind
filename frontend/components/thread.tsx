"use client";

import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { Message, MessageContent } from "@/components/ui/message";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import { AnswerBlock } from "@/components/answer";
import { useThread } from "@/components/thread-provider";
import { cn } from "@/lib/utils";

// The question sits in a small bubble; the answer is a full-width reading column, not a bubble (UI_UX_BRIEF §1).
export function Thread() {
  const { turns, announcement } = useThread();
  return (
    <MessageScrollerProvider autoScroll>
      <MessageScroller className="flex-1">
        <MessageScrollerViewport>
          <MessageScrollerContent className="mx-auto w-full max-w-[720px] gap-3 px-4 py-6 lg:px-6">
            {turns.flatMap((turn, i) => [
              <MessageScrollerItem key={`${turn.id}-q`} messageId={`${turn.id}-q`} scrollAnchor className={cn(i > 0 && "mt-5")}>
                <Message align="end">
                  <MessageContent>
                    <Bubble variant="muted" align="end">
                      <BubbleContent className="text-base whitespace-pre-line">{turn.question}</BubbleContent>
                    </Bubble>
                  </MessageContent>
                </Message>
              </MessageScrollerItem>,
              <MessageScrollerItem key={`${turn.id}-a`} messageId={`${turn.id}-a`}>
                <Message align="start">
                  <MessageContent>
                    <Bubble variant="ghost">
                      <BubbleContent className="overflow-visible text-base">
                        <AnswerBlock turn={turn} />
                      </BubbleContent>
                    </Bubble>
                  </MessageContent>
                </Message>
              </MessageScrollerItem>,
            ])}
          </MessageScrollerContent>
        </MessageScrollerViewport>
        <MessageScrollerButton />
      </MessageScroller>
      {/* One announcement per answer, not every word (APP_FLOW J12). */}
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
    </MessageScrollerProvider>
  );
}
