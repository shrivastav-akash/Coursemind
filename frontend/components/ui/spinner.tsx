import { cn } from "cn"
import { CircleNotchIcon, ClockIcon } from "@phosphor-icons/react/ssr"

// Decorative: every spinner sits next to status text that says what is happening (UI_UX_BRIEF §3.5).
// With reduced motion it becomes the static Clock icon (§3.6).
function Spinner({ className, ...props }: React.ComponentProps<"svg">) {
  return (
    <>
      <CircleNotchIcon data-slot="spinner" aria-hidden="true" className={cn("size-4 animate-spin motion-reduce:hidden", className)} {...props} />
      <ClockIcon aria-hidden="true" className={cn("size-4 motion-safe:hidden", className)} {...props} />
    </>
  )
}

export { Spinner }
