"use client";

import type { ComponentProps } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * A button that stays focusable while unavailable and says why in a tooltip (UI_UX_BRIEF §4.4, APP_FLOW J1).
 * `aria-disabled` instead of `disabled`, because disabled buttons get no hover or focus, so no tooltip.
 */
export function GuardedButton({
  reason,
  onClick,
  className,
  ...props
}: ComponentProps<typeof Button> & { reason: string | null }) {
  const button = (
    <Button
      type="button"
      {...props}
      aria-disabled={reason ? true : undefined}
      onClick={reason ? undefined : onClick}
      className={cn("aria-disabled:cursor-not-allowed aria-disabled:opacity-50", className)}
    />
  );
  if (!reason) return button;
  return (
    <Tooltip>
      <TooltipTrigger render={button} />
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  );
}
