"use client";

import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { AddFilesButton, SampleDocumentsButton } from "@/components/library";

// S5: an invitation with two clear actions, no illustration (UI_UX_BRIEF §4.2).
export function FirstVisit() {
  return (
    <Empty data-first-visit className="mx-auto max-w-[720px] px-4 lg:px-6">
      <EmptyHeader className="max-w-md">
        <EmptyTitle className="text-2xl font-bold">
          <h2>Add your course files to start</h2>
        </EmptyTitle>
        <EmptyDescription className="text-base">
          CourseMind answers questions from your PDFs, slides, and Word notes, and shows the page each answer came from.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="flex-row flex-wrap justify-center">
        <AddFilesButton />
        <SampleDocumentsButton />
      </EmptyContent>
    </Empty>
  );
}
