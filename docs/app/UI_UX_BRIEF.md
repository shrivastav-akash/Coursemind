# CourseMind — UI/UX Brief

**Status:** Draft v1 · **Date:** 2026-09-27 · **Based on:** PRD v2, TRD v1, [APP_FLOW.md](APP_FLOW.md)

How CourseMind looks and feels. This brief is the design source of truth until a `DESIGN.md` exists; build tokens straight from §3.

---

## 0. Design read

**Reading this as:** a focused study tool (product UI, not a landing page) for university students revising from their own course files, and for technical reviewers judging the build. The language is calm, precise, and evidence-first. The build uses customized shadcn/ui on Tailwind v4 with Phosphor icons.

**Dials** (1–10): variance **3** (predictable, trustworthy layout) · motion **3** (only motion that explains a change) · density **5** (standard app spacing).

**How the design guidance was combined**

| Source | What we took | What we rejected, and why |
|---|---|---|
| frontend-design | Ground the look in the subject (paper, ink, highlighter). Spend boldness in one place. Plain, specific copy. | Its list of AI-default looks: cream + terracotta, near-black + acid green, SaaS card grids, all-caps eyebrows. We avoid all of them. |
| ui-ux-pro-max | Swiss / minimal structure, accessibility-first priorities, streaming over spinners, determinate progress, stable layouts (no content jumping). | Its generated palette and type (`#2563EB` blue + Inter). This is the generic SaaS default, the same for every product. |
| Apple HIG | Follow the system light/dark setting. Put status next to the item it describes. Give specific progress text. Let people stop long work. Confirm irreversible deletes. Teach by doing (sample documents + suggested questions). | Platform chrome (Liquid Glass, SF Symbols). They belong to Apple platforms, not this web app. |
| shadcn/ui | Component map (§6), semantic color tokens, chat primitives, `Empty`, `Skeleton`, `AlertDialog`, `Sheet`. | Its default look. Every token is overridden (§3). |
| web-design-guidelines | Focus, forms, typography, content, and anti-pattern checklist (§9). | Title Case for buttons. We use sentence case (friendlier for students; matches HIG and frontend-design writing guidance). |
| taste-skill | Anti-slop rules that apply to product UI: one accent, a documented radius system, no em dashes in UI copy, no Inter default, no decorative dots, Phosphor icons, both modes designed. | Its landing-page rules (hero, bento, marquee, imagery). Out of scope for a product screen. |

---

## 1. Look and tone

**Three words:** calm, precise, evidential.

It should feel like a well-kept study desk: clean paper, dark ink, and one highlighter. Nothing sparkles, glows, or pretends to be a person. The product's personality comes from **how clearly it shows its evidence**, not from decoration.

**References (what to take, what not to copy)**

| Reference | Take | Don't copy |
|---|---|---|
| NotebookLM | Sources panel next to a grounded chat; citations that open the passage. | The Material look and the generated-audio features. |
| Perplexity | Sources arriving before the answer; numbered citations the reader can trust. | Dark teal look, card carousels of sources. |
| Readwise Reader | The highlight as a first-class visual; calm reading typography. | Dense toolbars and reader chrome. |
| Linear | Restraint: status shown with a small icon and a few words, no noise. | Its dark-first purple styling. |

**Signature (the one bold thing): yellow means evidence.** Highlighter yellow appears **only** on text that comes from the student's own documents: inline citations, active citations, and expanded source passages. Everything the model writes is ink. Nothing else in the UI is yellow (no yellow buttons, warnings, or badges). A student learns in one answer: "yellow = I can check this."

**Principles**
1. **Yellow means evidence.** Never spend the accent on anything else.
2. **An answer is a document, not a chat bubble.** Answers are full-width reading text in a comfortable column. Only the student's question sits in a small bubble.
3. **Status lives next to the thing.** File status is on the file row; answer errors are on the answer. No generic alerts.
4. **Quiet by default.** Flat surfaces, borders for structure, motion only when something changed.
5. **Readable for long sessions.** Legible type built to tell `I l 1` and `0 O` apart, generous line height, follows the system's light or dark setting.

---

## 2. Mobile-first or desktop-first?

**Desktop-first design, mobile-first code.**

- **Design priority is desktop.** Students study with their files on a laptop, and reviewers open the link on a laptop. The core composition is a split view: library and answers side by side, so evidence and questions are visible together.
- **Implementation is mobile-first.** Tailwind base styles target small screens. The split view switches on at `lg` (1024 px). Mobile is fully supported: the thread fills the screen and the library opens as a sheet (APP_FLOW J11).
- Supported widths: 320 px to 1920 px. No horizontal scroll at any width or at 200% zoom.

| Range | Layout |
|---|---|
| < 1024 px | Single column. Header with **Documents (n)** button. Library in a left `Sheet`. |
| 1024–1279 px | Split view. Library 320 px, thread fluid. |
| ≥ 1280 px | Split view. Library 360 px, thread fluid; reading column capped (§3.3). |

---

## 3. Design tokens

### 3.1 Color

One neutral family (cool blue-grey), one accent (highlighter), two status colors. Tokens use shadcn's semantic names so components pick them up without overrides.

| Token (shadcn name) | Role | Light | Dark |
|---|---|---|---|
| `--background` | Paper (page) | `#F7F8FA` | `#121826` |
| `--card`, `--popover` | Surface (panels, inputs, dialogs) | `#FFFFFF` | `#1A2233` |
| `--foreground` | Ink (text, icons) | `#172033` | `#E8ECF3` |
| `--muted-foreground` | Graphite (secondary text) | `#5B6474` | `#9AA4B5` |
| `--secondary`, `--muted`, `--accent` | Soft fill (hover rows, question bubble) | `#EEF1F5` | `#212B3D` |
| `--border` | Rules and dividers (decorative) | `#DDE1E8` | `#2A3447` |
| `--input` | Control borders (inputs, drop zone) | `#7C8698` | `#6B7587` |
| `--primary` / `--primary-foreground` | Primary button (ink on paper) | `#172033` / `#F7F8FA` | `#E8ECF3` / `#121826` |
| `--ring` | Focus ring | `#172033` | `#E8ECF3` |
| `--evidence` / `--evidence-foreground` | Highlighter mark (citations) | `#FFE45C` / `#172033` | `#EBD452` / `#121826` |
| `--evidence-strong` | Active citation | `#F5CF1F` | `#FFE45C` |
| `--evidence-tint` | Expanded passage background | `#FFF6C2` | `#3B3A1E` |
| `--destructive` | Failed status, delete | `#B42318` | `#F97066` |
| `--success` | Ready status | `#1F7A4D` | `#4CC38A` |

`--evidence*` and `--success` are new tokens added to the shadcn theme. Why these hues: the paper is cool white (not cream) so the yellow reads as a real highlighter mark. The ink is blue-black like fountain-pen ink. The dark background is "ink bottle" blue-black, not neutral black, so both modes feel like the same desk.

**Measured contrast (WCAG 2.x)**

| Pair | Light | Dark | Needs |
|---|---|---|---|
| Ink on paper | 15.3 | 15.0 | 4.5 |
| Ink on surface | 16.3 | 13.4 | 4.5 |
| Graphite on paper | 5.6 | 7.1 | 4.5 |
| Graphite on surface | 6.0 | 6.3 | 4.5 |
| Mark text on evidence | 12.8 | 11.9 | 4.5 |
| Mark text on evidence-strong | 10.7 | 13.9 | 4.5 |
| Text on evidence-tint | 14.9 | 9.8 | 4.5 |
| Destructive on surface | 6.6 | 5.7 | 4.5 |
| Success on surface | 5.3 | 7.2 | 4.5 |
| Primary button text | 15.3 | 15.0 | 4.5 |
| Control border on paper / surface | 3.5 / 3.7 | 3.8 / 3.4 | 3.0 (non-text) |

Dividers (`--border`) are decorative and intentionally low contrast; anything interactive uses `--input`.

**Appearance:** follow the operating system (`prefers-color-scheme`). No in-app theme toggle (Apple HIG: app-specific appearance settings make people adjust two places). Set `color-scheme: light dark` on `<html>` and a `theme-color` meta for each scheme.

### 3.2 Typography

| Role | Family | Why |
|---|---|---|
| Everything (UI, answers, headings) | **Atkinson Hyperlegible Next** (variable, 200–800) | Built by the Braille Institute to keep look-alike characters distinct (`I l 1`, `0 O`, `rn m`). Course notes are full of these (`3NF`, `O(n log n)`, `P1`, `l1`). Not a default SaaS face, and it has a clear reason to exist here. |
| Code inside passages or answers only | **Atkinson Hyperlegible Mono** | Same design family, so code sits comfortably inside text. Never used for labels or metadata. |

Load both with `next/font/google` (self-hosted at build, works with static export, `display: swap`).

**Scale** (16 px base, ratio ≈ 1.2):

| Step | Size / line height | Weight | Use |
|---|---|---|---|
| Caption | 13 / 18 | 400 | Library row meta, source location, counters |
| Small | 14 / 20 | 400–500 | Buttons, library file names, helper text |
| Body | 16 / 24 | 400 | UI text, question bubble |
| Reading | 17 / 27 (1.6) | 400 | Answer text and expanded passages |
| Heading S | 20 / 26 | 700 | Panel titles ("Documents") |
| Heading M | 24 / 30 | 700 | Empty-state heading |
| Wordmark | 20 / 24 | 800, −0.01em | "CourseMind" in the header |

**Rules**
- Answer column max width 68 characters (≈ 680 px at 17 px). Passages use the same width.
- Sentence case everywhere. No all-caps labels. No eyebrow labels above headings.
- Emphasis inside answers uses weight 700 of the same family, never a second family or color.
- `text-wrap: pretty` on answer paragraphs, `balance` on headings.
- `font-variant-numeric: tabular-nums` on counts ("3 of 30 documents", "480 / 500", "128 passages").
- Typographic characters in UI copy: `…` (one character), curly quotes and apostrophes, non-breaking space in `25 MB` and `p. 12`.

### 3.3 Spacing and layout

- **Base unit 4 px.** Scale: 4, 8, 12, 16, 24, 32, 48, 64.
- **Header:** 56 px high, full width, bottom border.
- **Library panel:** 320 px (≥ 1280 px: 360 px), right border, padding 16 px. Rows 56 px (two lines), 64 px on touch.
- **Thread:** reading column centered in the remaining space, max 720 px, side padding 24 px desktop, 16 px mobile. 32 px between question/answer pairs, 12 px between a question and its answer.
- **Question box:** pinned to the bottom of the thread column, same 720 px width, 16 px from the bottom edge (plus safe-area inset on mobile).
- **Alignment:** everything left-aligned. Only empty states center their content inside the thread area.

### 3.4 Shape, borders, elevation

**Radius rule (documented, applied everywhere):**
- **4 px:** evidence marks and badges (they read like highlighter strokes).
- **8 px:** buttons, inputs, list rows (hover), suggested-question buttons.
- **12 px:** panels, question box, dialogs, sheets, question bubble.
- Nothing is fully rounded (no pills).

**Elevation:** flat. Structure comes from 1 px borders and spacing, not shadows. Shadows exist only on overlays (dialog, sheet, toast, tooltip): `0 8px 24px rgb(23 32 51 / 0.12)` light, `0 8px 24px rgb(0 0 0 / 0.4)` dark. No blur or glass effects.

### 3.5 Icons

**Phosphor Icons**, regular weight. 20 px in controls, 16 px inline. One family only.

| Meaning | Icon |
|---|---|
| PDF / Word / PowerPoint | `FilePdf` / `FileDoc` / `FilePpt` |
| Queued / processing / ready / failed | `Clock` / `CircleNotch` (spinning) / `CheckCircle` / `WarningCircle` |
| Add files, delete, retry | `Plus`, `Trash`, `ArrowClockwise` |
| Send, stop | `ArrowUp`, `Stop` |
| Expand source | `CaretDown` |
| External link ("How it works") | `ArrowSquareOut` |

Icons never carry meaning alone: every status icon has text next to it; every icon-only button has an `aria-label`. No robot, sparkle, or "AI" glyphs anywhere.

### 3.6 Motion

Motion only explains a change. Durations are short; exits are faster than entrances. Animate `opacity` and `transform` only (except the collapsible height, which uses the component's built-in height variable).

| Moment | Motion | Duration / easing |
|---|---|---|
| Hover, press | Color change; buttons scale to 0.98 on press | 120 ms, ease-out |
| Source expand / collapse | Height + fade | 180 ms in, 140 ms out, `cubic-bezier(0.2, 0, 0, 1)` |
| **Sources arrive** (the one orchestrated moment) | Source rows fade in top to bottom, 40 ms apart, max 6 | 160 ms each |
| Streaming | Text appends as it arrives; a 2 px ink caret blinks at the end | Caret 1 s blink; removed on done |
| File status change | Status text crossfades | 150 ms |
| Duplicate file | Existing row background flashes `--secondary` and fades | 1.2 s, once |
| Sheet | Slides from left | 240 ms in, 180 ms out |
| Dialog, toast | Fade + scale from 0.98 | 160 ms in, 120 ms out |

**Not allowed:** page-load animations, scroll reveals, typewriter effects that replay text already received, infinite loops other than the spinner and caret.

**Reduced motion:** all of the above become instant; the caret stops blinking; the spinner is replaced by the static `Clock` icon plus "Processing…".

---

## 4. Key screens

Wireframes use real copy. `▓` marks highlighter yellow (evidence only). Symbols stand in for Phosphor icons: `▢` file type, `🗑` Trash, `✓` CheckCircle, `◌` spinner, `✕` remove, `↗` external link, `(↑)` send.

### 4.1 Desktop: answer with a source open (S1, S8, S9)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ CourseMind                                   How it works ↗        ✓ Connected       │
├───────────────────────────────┬──────────────────────────────────────────────────────┤
│ Documents        3 of 30      │                                                      │
│                               │                     ╭──────────────────────────────╮ │
│ [+ Add files]                 │                     │ What is the difference       │ │
│ [Try sample documents]        │                     │ between 2NF and 3NF?         │ │
│ PDF, .docx, .pptx, up to 25 MB│                     ╰──────────────────────────────╯ │
│ ───────────────────────────── │                                                      │
│ ▢ OS_Lecture3.pdf        🗑   │  A table is in 2NF when every non-key column depends │
│   ✓ Ready, 128 passages       │  on the whole primary key ▓DBMS_Notes, § Normal forms▓│
│ ▢ DBMS.pptx              🗑   │  3NF adds one rule: no non-key column may depend on  │
│   ✓ Ready, 41 passages        │  another non-key column ▓DBMS, slide 14▓. So 3NF     │
│ ▢ DBMS_Notes.docx        🗑   │  removes transitive dependencies that 2NF allows     │
│   ◌ Processing…               │  ▓DBMS, slide 15▓.                                   │
│                               │                                                      │
│                               │  Sources                                             │
│                               │  1  DBMS_Notes.docx   § Normal forms           ▾     │
│                               │  2  DBMS.pptx         slide 14                 ▴     │
│                               │  ┌────────────────────────────────────────────────┐  │
│                               │  │▓ Third normal form: a relation is in 3NF if it ▓│  │
│                               │  │▓ is in 2NF and no non-prime attribute is       ▓│  │
│                               │  │▓ transitively dependent on a candidate key.    ▓│  │
│                               │  └────────────────────────────────────────────────┘  │
│                               │  3  DBMS.pptx         slide 15                 ▾     │
│                               │                                                      │
│                               │ ╭──────────────────────────────────────────────────╮ │
│                               │ │ Ask about your notes…                        (↑) │ │
│                               │ ╰──────────────────────────────────────────────────╯ │
│                               │   Enter to send, Shift+Enter for a new line          │
└───────────────────────────────┴──────────────────────────────────────────────────────┘
```

Notes
- Inline citations show the document name without extension plus location, truncated at 18 characters for the name. Full name in a tooltip and in the source list.
- The expanded passage uses `--evidence-tint` with a 3 px left bar in `--evidence`; the citation that opened it switches to `--evidence-strong`.
- Source numbers are a real sequence (they match answer order), so numbering is justified here.
- File-type icons (`▢` in the sketch) are Phosphor `FilePdf` / `FilePpt` / `FileDoc`. Long file names truncate the stem but always keep the extension visible.

### 4.2 Desktop: first visit (S5)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ CourseMind                                   How it works ↗        ✓ Connected       │
├───────────────────────────────┬──────────────────────────────────────────────────────┤
│ Documents        0 of 30      │                                                      │
│                               │                                                      │
│ [+ Add files]                 │            Add your course files to start            │
│ [Try sample documents]        │                                                      │
│ PDF, .docx, .pptx, up to 25 MB│     CourseMind answers questions from your PDFs,     │
│ ───────────────────────────── │     slides, and Word notes, and shows the page       │
│ No documents yet.             │     each answer came from.                           │
│                               │                                                      │
│                               │        [ Add files ]   [ Try sample documents ]      │
│                               │                                                      │
│                               │ ╭──────────────────────────────────────────────────╮ │
│                               │ │ Add a document to ask questions.          (↑)    │ │
│                               │ ╰──────────────────────────────────────────────────╯ │
└───────────────────────────────┴──────────────────────────────────────────────────────┘
```

No illustration. The empty state is an invitation with two clear actions. After samples load, the centered block is replaced by three suggested questions (outline buttons, left-aligned, one per line).

### 4.3 Answer block states (S8)

```
Searching          ◌ Searching 3 documents…

Sources found      ◌ Found 4 passages. Writing answer…
                   Sources
                   1  OS_Lecture3.pdf   p. 12        ▾
                   …

Streaming          A deadlock needs four conditions at once: mutual
                   exclusion, hold and wait ▓OS_Lecture3, p. 12▓, no
                   preemption, and circular wait▍                     [■ Stop]

Done               (caret and progress line gone; Stop becomes send again)

Refused            I couldn't find that in your notes.
                   Try rephrasing with terms from your notes, or add the
                   document that covers this.
                   (no sources, no yellow)

Stopped / error    …partial text stays…
                   Stopped.                                           [↻ Retry]
                   The answer was interrupted.                        [↻ Retry]
```

The progress line keeps the same position from "Searching" to "Writing" so nothing jumps. Source rows reserve their height as they arrive.

### 4.4 Library row states (S3)

```
▢ Lecture_05.pdf                         Uploading…            (spinner)
▢ Lecture_05.pdf                         Queued                (Clock)
▢ Lecture_05.pdf                         Processing…           (spinner)
▢ Lecture_05.pdf                    🗑   Ready, 96 passages    (CheckCircle, success)
▢ Scan_notes.pdf                    ✕    No selectable text found. Scanned
                                         documents aren't supported yet.   (WarningCircle, destructive)
▢ Week2.ppt                         ✕    Old Word and PowerPoint formats aren't
                                         supported. Save it as .docx or .pptx and add it again.
```

Failed rows wrap their message (never truncate an error) and show **Remove** (`✕`, labelled "Remove Scan_notes.pdf"). Delete is disabled while a file is processing, with the reason in a tooltip. Sample documents carry a small "Sample" badge.

### 4.5 Mobile thread and library sheet (S2, S4)

```
┌───────────────────────────┐    ┌───────────────────────────┐
│ CourseMind   [Documents 3]│    │ Documents        3 of 30 ✕│
│               ✓ Connected │    │                           │
├───────────────────────────┤    │ [+ Add files]             │
│      ╭──────────────────╮ │    │ [Try sample documents]    │
│      │ What is 3NF?     │ │    │ PDF, .docx, .pptx,        │
│      ╰──────────────────╯ │    │ up to 25 MB               │
│                           │    │ ───────────────────────── │
│ 3NF means no non-key      │    │ ▢ OS_Lecture3.pdf       🗑 │
│ column depends on another │    │   ✓ Ready, 128 passages   │
│ non-key column            │    │ ▢ DBMS.pptx             🗑 │
│ ▓DBMS, slide 14▓.         │    │   ✓ Ready, 41 passages    │
│                           │    │ ▢ DBMS_Notes.docx       🗑 │
│ Sources                   │    │   ◌ Processing…           │
│ 1 DBMS.pptx  slide 14   ▾ │    │                           │
│                           │    │                           │
│╭─────────────────────────╮│    │                           │
││ Ask about your notes… (↑)││   │                           │
│╰─────────────────────────╯│    │                           │
└───────────────────────────┘    └───────────────────────────┘
      Thread (S2)                   Library sheet (S4)
```

All touch targets are at least 44 × 44 px. The question box sits above the safe-area inset and the on-screen keyboard.

### 4.6 Delete confirmation (S10) and server banner (S12)

```
╭──────────────────────────────────────────────╮
│ Delete OS_Lecture3.pdf?                      │
│                                              │
│ It will no longer be used in answers.        │
│ Answers already shown stay on screen.        │
│                                              │
│                  [Cancel]  [Delete document] │   ← destructive button
╰──────────────────────────────────────────────╯

┌──────────────────────────────────────────────────────────────┐
│ ◌ The server is starting. This can take up to a minute.     │   ← Alert at top of thread
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Interaction details

- **Question box:** multi-line, grows to 6 lines then scrolls. Enter sends, Shift+Enter adds a line. Counter appears at 450 characters. Send is disabled under 3 characters, with the reason in helper text. While streaming, the send button becomes **Stop** (Apple HIG: let people halt processing).
- **Citations:** inline buttons styled as highlighter marks, minimum 24 px tall (WCAG 2.2 target size). Hover or focus shows the full document name in a tooltip. Selecting one toggles its source row and scrolls it into view only if it's off screen.
- **Thread scrolling:** follows the stream while the reader is at the bottom; stops following as soon as they scroll up; a **Jump to latest** button appears (shadcn `MessageScrollerButton`).
- **Drag and drop:** dragging files anywhere over the window shows the drop overlay on the library (desktop). The file picker is always available as the non-drag alternative.
- **Suggested questions:** only for sample documents; selecting one sends it immediately and removes the suggestions.
- **Toasts:** only for transient, non-blocking confirmations ("Sample documents added.", "OS_Lecture3.pdf deleted."). Errors about a specific file or answer appear on that file or answer instead.

---

## 6. Component map (shadcn/ui)

Init with the Next.js template, choose Phosphor as the icon library, then replace every theme token with §3. Never ship the default look.

| UI part | shadcn component(s) | Customization |
|---|---|---|
| Header actions | `Button` (ghost), `Tooltip` | "How it works" is a real link (`<a>`), not a button. |
| Server banner | `Alert` | Neutral styling; no yellow. |
| Add files, samples | `Button` (primary / outline) + hidden `input[type=file]` | Label wraps the input so the button opens the picker. |
| Library list | `ScrollArea`, `Item` (`ItemMedia`, `ItemContent`, `ItemTitle`, `ItemDescription`, `ItemActions`) | Rows, not cards. `Separator` between groups only. |
| Status | Icon + text in `ItemDescription`; `Spinner` while processing | `Badge` only for the "Sample" tag. |
| Library loading | `Skeleton` | Three rows, same shape as real rows. |
| Empty states | `Empty` | Heading M + body + actions; no illustration. |
| Mobile library | `Sheet` (side left) with `SheetTitle` "Documents" | Width 88vw, max 360 px. |
| Delete | `AlertDialog` | Confirm button uses destructive variant, label "Delete document". |
| Thread | `MessageScroller`, `MessageScrollerItem`, `MessageScrollerButton` | Built-in stream-follow and jump-to-latest; no custom scroll code. |
| Question | `Message align="end"` + `Bubble variant="muted"` | 12 px radius, `--secondary` fill. |
| Answer | `Message align="start"` + `Bubble variant="ghost"` | No surface, full reading column; no avatar. |
| Inline citation | `Button` with a new `evidence` variant | `--evidence` fill, 4 px radius, xs size, 24 px min height. |
| Source list | `Collapsible` per row inside an ordered list | Expanded content uses `--evidence-tint` + 3 px `--evidence` left bar. |
| Question box | `InputGroup` + `InputGroupTextarea` + `InputGroupAddon` (send/stop `Button`), `Field` + `FieldDescription` | Helper text and counter in `FieldDescription`. |
| Suggested questions | `Button` (outline, sm) | Left-aligned stack. |
| Toasts | `toast` / `sonner` (whichever the chosen base uses) | Bottom-right desktop, bottom-center mobile. |

Follow the shadcn rules: semantic tokens only (no raw hex in components), `gap-*` not `space-*`, `size-*` for square elements, titles on every dialog and sheet.

---

## 7. Voice and copy

- **Sentence case** for everything: headings, buttons, labels.
- **Name things the way students do:** documents, library, passages, sources, questions. Never show internal words: chunks, embeddings, vectors, workspace, collection, tokens.
- **Buttons say exactly what happens**, and an action keeps its name through the flow: "Add files" (never Upload / Import), "Try sample documents" → toast "Sample documents added.", "Delete document" → toast "OS_Lecture3.pdf deleted."
- **Progress text is specific:** "Searching 3 documents…", "Found 4 passages. Writing answer…". Never a bare "Loading…".
- **Errors** say what happened and what to do next. They don't apologize and are never vague. "Something went wrong" is banned. Full catalogue: APP_FLOW §5.
- **No em dashes** in any UI string. Use a period, comma, or colon.
- **Numerals** for counts ("3 of 30 documents"); `…` as one character; curly apostrophes.
- **The refusal sentence is fixed:** "I couldn't find that in your notes."

---

## 8. What we will not do

- Chat bubbles around answers, avatars, robot or sparkle icons, "AI" badges.
- Gradients, glows, glassmorphism, purple or electric-blue accents.
- Inter + `#2563EB`, cream + terracotta, or near-black + neon.
- Cards for every document or source; the same shadow under everything.
- All-caps labels, eyebrow labels, decorative dots, section numbers.
- Yellow on anything that is not evidence from the student's documents.
- Spinner-only waits with no text; errors in generic modals or toasts when they belong to a row or answer.
- An in-app light/dark toggle.
- Motion on page load, scroll reveals, or replayed typewriter text.
- Emoji as icons.

---

## 9. Accessibility and quality checklist

Build is not done until every line is true.

**Accessibility**
- [ ] Text contrast ≥ 4.5:1 and control borders ≥ 3:1 in both modes (§3.1 table).
- [ ] Visible `:focus-visible` ring (2 px `--ring`, 2 px offset) on every interactive element; never removed.
- [ ] Skip link "Skip to question box" is the first focusable element.
- [ ] Status is icon + text, never color alone.
- [ ] Icon-only buttons have `aria-label` ("Delete OS_Lecture3.pdf"); decorative icons are `aria-hidden`.
- [ ] Status changes announced with `aria-live="polite"`; the streaming answer is `aria-busy` and announces "Answer ready." once.
- [ ] Dialog and sheet have titles, trap focus, close on Esc, and return focus.
- [ ] Touch targets ≥ 44 px on mobile; inline citations ≥ 24 px.
- [ ] Drag and drop has the file picker alternative.
- [ ] Works at 200% zoom and 320 px width; zoom never disabled.
- [ ] `prefers-reduced-motion` respected (§3.6).
- [ ] File names and "CourseMind" wrapped with `translate="no"`; `<html lang="en">`.

**Web interface guidelines**
- [ ] Buttons are `<button>`, links are `<a>`; no clickable `div`s.
- [ ] Question box has a real label, `name`, and `autocomplete="off"`; paste is never blocked.
- [ ] No `transition: all`; only listed properties.
- [ ] Long names handled (`truncate` + `min-w-0`, extension kept visible); errors wrap.
- [ ] Dates and numbers formatted with `Intl.*` (if any are shown).
- [ ] `color-scheme` and `theme-color` set for both modes.
- [ ] `overscroll-behavior: contain` on the sheet and dialog.

**Design consistency**
- [ ] Yellow appears only on evidence.
- [ ] Radius rule (4 / 8 / 12 px) followed everywhere.
- [ ] One icon family (Phosphor), one font family (+ its mono for code only).
- [ ] No raw hex in components; all colors come from tokens.
- [ ] Every screen checked in light mode, dark mode, desktop, and mobile before calling it done.
