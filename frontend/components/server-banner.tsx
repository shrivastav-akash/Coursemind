"use client";

import { WarningCircleIcon } from "@phosphor-icons/react/ssr";
import { Alert, AlertAction, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useWorkspace } from "@/components/workspace-provider";
import { COPY } from "@/lib/copy";

// S12: only while the backend is starting or unreachable; neutral styling, never yellow (UI_UX_BRIEF §6).
export function ServerBanner() {
  const { server, retryServer } = useWorkspace();
  if (server !== "starting" && server !== "unreachable") return null;
  const unreachable = server === "unreachable";
  return (
    <div className="mx-auto w-full max-w-[720px] px-4 pt-4 lg:px-6">
      <Alert>
        {unreachable ? <WarningCircleIcon aria-hidden="true" /> : <Spinner />}
        <AlertDescription className="text-sm text-foreground">
          {unreachable ? COPY.serverUnreachable : COPY.serverStarting}
        </AlertDescription>
        {unreachable && (
          <AlertAction>
            <Button type="button" variant="outline" size="sm" onClick={retryServer}>
              Try again
            </Button>
          </AlertAction>
        )}
      </Alert>
    </div>
  );
}
