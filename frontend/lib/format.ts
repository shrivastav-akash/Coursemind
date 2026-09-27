const CITATION_NAME_CHARS = 18; // UI_UX_BRIEF §4.1

export function splitName(name: string): [stem: string, ext: string] {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? [name.slice(0, dot), name.slice(dot)] : [name, ""];
}

// "p. 12" and "slide 4" never break across lines (§3.2).
export function displayLocation(location: string): string {
  return location.replace(/^(p\.|slide|§) /, "$1 ");
}

// Inline citation text: file name without extension, cut at 18 characters, then the location.
export function citationLabel(name: string, location: string): string {
  const [stem] = splitName(name);
  const short = stem.length > CITATION_NAME_CHARS ? `${stem.slice(0, CITATION_NAME_CHARS - 1)}…` : stem;
  return `${short}, ${displayLocation(location)}`;
}

export const count = new Intl.NumberFormat("en");

const plural = new Intl.PluralRules("en");
export function passages(n: number): string {
  return `${count.format(n)} ${plural.select(n) === "one" ? "passage" : "passages"}`;
}
