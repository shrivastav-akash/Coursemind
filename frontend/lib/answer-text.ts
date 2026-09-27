// Turns the streamed answer into blocks for display. Parsed from the whole accumulated text on
// every update, because citation markers arrive split across pieces ("[", "1", "]").
// ponytail: a small Markdown subset (paragraphs, lists, **bold**, *emphasis*, `code`, ``` blocks); a Markdown library if answers need more.

export type Inline = { text: string; bold?: boolean; code?: boolean } | { cite: number };
export type Block = { kind: "p"; inlines: Inline[] } | { kind: "ul" | "ol"; items: Inline[][] } | { kind: "code"; text: string };

const LIST_ITEM = /^\s*(?:([-*•])|(\d+)[.)])\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
const FENCE = /^\s*```/;
// **bold** and *emphasis*; both render as weight 700 (UI_UX_BRIEF §3.2: emphasis is weight, never a second style).
const EMPHASIS = /\*\*(.+?)\*\*|\*(\S(?:[^*]*\S)?)\*/g;
// [2], 【2】 (the model sometimes uses full-width brackets), and grouped forms like [1, 2].
const CITATION = /[[【]\s*(\d+(?:\s*[,，]\s*\d+)*)\s*[\]】]/g;
// `code` renders in the mono face (UI_UX_BRIEF §3.2). Code spans are set aside before emphasis and
// citations are parsed, so `*.swp` or `arr[1]` inside them stay literal.
const CODE = /`([^`\n]+)`/g;
const CODE_SLOT = /\u0000(\d+)\u0000/;

export function parseAnswer(text: string, sourceNumbers: ReadonlySet<number>): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: { kind: "ul" | "ol"; items: string[] } | null = null;
  let fence: string[] | null = null; // lines of an open ``` block; still open while streaming

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ kind: "p", inlines: parseInline(paragraph.join("\n"), sourceNumbers) });
    paragraph = [];
  };
  const flushList = () => {
    if (list) blocks.push({ kind: list.kind, items: list.items.map((item) => parseInline(item, sourceNumbers)) });
    list = null;
  };

  for (const raw of text.replace(/\r\n?/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    if (FENCE.test(line)) {
      if (fence) {
        blocks.push({ kind: "code", text: fence.join("\n") });
        fence = null;
      } else {
        flushParagraph();
        flushList();
        fence = [];
      }
      continue;
    }
    if (fence) {
      fence.push(line);
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    const item = LIST_ITEM.exec(line);
    // An indented line under a list item continues that item.
    if (!item && list && /^\s{2,}\S/.test(line)) {
      list.items[list.items.length - 1] += `\n${line.trim()}`;
      continue;
    }
    if (item) {
      flushParagraph();
      const kind = item[2] ? "ol" : "ul";
      if (list && list.kind !== kind) flushList();
      list ??= { kind, items: [] };
      list.items.push(item[3]);
      continue;
    }
    flushList();
    const heading = HEADING.exec(line);
    paragraph.push(heading ? `**${heading[1]}**` : line);
  }
  flushParagraph();
  flushList();
  if (fence) blocks.push({ kind: "code", text: fence.join("\n") });
  return blocks;
}

export function parseInline(text: string, sourceNumbers: ReadonlySet<number>): Inline[] {
  const codes: string[] = [];
  const masked = text.replace(CODE, (_, code: string) => `\u0000${codes.push(code) - 1}\u0000`);
  const out: Inline[] = [];
  let last = 0;
  for (const match of masked.matchAll(EMPHASIS)) {
    pushCitations(out, masked.slice(last, match.index), false, sourceNumbers);
    pushCitations(out, match[1] ?? match[2], true, sourceNumbers);
    last = match.index + match[0].length;
  }
  pushCitations(out, masked.slice(last), false, sourceNumbers);
  // Put the code spans back, each as its own part.
  return out.flatMap((part) =>
    "text" in part
      ? part.text.split(CODE_SLOT).flatMap((piece, i): Inline[] =>
          i % 2 ? [{ ...part, text: codes[Number(piece)], code: true }] : piece ? [{ ...part, text: piece }] : [],
        )
      : [part],
  );
}

function pushCitations(out: Inline[], text: string, bold: boolean, sourceNumbers: ReadonlySet<number>) {
  let last = 0;
  for (const match of text.matchAll(CITATION)) {
    const numbers = match[1].split(/[,，]/).map((n) => Number(n.trim()));
    if (!numbers.every((n) => sourceNumbers.has(n))) continue; // not a real source: leave as text
    pushText(out, text.slice(last, match.index), bold);
    for (const n of numbers) out.push({ cite: n });
    last = match.index + match[0].length;
  }
  pushText(out, text.slice(last), bold);
}

function pushText(out: Inline[], text: string, bold: boolean) {
  if (!text) return;
  const prev = out.at(-1);
  if (prev && "text" in prev && Boolean(prev.bold) === bold) prev.text += text;
  else out.push(bold ? { text, bold } : { text });
}
