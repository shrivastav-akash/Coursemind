// Turns the streamed answer into blocks for display. Parsed from the whole accumulated text on
// every update, because citation markers arrive split across pieces ("[", "1", "]").
// ponytail: a small Markdown subset (paragraphs, lists, **bold**, *emphasis*); a Markdown library if answers need more.

export type Inline = { text: string; bold?: boolean } | { cite: number };
export type Block = { kind: "p"; inlines: Inline[] } | { kind: "ul" | "ol"; items: Inline[][] };

const LIST_ITEM = /^\s*(?:([-*•])|(\d+)[.)])\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
// **bold** and *emphasis*; both render as weight 700 (UI_UX_BRIEF §3.2: emphasis is weight, never a second style).
const EMPHASIS = /\*\*(.+?)\*\*|\*(\S(?:[^*]*\S)?)\*/g;
// [2], 【2】 (the model sometimes uses full-width brackets), and grouped forms like [1, 2].
const CITATION = /[[【]\s*(\d+(?:\s*[,，]\s*\d+)*)\s*[\]】]/g;

export function parseAnswer(text: string, sourceNumbers: ReadonlySet<number>): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: { kind: "ul" | "ol"; items: string[] } | null = null;

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
  return blocks;
}

export function parseInline(text: string, sourceNumbers: ReadonlySet<number>): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const match of text.matchAll(EMPHASIS)) {
    pushCitations(out, text.slice(last, match.index), false, sourceNumbers);
    pushCitations(out, match[1] ?? match[2], true, sourceNumbers);
    last = match.index + match[0].length;
  }
  pushCitations(out, text.slice(last), false, sourceNumbers);
  return out;
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
