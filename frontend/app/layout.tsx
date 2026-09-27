import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible_Mono, Atkinson_Hyperlegible_Next } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";

// Built to keep look-alike characters apart (I l 1, 0 O), which course notes are full of (UI_UX_BRIEF §3.2).
const sans = Atkinson_Hyperlegible_Next({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = Atkinson_Hyperlegible_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CourseMind",
  description:
    "Ask questions across your PDF, Word, and PowerPoint course notes and get answers that cite the page, slide, or section.",
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F8FA" },
    { media: "(prefers-color-scheme: dark)", color: "#121826" },
  ],
};

// Runs before first paint: a returning visitor must not glimpse the prerendered first-visit
// state while their library loads. Mirrors lib/workspace.ts (key and UUID v4 check).
const RETURNING_SCRIPT = `try{if(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(localStorage.getItem("coursemind.workspace")||""))document.documentElement.dataset.returning=""}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // The script above adds data-returning before hydration, so React must not flag it.
    <html lang="en" className={cn("h-full antialiased", sans.variable, mono.variable)} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: RETURNING_SCRIPT }} />
      </head>
      <body className="h-full">
        <TooltipProvider>
          <Toaster>{children}</Toaster>
        </TooltipProvider>
      </body>
    </html>
  );
}
