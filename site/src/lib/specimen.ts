/**
 * The specimen's keyboard/state model, kept pure so it can be tested without a browser.
 *
 * The page is a specimen first and a document second: B/L switch weight, M/S switch family,
 * I toggles italic, arrows walk the sections and 1–9 jump to one. None of that fires while the
 * visitor is editing text in the hero.
 */

export type Family = "sans" | "mono";
export type Weight = "regular" | "bold";

export interface SpecimenState {
  family: Family;
  weight: Weight;
  italic: boolean;
}

export const INITIAL_STATE: SpecimenState = { family: "sans", weight: "regular", italic: false };

export const SECTIONS = [
  "specimen",
  "ascii",
  "lookalikes",
  "grid",
  "text",
  "coverage",
  "download",
] as const;

export type SectionId = (typeof SECTIONS)[number];

export interface KeyContext {
  /** True when focus sits in the editable hero or any other text field. */
  editing: boolean;
  /** Index of the section currently in view. */
  section: number;
}

export type Action =
  | { type: "state"; state: SpecimenState }
  | { type: "section"; index: number }
  | { type: "none" };

const sectionStep = (index: number, direction: 1 | -1): number => {
  const next = index + direction;
  return Math.min(SECTIONS.length - 1, Math.max(0, next));
};

/** Every key the specimen listens for; anything else is `none`. */
export function applyKey(state: SpecimenState, key: string, context: KeyContext): Action {
  if (context.editing && key.length === 1) return { type: "none" };
  switch (key) {
    case "b":
    case "B":
    case "l":
    case "L":
      return { type: "state", state: { ...state, weight: "bold" } };
    case "r":
    case "R":
      return { type: "state", state: { ...state, weight: "regular" } };
    case "m":
    case "M":
      return { type: "state", state: { ...state, family: "mono" } };
    case "s":
    case "S":
      return { type: "state", state: { ...state, family: "sans" } };
    case "i":
    case "I":
      return { type: "state", state: { ...state, italic: !state.italic } };
    case "ArrowDown":
      return { type: "section", index: sectionStep(context.section, 1) };
    case "ArrowUp":
      return { type: "section", index: sectionStep(context.section, -1) };
    default: {
      if (/^[1-9]$/.test(key)) {
        const index = Number(key) - 1;
        return index < SECTIONS.length ? { type: "section", index } : { type: "none" };
      }
      return { type: "none" };
    }
  }
}

/** The CSS family stack the specimen and the code samples use for the current state. */
export function fontFamily(state: SpecimenState): string {
  return state.family === "mono" ? '"QuBlack Mono"' : '"QuBlack Sans"';
}

/** The six font faces a state can address (Regular/Bold × upright/italic per family). */
export function faceLabel(state: SpecimenState): string {
  const family = state.family === "mono" ? "QuBlack Mono" : "QuBlack Sans";
  const style = state.weight === "bold" ? "Bold" : "Regular";
  return `${family} ${style}${state.italic ? " Italic" : ""}`;
}
