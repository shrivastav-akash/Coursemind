import type { Metadata } from "next";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Page not found" };

// S13: static 404 with one way back (APP_FLOW §1).
export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center p-6">
      <div className="flex max-w-sm flex-col items-center gap-4 text-center">
        <p translate="no" className="text-xl leading-6 font-extrabold tracking-[-0.01em]">
          CourseMind
        </p>
        <h1 className="text-2xl font-bold">This page doesn’t exist.</h1>
        <Link href="/" className={buttonVariants()}>
          Go to CourseMind
        </Link>
      </div>
    </main>
  );
}
