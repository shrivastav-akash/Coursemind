// Run: npm test (Node's built-in runner; no test dependency).
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseAnswer, parseInline } from "./answer-text.ts";

const sources = new Set([1, 2, 3, 4]);

test("citations in square and full-width brackets, single and grouped", () => {
  assert.deepEqual(parseInline("Mutual exclusion [1]. Hold and wait 【2】 and [3, 4].", sources), [
    { text: "Mutual exclusion " },
    { cite: 1 },
    { text: ". Hold and wait " },
    { cite: 2 },
    { text: " and " },
    { cite: 3 },
    { cite: 4 },
    { text: "." },
  ]);
});

test("numbers that are not sources stay as text", () => {
  assert.deepEqual(parseInline("See [7] and [2, 9] and [x].", sources), [{ text: "See [7] and [2, 9] and [x]." }]);
});

test("a marker split across stream pieces becomes a citation once complete", () => {
  assert.deepEqual(parseInline("Deadlock [", sources), [{ text: "Deadlock [" }]);
  assert.deepEqual(parseInline("Deadlock [1", sources), [{ text: "Deadlock [1" }]);
  assert.deepEqual(parseInline("Deadlock [1]", sources), [{ text: "Deadlock " }, { cite: 1 }]);
});

test("bold keeps its citations; an unclosed ** stays literal while streaming", () => {
  assert.deepEqual(parseInline("**Circular wait [4]** closes it.", sources), [
    { text: "Circular wait ", bold: true },
    { cite: 4 },
    { text: " closes it." },
  ]);
  assert.deepEqual(parseInline("A **partial", sources), [{ text: "A **partial" }]);
});

test("paragraphs, numbered and bulleted lists, headings", () => {
  const text = "The four conditions are:\n\n1. **Mutual exclusion** [1]  \n2. Hold and wait [2]\n\n- One\n* Two\n\n### Summary\nAll four at once.";
  assert.deepEqual(parseAnswer(text, sources), [
    { kind: "p", inlines: [{ text: "The four conditions are:" }] },
    {
      kind: "ol",
      items: [
        [{ text: "Mutual exclusion", bold: true }, { text: " " }, { cite: 1 }],
        [{ text: "Hold and wait " }, { cite: 2 }],
      ],
    },
    { kind: "ul", items: [[{ text: "One" }], [{ text: "Two" }]] },
    { kind: "p", inlines: [{ text: "Summary", bold: true }, { text: "\nAll four at once." }] },
  ]);
});

test("the refusal sentence is one plain paragraph", () => {
  assert.deepEqual(parseAnswer("I couldn't find that in your notes.", new Set()), [
    { kind: "p", inlines: [{ text: "I couldn't find that in your notes." }] },
  ]);
});

test("single-asterisk emphasis renders as bold; stray asterisks stay text", () => {
  assert.deepEqual(parseInline("a *weight* field", sources), [
    { text: "a " },
    { text: "weight", bold: true },
    { text: " field" },
  ]);
  assert.deepEqual(parseInline("2 * 3 * 4", sources), [{ text: "2 * 3 * 4" }]);
});

test("an indented line continues the list item above it", () => {
  const text = "- Stores globs in a **GlobList**.  \n  Each entry has a weight [2].\n- Banker's algorithm [4]";
  assert.deepEqual(parseAnswer(text, sources), [
    {
      kind: "ul",
      items: [
        [{ text: "Stores globs in a " }, { text: "GlobList", bold: true }, { text: ".\nEach entry has a weight " }, { cite: 2 }, { text: "." }],
        [{ text: "Banker's algorithm " }, { cite: 4 }],
      ],
    },
  ]);
});

test("inline code keeps its brackets and asterisks literal, inside bold too", () => {
  assert.deepEqual(parseInline("Run `git stash` then `arr[1]` [2].", sources), [
    { text: "Run " },
    { text: "git stash", code: true },
    { text: " then " },
    { text: "arr[1]", code: true },
    { text: " " },
    { cite: 2 },
    { text: "." },
  ]);
  assert.deepEqual(parseInline("**Recovering with `git reflog`**", sources), [
    { text: "Recovering with ", bold: true },
    { text: "git reflog", bold: true, code: true },
  ]);
  // Asterisks inside code are not emphasis (.gitignore patterns).
  assert.deepEqual(parseInline("Add `/logs/*`, `/tmp`, and `*.swp` [3].", sources), [
    { text: "Add " },
    { text: "/logs/*", code: true },
    { text: ", " },
    { text: "/tmp", code: true },
    { text: ", and " },
    { text: "*.swp", code: true },
    { text: " " },
    { cite: 3 },
    { text: "." },
  ]);
  // Unclosed while streaming: stays literal until the closing backtick arrives.
  assert.deepEqual(parseInline("Use `git sta", sources), [{ text: "Use `git sta" }]);
});

test("fenced code blocks keep their lines and are not parsed; an open fence is code while streaming", () => {
  assert.deepEqual(parseAnswer("Add this [1]:\n\n```\n*.swp\n\n/tmp\n```\nDone.", sources), [
    { kind: "p", inlines: [{ text: "Add this " }, { cite: 1 }, { text: ":" }] },
    { kind: "code", text: "*.swp\n\n/tmp" },
    { kind: "p", inlines: [{ text: "Done." }] },
  ]);
  assert.deepEqual(parseAnswer("Try:\n```gitignore\n.env", sources), [
    { kind: "p", inlines: [{ text: "Try:" }] },
    { kind: "code", text: ".env" },
  ]);
});
