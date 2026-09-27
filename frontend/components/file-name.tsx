import type { Icon } from "@phosphor-icons/react";
import { FileDocIcon, FilePdfIcon, FilePptIcon } from "@phosphor-icons/react/ssr";
import { cn } from "@/lib/utils";
import { splitName } from "@/lib/format";
import type { DocType } from "@/lib/types";

export const DOC_TYPE_ICON: Record<DocType, Icon> = { pdf: FilePdfIcon, docx: FileDocIcon, pptx: FilePptIcon };

// Long names truncate the stem but always keep the extension visible (UI_UX_BRIEF §4.1).
export function FileName({ name, className }: { name: string; className?: string }) {
  const [stem, ext] = splitName(name);
  return (
    <span translate="no" title={name} className={cn("flex min-w-0", className)}>
      <span className="truncate">{stem}</span>
      <span className="shrink-0">{ext}</span>
    </span>
  );
}
