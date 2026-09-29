"use client";

import { ArrowSquareOutIcon, CheckCircleIcon, WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { Library, LibraryCount } from "@/components/library";
import { useWorkspace } from "@/components/workspace-provider";

const HOW_IT_WORKS = "https://github.com/shrivastav-akash/coursemind#readme";

function HowItWorks() {
  return (
    <a
      href={HOW_IT_WORKS}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm pointer-coarse:min-h-11 text-muted-foreground underline-offset-4 transition-colors duration-[120ms] outline-none hover:text-foreground hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      How it works
      <ArrowSquareOutIcon aria-hidden="true" className="size-4" />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

// Header indicator for GET /status (APP_FLOW §2); the banner in the thread carries the details.
function ServerStatus() {
  const { server } = useWorkspace();
  return (
    <p role="status" className="flex items-center gap-1.5 text-xs text-muted-foreground">
      {server === "ready" && (
        <>
          <CheckCircleIcon aria-hidden="true" className="size-4 text-success" />
          Connected
        </>
      )}
      {(server === "checking" || server === "starting") && (
        <>
          <Spinner className="size-4" />
          Starting server…
        </>
      )}
      {server === "unreachable" && (
        <>
          <WarningCircleIcon aria-hidden="true" className="size-4 text-destructive" />
          Can’t reach the server
        </>
      )}
    </p>
  );
}

export function AppHeader() {
  const { documents } = useWorkspace();
  return (
    <header className="flex min-h-14 shrink-0 items-center justify-between gap-3 border-b px-4 py-2 lg:px-6">
      <span translate="no" className="text-xl leading-6 font-extrabold tracking-[-0.01em]">
        CourseMind
      </span>
      <div className="hidden items-center gap-4 lg:flex">
        <HowItWorks />
        <ServerStatus />
      </div>
      {/* Below 1024 px the library lives in a sheet (UI_UX_BRIEF §4.5). */}
      <div className="flex flex-col items-end gap-1 lg:hidden">
        <Sheet>
          <SheetTrigger render={<Button type="button" variant="outline" size="sm" />}>
            Documents <span className="text-muted-foreground tabular-nums">{documents.length}</span>
          </SheetTrigger>
          <SheetContent
            side="left"
            className="gap-0 overscroll-contain data-[side=left]:w-[88vw] data-[side=left]:max-w-[360px] data-[side=left]:sm:max-w-[360px]"
          >
            <SheetHeader className="flex-row items-baseline gap-3 pr-12">
              <SheetTitle className="text-xl font-bold">Documents</SheetTitle>
              <LibraryCount />
            </SheetHeader>
            <div className="flex min-h-0 flex-1 flex-col gap-4 px-4 pb-4">
              <Library />
              <HowItWorks />
            </div>
          </SheetContent>
        </Sheet>
        <ServerStatus />
      </div>
    </header>
  );
}
