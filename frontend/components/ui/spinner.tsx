import { cn } from "cn"
import { CircleNotchIcon } from "@phosphor-icons/react/ssr"

// Decorative: every spinner sits next to status text that says what is happening (UI_UX_BRIEF §3.5).
function Spinner({ className, ...props }: React.ComponentProps<"svg">) {
  return (
    <CircleNotchIcon data-slot="spinner" aria-hidden="true" className={cn("size-4 animate-spin", className)} {...props} />
  )
}

export { Spinner }
